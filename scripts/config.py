"""
Configuration module for trend analysis scripts.
Handles database connections and shared constants.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    host: str
    port: int
    database: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create config from environment variables."""
        url = os.environ.get("DATABASE_URL", "")
        if url:
            # Parse DATABASE_URL format
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return cls(
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                database=parsed.path.lstrip("/") or "postgres",
                user=parsed.username or "postgres",
                password=parsed.password or "",
            )
        return cls(
            host=os.environ.get("PGHOST", "localhost"),
            port=int(os.environ.get("PGPORT", "5432")),
            database=os.environ.get("PGDATABASE", "postgres"),
            user=os.environ.get("PGUSER", "postgres"),
            password=os.environ.get("PGPASSWORD", ""),
        )

    def connection_params(self) -> dict:
        """Return psycopg2-compatible connection parameters."""
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.database,
            "user": self.user,
            "password": self.password,
            "options": "-c client_encoding=UTF8",
        }


@dataclass
class AnalysisConfig:
    """Configuration for analysis parameters."""
    # Time windows
    trend_days: int = 30
    forecast_days: int = 14
    moving_average_window: int = 7

    # Thresholds
    min_posts_for_analysis: int = 5
    top_n_posts: int = 10
    top_n_users: int = 10

    # Output
    output_dir: str = "output"
    report_filename: str = "trend_report.pdf"
    
    # Chart styling
    chart_style: str = "seaborn-v0_8-darkgrid"
    primary_color: str = "#8B5CF6"
    secondary_color: str = "#EC4899"
    tertiary_color: str = "#10B981"
    background_color: str = "#0F172A"
    text_color: str = "#E2E8F0"
    grid_color: str = "#1E293B"


# Singleton instances
db_config = DatabaseConfig.from_env()
analysis_config = AnalysisConfig()
