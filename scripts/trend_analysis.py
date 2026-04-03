"""
Trend Analysis Engine
=====================
Performs statistical analysis on community platform engagement data.
Computes growth trends, peak activity patterns, engagement forecasts,
and community health scores.

Usage:
    python scripts/trend_analysis.py

Dependencies:
    pandas, numpy, scipy, psycopg2-binary, matplotlib, seaborn
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import savgol_filter

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import db_config, analysis_config


def get_db_connection():
    """Establish database connection."""
    import psycopg2
    return psycopg2.connect(**db_config.connection_params())


def fetch_engagement_data(conn) -> Dict[str, pd.DataFrame]:
    """
    Fetch all engagement data from the database.
    Returns DataFrames for posts, likes, comments, reposts, and profiles.
    """
    tables = {
        "posts": "SELECT id, user_id, community_id, created_at FROM posts ORDER BY created_at",
        "likes": "SELECT id, post_id, user_id, created_at FROM likes ORDER BY created_at",
        "comments": "SELECT id, post_id, user_id, created_at FROM comments ORDER BY created_at",
        "reposts": "SELECT id, post_id, user_id, created_at FROM reposts ORDER BY created_at",
        "profiles": "SELECT id, username, display_name, created_at FROM profiles ORDER BY created_at",
        "communities": "SELECT id, name, creator_id, created_at FROM communities ORDER BY created_at",
        "memberships": "SELECT id, user_id, community_id, created_at FROM memberships ORDER BY created_at",
    }

    data = {}
    for name, query in tables.items():
        try:
            df = pd.read_sql(query, conn)
            if "created_at" in df.columns:
                df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
            data[name] = df
        except Exception as e:
            print(f"  Warning: Could not fetch {name}: {e}")
            data[name] = pd.DataFrame()

    return data


def compute_daily_engagement(data: Dict[str, pd.DataFrame], days: int = 30) -> pd.DataFrame:
    """
    Compute daily engagement metrics over the specified time window.
    Returns a DataFrame with columns: date, posts, likes, comments, reposts, total.
    """
    cutoff = datetime.now(tz=pd.Timestamp.now(tz="UTC").tz) - timedelta(days=days)
    date_range = pd.date_range(
        start=cutoff.date(),
        end=datetime.now(tz=pd.Timestamp.now(tz="UTC").tz).date(),
        freq="D",
    )

    daily = pd.DataFrame({"date": date_range.date})

    for metric in ["posts", "likes", "comments", "reposts"]:
        df = data.get(metric, pd.DataFrame())
        if df.empty or "created_at" not in df.columns:
            daily[metric] = 0
            continue

        filtered = df[df["created_at"] >= cutoff].copy()
        filtered["date"] = filtered["created_at"].dt.date
        counts = filtered.groupby("date").size().reset_index(name=metric)
        daily = daily.merge(counts, on="date", how="left")
        daily[metric] = daily[metric].fillna(0).astype(int)

    daily["total"] = daily["posts"] + daily["likes"] + daily["comments"] + daily["reposts"]
    return daily


def compute_moving_averages(daily: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    """Add moving average columns for smoothed trend visualization."""
    for col in ["posts", "likes", "comments", "reposts", "total"]:
        if col in daily.columns:
            daily[f"{col}_ma"] = daily[col].rolling(window=window, min_periods=1).mean()
    return daily


def detect_peak_hours(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Analyze activity by hour of day and day of week.
    Returns a pivot table (7 days × 24 hours) with activity counts.
    """
    all_timestamps = []
    for key in ["posts", "likes", "comments", "reposts"]:
        df = data.get(key, pd.DataFrame())
        if not df.empty and "created_at" in df.columns:
            all_timestamps.extend(df["created_at"].tolist())

    if not all_timestamps:
        return pd.DataFrame()

    ts_df = pd.DataFrame({"timestamp": all_timestamps})
    ts_df["hour"] = ts_df["timestamp"].dt.hour
    ts_df["day_of_week"] = ts_df["timestamp"].dt.day_name()

    heatmap = ts_df.groupby(["day_of_week", "hour"]).size().reset_index(name="count")
    pivot = heatmap.pivot_table(
        index="day_of_week",
        columns="hour",
        values="count",
        fill_value=0,
    )

    # Reorder days
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])

    return pivot


def forecast_growth(daily: pd.DataFrame, forecast_days: int = 14) -> Dict:
    """
    Use polynomial regression to forecast engagement growth.
    Returns forecast data and trend statistics.
    """
    if daily.empty or daily["total"].sum() == 0:
        return {"forecast": [], "trend": "insufficient_data", "r_squared": 0}

    x = np.arange(len(daily))
    y = daily["total"].values.astype(float)

    # Fit polynomial (degree 2 for trend detection)
    try:
        coeffs = np.polyfit(x, y, deg=2)
        poly = np.poly1d(coeffs)

        # Generate forecast
        future_x = np.arange(len(daily), len(daily) + forecast_days)
        forecast_values = np.maximum(poly(future_x), 0)  # No negative predictions

        # R-squared
        y_pred = poly(x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Determine trend direction
        slope = coeffs[-2] if len(coeffs) > 1 else coeffs[0]
        if slope > 0.5:
            trend = "growing"
        elif slope < -0.5:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "forecast": forecast_values.tolist(),
            "trend": trend,
            "r_squared": round(r_squared, 4),
            "slope": round(float(slope), 4),
        }
    except Exception as e:
        return {"forecast": [], "trend": "error", "r_squared": 0, "error": str(e)}


def compute_community_health(data: Dict[str, pd.DataFrame]) -> List[Dict]:
    """
    Calculate health score for each community based on:
    - Member engagement ratio (active members / total members)
    - Post frequency
    - Engagement per post (likes + comments + reposts per post)
    - Growth trend
    """
    communities = data.get("communities", pd.DataFrame())
    if communities.empty:
        return []

    health_scores = []
    for _, comm in communities.iterrows():
        cid = comm["id"]

        # Count members
        members = data.get("memberships", pd.DataFrame())
        member_count = len(members[members["community_id"] == cid]) if not members.empty else 0

        # Count posts
        posts = data.get("posts", pd.DataFrame())
        comm_posts = posts[posts["community_id"] == cid] if not posts.empty else pd.DataFrame()
        post_count = len(comm_posts)

        if post_count == 0:
            health_scores.append({
                "community_id": cid,
                "name": comm.get("name", "Unknown"),
                "health_score": 0,
                "member_count": member_count,
                "post_count": 0,
                "avg_engagement": 0,
            })
            continue

        # Engagement per post
        post_ids = comm_posts["id"].tolist()
        likes = data.get("likes", pd.DataFrame())
        comments = data.get("comments", pd.DataFrame())
        reposts = data.get("reposts", pd.DataFrame())

        like_count = len(likes[likes["post_id"].isin(post_ids)]) if not likes.empty else 0
        comment_count = len(comments[comments["post_id"].isin(post_ids)]) if not comments.empty else 0
        repost_count = len(reposts[reposts["post_id"].isin(post_ids)]) if not reposts.empty else 0

        total_engagement = like_count + comment_count + repost_count
        avg_engagement = total_engagement / post_count

        # Health score (0-100)
        engagement_score = min(avg_engagement * 10, 40)  # Max 40 points
        activity_score = min(post_count * 2, 30)  # Max 30 points
        member_score = min(member_count * 3, 30)  # Max 30 points
        health_score = round(engagement_score + activity_score + member_score, 1)

        health_scores.append({
            "community_id": cid,
            "name": comm.get("name", "Unknown"),
            "health_score": min(health_score, 100),
            "member_count": member_count,
            "post_count": post_count,
            "avg_engagement": round(avg_engagement, 2),
        })

    return sorted(health_scores, key=lambda x: x["health_score"], reverse=True)


def compute_top_performers(data: Dict[str, pd.DataFrame], top_n: int = 10) -> Dict:
    """Find top posts by engagement and most active users."""
    posts = data.get("posts", pd.DataFrame())
    if posts.empty:
        return {"top_posts": [], "top_users": []}

    # Top posts
    post_engagement = []
    for _, post in posts.iterrows():
        pid = post["id"]
        likes = len(data["likes"][data["likes"]["post_id"] == pid]) if not data["likes"].empty else 0
        comments = len(data["comments"][data["comments"]["post_id"] == pid]) if not data["comments"].empty else 0
        reposts_count = len(data["reposts"][data["reposts"]["post_id"] == pid]) if not data["reposts"].empty else 0
        total = likes + comments + reposts_count

        post_engagement.append({
            "post_id": pid,
            "user_id": post["user_id"],
            "likes": likes,
            "comments": comments,
            "reposts": reposts_count,
            "total_engagement": total,
            "created_at": str(post["created_at"]),
        })

    top_posts = sorted(post_engagement, key=lambda x: x["total_engagement"], reverse=True)[:top_n]

    # Most active users
    user_activity = {}
    for key in ["posts", "likes", "comments", "reposts"]:
        df = data.get(key, pd.DataFrame())
        if df.empty:
            continue
        for uid in df["user_id"].values:
            uid_str = str(uid)
            if uid_str not in user_activity:
                user_activity[uid_str] = {"posts": 0, "likes": 0, "comments": 0, "reposts": 0}
            user_activity[uid_str][key] += 1

    top_users = sorted(
        [{"user_id": uid, **counts, "total": sum(counts.values())} for uid, counts in user_activity.items()],
        key=lambda x: x["total"],
        reverse=True,
    )[:top_n]

    return {"top_posts": top_posts, "top_users": top_users}


def run_analysis() -> Dict:
    """
    Main analysis pipeline.
    Connects to database, fetches data, and runs all analysis modules.
    """
    print("=" * 60)
    print("  📊 Community Platform — Trend Analysis Engine")
    print("=" * 60)
    print()

    # Connect and fetch
    print("🔌 Connecting to database...")
    conn = get_db_connection()
    print("📥 Fetching engagement data...")
    data = fetch_engagement_data(conn)
    conn.close()

    # Print data summary
    for name, df in data.items():
        print(f"  • {name}: {len(df)} records")
    print()

    # Run analysis modules
    print("📈 Computing daily engagement trends...")
    daily = compute_daily_engagement(data, days=analysis_config.trend_days)
    daily = compute_moving_averages(daily, window=analysis_config.moving_average_window)

    print("⏰ Detecting peak activity hours...")
    peak_hours = detect_peak_hours(data)

    print("🔮 Forecasting growth trends...")
    forecast = forecast_growth(daily, forecast_days=analysis_config.forecast_days)

    print("🏥 Computing community health scores...")
    health = compute_community_health(data)

    print("🏆 Finding top performers...")
    performers = compute_top_performers(data, top_n=analysis_config.top_n_posts)

    # Summary
    print()
    print("=" * 60)
    print("  📋 Analysis Summary")
    print("=" * 60)
    print(f"  Trend direction:  {forecast['trend']}")
    print(f"  R² confidence:    {forecast['r_squared']}")
    print(f"  Total engagement: {daily['total'].sum()}")
    print(f"  Avg daily:        {daily['total'].mean():.1f}")
    print(f"  Communities:      {len(health)}")
    print(f"  Top posts found:  {len(performers['top_posts'])}")
    print()

    results = {
        "generated_at": datetime.utcnow().isoformat(),
        "daily_engagement": daily.to_dict(orient="records"),
        "peak_hours": peak_hours.to_dict() if not peak_hours.empty else {},
        "forecast": forecast,
        "community_health": health,
        "performers": performers,
        "summary": {
            "total_engagement": int(daily["total"].sum()),
            "avg_daily_engagement": round(float(daily["total"].mean()), 2),
            "trend": forecast["trend"],
            "num_communities": len(health),
        },
    }

    # Save results
    os.makedirs(analysis_config.output_dir, exist_ok=True)
    output_path = os.path.join(analysis_config.output_dir, "analysis_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"💾 Results saved to {output_path}")

    return results


if __name__ == "__main__":
    results = run_analysis()
