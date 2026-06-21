import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Briefcase, FileText, Mail, TrendingUp, Target,
  ArrowRight, Zap, AlertCircle,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const STATUS_COLORS: Record<string, string> = {
  saved: '#6b7280',
  applied: '#3b82f6',
  interview: '#f59e0b',
  rejected: '#ef4444',
  offer: '#10b981',
  accepted: '#8b5cf6',
};

export default function DashboardPage() {
  const { user } = useAuthStore();

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics', 'dashboard'],
    queryFn: () => api.get('/analytics/dashboard').then((r) => r.data),
  });

  const statusData = analytics?.applications?.by_status
    ? Object.entries(analytics.applications.by_status).map(([status, count]) => ({
        name: status.charAt(0).toUpperCase() + status.slice(1),
        value: count as number,
        color: STATUS_COLORS[status] || '#6b7280',
      }))
    : [];

  const missingSkillsData = (analytics?.top_missing_skills || []).slice(0, 8).map((s: any) => ({
    name: s.skill,
    frequency: s.frequency,
  }));

  const statCards = [
    {
      label: 'Total Applications',
      value: analytics?.applications?.total ?? '—',
      icon: Briefcase,
      color: 'text-blue-400',
      bg: 'bg-blue-900/20',
      border: 'border-blue-800/30',
    },
    {
      label: 'Avg. Match Score',
      value: analytics?.applications?.avg_match_score ? `${analytics.applications.avg_match_score}%` : '—',
      icon: Target,
      color: 'text-brand-400',
      bg: 'bg-brand-900/20',
      border: 'border-brand-800/30',
    },
    {
      label: 'Resumes Uploaded',
      value: analytics?.resumes?.total ?? '—',
      icon: FileText,
      color: 'text-green-400',
      bg: 'bg-green-900/20',
      border: 'border-green-800/30',
    },
    {
      label: 'Cover Letters',
      value: analytics?.cover_letters?.total ?? '—',
      icon: Mail,
      color: 'text-yellow-400',
      bg: 'bg-yellow-900/20',
      border: 'border-yellow-800/30',
    },
  ];

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="page-title">
              Welcome back, {user?.full_name?.split(' ')[0]} 👋
            </h1>
            <p className="page-subtitle">Here's your job search overview</p>
          </div>
          <Link to="/jobs" className="btn-primary text-sm">
            <Zap size={16} /> Analyze Job
          </Link>
        </div>
      </div>

      {/* Quick actions if no data */}
      {!isLoading && analytics?.applications?.total === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-6 mb-8 flex items-center gap-4"
        >
          <div className="w-10 h-10 bg-brand-900/40 border border-brand-700/30 rounded-xl flex items-center justify-center flex-shrink-0">
            <AlertCircle size={20} className="text-brand-400" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-white text-sm mb-0.5">Get started with ResuMesh</h3>
            <p className="text-slate-400 text-sm">Upload your resume and analyze your first job to see your personalized dashboard.</p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <Link to="/resumes" className="btn-secondary text-xs py-1.5 px-3">Upload Resume</Link>
            <Link to="/jobs" className="btn-primary text-xs py-1.5 px-3">Analyze Job</Link>
          </div>
        </motion.div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {statCards.map((card, i) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className={`card p-5 border ${card.border}`}
          >
            <div className={`w-10 h-10 ${card.bg} rounded-xl flex items-center justify-center mb-3`}>
              <card.icon size={20} className={card.color} />
            </div>
            <div className="text-3xl font-bold text-white mb-1">
              {isLoading ? <span className="shimmer inline-block w-12 h-8 rounded" /> : card.value}
            </div>
            <div className="text-sm text-slate-400">{card.label}</div>
          </motion.div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Application Pipeline */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card p-6"
        >
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-brand-400" />
            Application Pipeline
          </h2>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={statusData} cx="50%" cy="50%" innerRadius={60} outerRadius={90}
                  dataKey="value" nameKey="name" label={({ name, value }) => `${name}: ${value}`}
                  labelLine={false}
                >
                  {statusData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#111118', border: '1px solid #1e1e2e', borderRadius: '8px', color: '#e2e8f0' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-slate-500 text-sm">
              No applications yet. Start by analyzing a job!
            </div>
          )}
        </motion.div>

        {/* Missing Skills */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card p-6"
        >
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Target size={18} className="text-brand-400" />
            Top Missing Skills
          </h2>
          {missingSkillsData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={missingSkillsData} layout="vertical" margin={{ left: 0, right: 20 }}>
                <XAxis type="number" stroke="#374151" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                <YAxis type="category" dataKey="name" width={90} tick={{ fill: '#d1d5db', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#111118', border: '1px solid #1e1e2e', borderRadius: '8px', color: '#e2e8f0' }}
                />
                <Bar dataKey="frequency" fill="#7c3aed" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-slate-500 text-sm">
              Analyze jobs to see your skill gaps here.
            </div>
          )}
        </motion.div>
      </div>

      {/* Quick links */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="grid grid-cols-1 sm:grid-cols-3 gap-4"
      >
        {[
          { title: 'Upload Resume', desc: 'Add a new resume to analyze jobs', to: '/resumes', icon: FileText },
          { title: 'Analyze a Job', desc: 'Paste a job description for scoring', to: '/jobs', icon: Briefcase },
          { title: 'Chat with Coach', desc: 'Get AI career advice instantly', to: '/coach', icon: Zap },
        ].map((item) => (
          <Link key={item.title} to={item.to}
            className="card-hover p-5 group"
          >
            <item.icon size={20} className="text-brand-400 mb-3" />
            <div className="font-semibold text-white text-sm mb-1">{item.title}</div>
            <div className="text-xs text-slate-400 mb-3">{item.desc}</div>
            <div className="flex items-center text-brand-400 text-xs font-medium group-hover:gap-2 transition-all">
              Get started <ArrowRight size={12} className="ml-1" />
            </div>
          </Link>
        ))}
      </motion.div>
    </div>
  );
}
