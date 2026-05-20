import React, { useState, useEffect } from 'react';
import { Calendar, TrendingUp, TrendingDown, Minus, AlertTriangle, Sparkles, Loader2, RefreshCw } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const WeeklySummary = () => {
  const { token } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_URL = import.meta.env.VITE_API_URL;

  const fetchWeeklySummary = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/analytics/weekly-summary`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Failed to load weekly summary');
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchWeeklySummary(); }, []);

  const trendIcon = {
    improving: <TrendingUp className="w-5 h-5 text-emerald-400" />,
    stable: <Minus className="w-5 h-5 text-yellow-400" />,
    declining: <TrendingDown className="w-5 h-5 text-red-400" />
  };

  const trendColor = {
    improving: 'text-emerald-400',
    stable: 'text-yellow-400',
    declining: 'text-red-400'
  };

  const riskColor = {
    low: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    moderate: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    high: 'bg-red-500/10 text-red-400 border-red-500/20'
  };

  if (loading) {
    return (
      <div className="bg-glass border border-borderglass rounded-2xl p-8 flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-indigo-400 animate-spin mr-3" />
        <span className="text-xs font-bold tracking-widest uppercase text-muted">Generating Weekly Synthesis...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-glass border border-borderglass rounded-2xl p-6">
        <div className="flex items-center gap-2 text-red-400">
          <AlertTriangle className="w-5 h-5" />
          <p className="text-sm">{error}</p>
        </div>
        <button onClick={fetchWeeklySummary} className="mt-3 text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
          <RefreshCw className="w-3 h-3" /> Retry
        </button>
      </div>
    );
  }

  if (!data || data.status === 'insufficient_data') {
    return (
      <div className="bg-glass border border-borderglass rounded-2xl p-6 text-center">
        <Calendar className="w-8 h-8 text-muted mx-auto mb-3" />
        <p className="text-sm text-muted">{data?.message || 'Not enough data for a weekly summary yet.'}</p>
        <p className="text-xs text-muted/60 mt-1">Keep journaling daily to unlock your weekly synthesis!</p>
      </div>
    );
  }

  return (
    <div className="bg-glass border border-borderglass rounded-2xl p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Calendar className="w-5 h-5 text-indigo-400" />
          <h3 className="text-sm font-black tracking-widest uppercase text-foreground">Weekly Synthesis</h3>
        </div>
        <div className="flex items-center gap-2">
          {trendIcon[data.trend]}
          <span className={`text-xs font-bold uppercase tracking-wider ${trendColor[data.trend]}`}>
            {data.trend}
          </span>
        </div>
      </div>

      {/* Period */}
      {data.period && (
        <p className="text-[10px] text-muted tracking-wider">
          {data.period.start} → {data.period.end}
        </p>
      )}

      {/* Summary */}
      <div className="p-4 bg-surface rounded-xl border border-borderglass">
        <p className="text-sm text-foreground leading-relaxed">{data.summary}</p>
      </div>

      {/* Stats Row */}
      {data.stats && (
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3 bg-surface rounded-xl border border-borderglass text-center">
            <p className="text-lg font-black text-foreground">{data.stats.days_active || 0}</p>
            <p className="text-[10px] font-bold tracking-widest uppercase text-muted">Days Active</p>
          </div>
          <div className="p-3 bg-surface rounded-xl border border-borderglass text-center">
            <p className="text-lg font-black text-foreground">{data.stats.total_journals || 0}</p>
            <p className="text-[10px] font-bold tracking-widest uppercase text-muted">Journals</p>
          </div>
          <div className="p-3 bg-surface rounded-xl border border-borderglass text-center">
            <p className="text-lg font-black text-foreground">{data.stats.total_events || 0}</p>
            <p className="text-[10px] font-bold tracking-widest uppercase text-muted">Syncs</p>
          </div>
        </div>
      )}

      {/* Daily Trend Mini Chart */}
      {data.daily_trend && (
        <div>
          <p className="text-[10px] font-bold tracking-widest uppercase text-muted mb-2">Daily Wellness</p>
          <div className="flex items-end gap-1 h-16">
            {data.daily_trend.map((d, i) => {
              const score = d.score || 0;
              const height = Math.max(4, (score / 100) * 64);
              const color = score >= 60 ? 'bg-emerald-500/60' : score >= 40 ? 'bg-yellow-500/60' : 'bg-red-500/60';
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div className={`w-full rounded-t-md ${d.score !== null ? color : 'bg-white/5'}`} 
                       style={{ height: `${d.score !== null ? height : 4}px` }}
                       title={d.score !== null ? `${d.day}: ${d.score}%` : `${d.day}: No data`}
                  />
                  <span className="text-[8px] text-muted">{d.day}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Patterns */}
      {data.patterns?.length > 0 && (
        <div>
          <p className="text-[10px] font-bold tracking-widest uppercase text-muted mb-2">Patterns Detected</p>
          <div className="space-y-2">
            {data.patterns.map((p, i) => (
              <div key={i} className="p-2 bg-indigo-500/5 border border-indigo-500/10 rounded-lg">
                <p className="text-xs text-foreground">• {p}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {data.recommendations?.length > 0 && (
        <div>
          <p className="text-[10px] font-bold tracking-widest uppercase text-muted mb-2">Recommendations</p>
          <div className="space-y-2">
            {data.recommendations.map((r, i) => (
              <div key={i} className="p-2 bg-emerald-500/5 border border-emerald-500/10 rounded-lg flex items-start gap-2">
                <Sparkles className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-foreground">{r}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Highlight */}
      {data.highlight && (
        <div className="p-3 bg-yellow-500/5 border border-yellow-500/10 rounded-xl">
          <p className="text-[10px] font-bold tracking-widest uppercase text-yellow-400 mb-1">✨ Week's Highlight</p>
          <p className="text-xs text-foreground">{data.highlight}</p>
        </div>
      )}

      {/* Risk Level */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold tracking-widest uppercase text-muted">Risk Assessment</span>
        <span className={`text-[10px] font-bold tracking-widest uppercase px-3 py-1 rounded-full border ${riskColor[data.risk_level] || riskColor.low}`}>
          {data.risk_level}
        </span>
      </div>

      {/* Refresh */}
      <button onClick={fetchWeeklySummary} className="w-full mt-2 text-xs text-indigo-400 hover:text-indigo-300 flex items-center justify-center gap-1 py-2">
        <RefreshCw className="w-3 h-3" /> Regenerate Synthesis
      </button>
    </div>
  );
};

export default WeeklySummary;
