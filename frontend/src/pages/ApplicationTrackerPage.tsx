import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Send, Briefcase, Calendar, TrendingUp, Filter } from 'lucide-react';
import { useState } from 'react';
import api from '@/lib/api';
import clsx from 'clsx';

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; border: string }> = {
  saved: { label: 'Saved', color: 'text-slate-400', bg: 'bg-slate-800/40', border: 'border-slate-700/50' },
  applied: { label: 'Applied', color: 'text-blue-400', bg: 'bg-blue-900/30', border: 'border-blue-800/40' },
  interview: { label: 'Interview', color: 'text-yellow-400', bg: 'bg-yellow-900/30', border: 'border-yellow-800/40' },
  rejected: { label: 'Rejected', color: 'text-red-400', bg: 'bg-red-900/20', border: 'border-red-800/30' },
  offer: { label: 'Offer', color: 'text-green-400', bg: 'bg-green-900/30', border: 'border-green-800/40' },
  accepted: { label: 'Accepted!', color: 'text-brand-400', bg: 'bg-brand-900/30', border: 'border-brand-800/40' },
};

const STATUSES = Object.keys(STATUS_CONFIG);

function ScoreBar({ score }: { score: number | null }) {
  if (score == null) return <span className="text-slate-500 text-xs">—</span>;
  const color = score >= 70 ? 'bg-green-500' : score >= 50 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-dark-600 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs text-slate-400 w-8">{Math.round(score)}%</span>
    </div>
  );
}

export default function ApplicationTrackerPage() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('all');

  const { data, isLoading } = useQuery({
    queryKey: ['applications', filter],
    queryFn: () => api.get('/applications/', {
      params: filter !== 'all' ? { status_filter: filter } : {},
    }).then((r) => r.data),
  });

  const { data: stats } = useQuery({
    queryKey: ['application-stats'],
    queryFn: () => api.get('/applications/stats/summary').then((r) => r.data),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.patch(`/applications/${id}/status`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['application-stats'] });
    },
  });

  const applications = data?.items || [];

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="page-title">Application Tracker</h1>
            <p className="page-subtitle">Track every job application through your pipeline.</p>
          </div>
        </div>
      </div>

      {/* Pipeline Summary */}
      {stats && (
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3 mb-6">
          {STATUSES.map((s) => {
            const cfg = STATUS_CONFIG[s];
            const count = stats.by_status?.[s] || 0;
            return (
              <div key={s} className={`card p-3 text-center border ${cfg.border} ${cfg.bg}`}>
                <div className={`text-xl font-bold ${cfg.color}`}>{count}</div>
                <div className="text-xs text-slate-400">{cfg.label}</div>
              </div>
            );
          })}
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-2 mb-5 flex-wrap">
        <Filter size={14} className="text-slate-500" />
        {['all', ...STATUSES].map((s) => (
          <button key={s} onClick={() => setFilter(s)}
            className={clsx(
              'text-xs px-3 py-1.5 rounded-full border transition-all',
              filter === s
                ? 'bg-brand-600 border-brand-500 text-white'
                : 'bg-dark-700 border-dark-500 text-slate-400 hover:text-white'
            )}>
            {s === 'all' ? 'All' : STATUS_CONFIG[s].label}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <div key={i} className="card h-16 shimmer" />)}
        </div>
      ) : applications.length === 0 ? (
        <div className="card p-14 text-center">
          <Send size={40} className="text-slate-600 mx-auto mb-4" />
          <h3 className="text-white font-medium mb-2">No applications {filter !== 'all' ? `with status "${filter}"` : 'yet'}</h3>
          <p className="text-slate-400 text-sm">Analyze a job to automatically add it here.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {applications.map((app: any, i: number) => (
            <motion.div
              key={app.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className="card p-4"
            >
              <div className="flex items-center gap-4">
                {/* Job info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-white text-sm truncate">
                      {app.job?.title || 'Unknown Position'}
                    </span>
                    <span className="text-slate-500 text-xs">@</span>
                    <span className="text-slate-300 text-xs">{app.job?.company}</span>
                    {app.job?.portal && (
                      <span className="badge-gray text-[10px]">{app.job.portal}</span>
                    )}
                  </div>
                  {app.job?.location && (
                    <div className="text-xs text-slate-500 mt-0.5">{app.job.location}</div>
                  )}
                </div>

                {/* Score */}
                <div className="w-28 flex-shrink-0 hidden sm:block">
                  <div className="text-[10px] text-slate-500 mb-1">Match Score</div>
                  <ScoreBar score={app.match_score} />
                </div>

                {/* Status selector */}
                <select
                  value={app.status}
                  onChange={(e) => updateMutation.mutate({ id: app.id, status: e.target.value })}
                  className={clsx(
                    'text-xs px-3 py-1.5 rounded-lg border font-medium cursor-pointer outline-none transition-all flex-shrink-0',
                    STATUS_CONFIG[app.status]?.bg,
                    STATUS_CONFIG[app.status]?.border,
                    STATUS_CONFIG[app.status]?.color,
                  )}
                >
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>{STATUS_CONFIG[s].label}</option>
                  ))}
                </select>

                {/* Date */}
                <div className="text-[10px] text-slate-500 flex-shrink-0 hidden md:block">
                  {new Date(app.created_at).toLocaleDateString()}
                </div>
              </div>

              {/* Missing skills preview */}
              {(app.missing_skills || []).length > 0 && (
                <div className="mt-3 flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] text-slate-500">Missing:</span>
                  {(app.missing_skills || []).slice(0, 5).map((s: string) => (
                    <span key={s} className="badge-red text-[10px]">{s}</span>
                  ))}
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
