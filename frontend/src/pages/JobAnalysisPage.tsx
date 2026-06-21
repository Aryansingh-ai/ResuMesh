import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Briefcase, Target, CheckCircle, XCircle, Lightbulb, Send, ExternalLink } from 'lucide-react';
import api from '@/lib/api';
import clsx from 'clsx';

const PORTALS = ['linkedin', 'wellfound', 'internshala', 'naukri', 'manual'];

export default function JobAnalysisPage() {
  const [form, setForm] = useState({
    title: '', company: '', location: '', portal: 'manual',
    job_url: '', raw_description: '',
  });
  const [matchResult, setMatchResult] = useState<any>(null);
  const [analyzedJobId, setAnalyzedJobId] = useState<string | null>(null);
  const [step, setStep] = useState<'form' | 'results'>('form');

  const { data: resumes } = useQuery({
    queryKey: ['resumes'],
    queryFn: () => api.get('/resumes/').then((r) => r.data),
  });

  const primaryResume = resumes?.items?.find((r: any) => r.is_primary) || resumes?.items?.[0];

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      // 1. Analyze the job
      const jobRes = await api.post('/jobs/analyze', form);
      setAnalyzedJobId(jobRes.data.id);

      // 2. Get match score if resume exists
      if (primaryResume?.id) {
        const matchRes = await api.post('/matching/score', {
          resume_id: primaryResume.id,
          job_id: jobRes.data.id,
          save_to_application: true,
        });
        setMatchResult(matchRes.data);
      } else {
        setMatchResult({ score: null, matched_skills: [], missing_skills: [], recommendations: [] });
      }

      setStep('results');
      return jobRes.data;
    },
  });

  const handleSubmit = () => {
    if (!form.title || !form.company || !form.raw_description) return;
    analyzeMutation.mutate();
  };

  const scoreColor = (score: number) => {
    if (score >= 70) return 'text-green-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  const scoreLabel = (score: number) => {
    if (score >= 70) return 'Great Match!';
    if (score >= 50) return 'Decent Match';
    if (score >= 30) return 'Needs Work';
    return 'Poor Match';
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Job Analysis</h1>
        <p className="page-subtitle">Paste a job description to see your match score and recommendations.</p>
      </div>

      {step === 'form' ? (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 lg:grid-cols-2 gap-6"
        >
          <div className="card p-6 space-y-5">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Briefcase size={16} className="text-brand-400" /> Job Details
            </h2>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Job Title *</label>
                <input className="input" placeholder="Software Engineer"
                  value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
              </div>
              <div>
                <label className="label">Company *</label>
                <input className="input" placeholder="Acme Corp"
                  value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Location</label>
                <input className="input" placeholder="San Francisco, CA"
                  value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
              </div>
              <div>
                <label className="label">Portal</label>
                <select className="input" value={form.portal} onChange={(e) => setForm({ ...form, portal: e.target.value })}>
                  {PORTALS.map((p) => (
                    <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="label">Job URL</label>
              <input className="input" placeholder="https://..."
                value={form.job_url} onChange={(e) => setForm({ ...form, job_url: e.target.value })} />
            </div>

            {!primaryResume && (
              <div className="bg-yellow-900/20 border border-yellow-800/30 rounded-lg p-3 text-xs text-yellow-400 flex items-start gap-2">
                <Lightbulb size={14} className="mt-0.5 flex-shrink-0" />
                <span>Upload a resume first to get a match score. You can still analyze the job description.</span>
              </div>
            )}

            {primaryResume && (
              <div className="bg-green-900/20 border border-green-800/30 rounded-lg p-3 text-xs text-green-400 flex items-center gap-2">
                <CheckCircle size={14} className="flex-shrink-0" />
                Using <strong className="text-green-300">{primaryResume.title}</strong> for matching
              </div>
            )}
          </div>

          <div className="card p-6">
            <label className="label">Job Description * (paste full text)</label>
            <textarea
              className="input h-80 resize-none font-mono text-xs"
              placeholder="Paste the full job description here..."
              value={form.raw_description}
              onChange={(e) => setForm({ ...form, raw_description: e.target.value })}
            />
            <div className="text-xs text-slate-500 mt-2 text-right">{form.raw_description.length} chars</div>

            <button
              onClick={handleSubmit}
              disabled={!form.title || !form.company || !form.raw_description || analyzeMutation.isPending}
              className="btn-primary w-full justify-center mt-4"
            >
              {analyzeMutation.isPending ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Analyzing...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Target size={16} /> Analyze Job
                </span>
              )}
            </button>
          </div>
        </motion.div>
      ) : (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
          <button onClick={() => setStep('form')} className="btn-ghost text-sm">← Analyze Another Job</button>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Score */}
            <div className="card p-6 text-center">
              <div className="text-sm text-slate-400 mb-2 uppercase tracking-wider">Match Score</div>
              {matchResult?.score != null ? (
                <>
                  <div className={`text-6xl font-black ${scoreColor(matchResult.score)}`}>
                    {Math.round(matchResult.score)}%
                  </div>
                  <div className={`text-sm mt-2 font-medium ${scoreColor(matchResult.score)}`}>
                    {scoreLabel(matchResult.score)}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">Model: {matchResult.model_version}</div>
                </>
              ) : (
                <div className="text-slate-500 text-sm">Upload a resume to see your score</div>
              )}
            </div>

            {/* Skills */}
            <div className="card p-6 lg:col-span-2">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h3 className="text-sm font-semibold text-green-400 mb-3 flex items-center gap-2">
                    <CheckCircle size={14} /> Matched Skills
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {(matchResult?.matched_skills || []).length > 0 ? (
                      (matchResult.matched_skills || []).map((s: string) => (
                        <span key={s} className="badge-green text-[11px]">{s}</span>
                      ))
                    ) : (
                      <span className="text-slate-500 text-xs">None matched</span>
                    )}
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
                    <XCircle size={14} /> Missing Skills
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {(matchResult?.missing_skills || []).length > 0 ? (
                      (matchResult.missing_skills || []).map((s: string) => (
                        <span key={s} className="badge-red text-[11px]">{s}</span>
                      ))
                    ) : (
                      <span className="text-green-400 text-xs">🎉 All skills covered!</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Recommendations */}
          {(matchResult?.recommendations || []).length > 0 && (
            <div className="card p-6">
              <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
                <Lightbulb size={16} className="text-yellow-400" /> Recommendations
              </h2>
              <div className="space-y-3">
                {matchResult.recommendations.slice(0, 5).map((rec: any, i: number) => (
                  <div key={i} className="flex gap-4 p-3 bg-dark-800 rounded-lg border border-dark-600">
                    <div className={clsx(
                      'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0',
                      rec.priority <= 2 ? 'bg-red-900/40 text-red-400' : 'bg-yellow-900/40 text-yellow-400'
                    )}>
                      {rec.priority}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-white text-sm">{rec.title}</div>
                      <div className="text-slate-400 text-xs mt-0.5">{rec.description}</div>
                      {rec.resource_url && (
                        <a href={rec.resource_url} target="_blank" rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-brand-400 text-xs mt-1 hover:text-brand-300">
                          Learn <ExternalLink size={10} />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
