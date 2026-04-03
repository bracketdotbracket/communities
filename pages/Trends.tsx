import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import Layout from "@/components/Layout";
import { ArrowLeft, TrendingUp, Clock, Users, Activity, Zap } from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, PieChart, Pie,
} from "recharts";
import { format, subDays, startOfDay, getHours, getDay } from "date-fns";

const COLORS = {
  likes: "hsl(330, 80%, 60%)",
  comments: "hsl(var(--primary))",
  reposts: "hsl(142, 70%, 45%)",
  posts: "hsl(200, 80%, 55%)",
};

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const Trends = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dailyData, setDailyData] = useState<any[]>([]);
  const [hourlyData, setHourlyData] = useState<any[]>([]);
  const [dayOfWeekData, setDayOfWeekData] = useState<any[]>([]);
  const [growthRate, setGrowthRate] = useState<string>("stable");
  const [engagementBreakdown, setEngagementBreakdown] = useState<any[]>([]);

  useEffect(() => {
    const fetchTrends = async () => {
      setLoading(true);

      // Fetch all engagement data
      const [
        { data: posts },
        { data: likes },
        { data: comments },
        { data: reposts },
      ] = await Promise.all([
        supabase.from("posts").select("id, created_at").order("created_at"),
        supabase.from("likes").select("id, created_at").order("created_at"),
        supabase.from("comments").select("id, created_at").order("created_at"),
        supabase.from("reposts").select("id, created_at").order("created_at"),
      ]);

      // Build 30-day daily data
      const days: any[] = [];
      for (let i = 29; i >= 0; i--) {
        const day = startOfDay(subDays(new Date(), i));
        const nextDay = startOfDay(subDays(new Date(), i - 1));
        const dayStr = format(day, "MMM d");

        const count = (arr: any[]) =>
          arr.filter((item) => {
            const d = new Date(item.created_at);
            return d >= day && d < nextDay;
          }).length;

        days.push({
          date: dayStr,
          posts: count(posts || []),
          likes: count(likes || []),
          comments: count(comments || []),
          reposts: count(reposts || []),
        });
      }
      setDailyData(days);

      // Hourly distribution
      const allTimestamps = [
        ...(posts || []),
        ...(likes || []),
        ...(comments || []),
        ...(reposts || []),
      ];

      const hourCounts = Array(24).fill(0);
      const dayCounts = Array(7).fill(0);

      allTimestamps.forEach((item) => {
        const d = new Date(item.created_at);
        hourCounts[getHours(d)]++;
        dayCounts[getDay(d)]++;
      });

      setHourlyData(
        hourCounts.map((count, hour) => ({
          hour: `${hour}:00`,
          activity: count,
        }))
      );

      setDayOfWeekData(
        dayCounts.map((count, day) => ({
          day: DAY_NAMES[day],
          activity: count,
        }))
      );

      // Engagement breakdown pie chart
      const totalLikes = (likes || []).length;
      const totalComments = (comments || []).length;
      const totalReposts = (reposts || []).length;
      setEngagementBreakdown([
        { name: "Likes", value: totalLikes, color: COLORS.likes },
        { name: "Comments", value: totalComments, color: COLORS.comments },
        { name: "Reposts", value: totalReposts, color: COLORS.reposts },
      ]);

      // Growth rate detection
      const recentTotal = days.slice(-7).reduce((s, d) => s + d.likes + d.comments + d.reposts, 0);
      const previousTotal = days.slice(-14, -7).reduce((s, d) => s + d.likes + d.comments + d.reposts, 0);
      if (previousTotal === 0 && recentTotal === 0) setGrowthRate("no data");
      else if (recentTotal > previousTotal * 1.2) setGrowthRate("growing 📈");
      else if (recentTotal < previousTotal * 0.8) setGrowthRate("declining 📉");
      else setGrowthRate("stable ➡️");

      setLoading(false);
    };

    fetchTrends();
  }, []);

  const peakHour = hourlyData.reduce(
    (max, h) => (h.activity > max.activity ? h : max),
    { hour: "N/A", activity: 0 }
  );

  const peakDay = dayOfWeekData.reduce(
    (max, d) => (d.activity > max.activity ? d : max),
    { day: "N/A", activity: 0 }
  );

  const totalEngagement = engagementBreakdown.reduce((s, e) => s + e.value, 0);

  return (
    <Layout>
      <div className="min-h-screen">
        <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-post-border px-4 py-3 flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="p-2 -ml-2 rounded-full hover:bg-hover transition-colors">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold">Trends</h1>
            <p className="text-xs text-muted-foreground">Platform-wide analytics</p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
          </div>
        ) : (
          <div className="p-4 space-y-6">
            {/* Quick Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: "Trend", value: growthRate, icon: TrendingUp, color: "text-primary" },
                { label: "Peak Hour", value: peakHour.hour, icon: Clock, color: "text-pink-500" },
                { label: "Peak Day", value: peakDay.day, icon: Zap, color: "text-amber-500" },
                { label: "Total Actions", value: totalEngagement.toLocaleString(), icon: Activity, color: "text-green-500" },
              ].map((stat) => (
                <div key={stat.label} className="rounded-xl border border-post-border p-4 bg-background">
                  <div className="flex items-center gap-2 mb-1">
                    <stat.icon className={`h-4 w-4 ${stat.color}`} />
                    <span className="text-xs text-muted-foreground">{stat.label}</span>
                  </div>
                  <p className="text-lg font-bold">{stat.value}</p>
                </div>
              ))}
            </div>

            {/* Engagement Over Time */}
            <div className="rounded-xl border border-post-border p-4 bg-background">
              <h2 className="text-sm font-bold mb-4 flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Engagement Over Time (30 Days)
              </h2>
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={dailyData}>
                  <defs>
                    <linearGradient id="likesG" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS.likes} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={COLORS.likes} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="commentsG" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS.comments} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={COLORS.comments} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: "hsl(var(--background))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} />
                  <Area type="monotone" dataKey="likes" stroke={COLORS.likes} fill="url(#likesG)" strokeWidth={2} name="Likes" />
                  <Area type="monotone" dataKey="comments" stroke={COLORS.comments} fill="url(#commentsG)" strokeWidth={2} name="Comments" />
                  <Area type="monotone" dataKey="reposts" stroke={COLORS.reposts} fill="none" strokeWidth={2} strokeDasharray="4 4" name="Reposts" />
                  <Area type="monotone" dataKey="posts" stroke={COLORS.posts} fill="none" strokeWidth={1.5} strokeDasharray="2 2" name="Posts" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Hourly Activity */}
              <div className="rounded-xl border border-post-border p-4 bg-background">
                <h2 className="text-sm font-bold mb-4 flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Activity by Hour
                </h2>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={hourlyData}>
                    <XAxis dataKey="hour" tick={{ fontSize: 8, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} interval={2} />
                    <YAxis tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={{ background: "hsl(var(--background))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} />
                    <Bar dataKey="activity" name="Activity" radius={[4, 4, 0, 0]}>
                      {hourlyData.map((entry, i) => (
                        <Cell key={i} fill={entry.hour === peakHour.hour ? COLORS.likes : "hsl(var(--primary) / 0.6)"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Day of Week */}
              <div className="rounded-xl border border-post-border p-4 bg-background">
                <h2 className="text-sm font-bold mb-4 flex items-center gap-2">
                  <Zap className="h-4 w-4" />
                  Activity by Day
                </h2>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={dayOfWeekData}>
                    <XAxis dataKey="day" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={{ background: "hsl(var(--background))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} />
                    <Bar dataKey="activity" name="Activity" radius={[4, 4, 0, 0]}>
                      {dayOfWeekData.map((entry, i) => (
                        <Cell key={i} fill={entry.day === peakDay.day ? COLORS.reposts : "hsl(var(--primary) / 0.6)"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Engagement Breakdown */}
            {totalEngagement > 0 && (
              <div className="rounded-xl border border-post-border p-4 bg-background">
                <h2 className="text-sm font-bold mb-4">Engagement Breakdown</h2>
                <div className="flex items-center justify-center gap-8">
                  <ResponsiveContainer width={180} height={180}>
                    <PieChart>
                      <Pie
                        data={engagementBreakdown}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={80}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {engagementBreakdown.map((entry, i) => (
                          <Cell key={i} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ background: "hsl(var(--background))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-2">
                    {engagementBreakdown.map((item) => (
                      <div key={item.name} className="flex items-center gap-2 text-sm">
                        <div className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
                        <span className="text-muted-foreground">{item.name}</span>
                        <span className="font-bold">{item.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Python analysis note */}
            <div className="rounded-xl border border-post-border p-4 bg-muted/30 text-center">
              <p className="text-xs text-muted-foreground">
                Advanced analysis with growth forecasting, community health scores, and detailed PDF reports
                is available via <code className="text-primary">scripts/generate_report.py</code>
              </p>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Trends;
