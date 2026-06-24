import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Briefcase, Target, CheckCircle, XCircle, Lightbulb, Send, ExternalLink } from 'lucide-react';
import api from '@/lib/api';
import clsx from 'clsx';

const PORTALS = ['linkedin', 'wellfound', 'internshala', 'naukri', 'manual'];

const getScoreReasons = (score: number, details: any) => {
  if (!details) return [];
  const reasons: string[] = [];
  const isHigh = score >= 80;

  const skillCoverage = details.skill_coverage ?? 0;
  if (isHigh) {
    if (skillCoverage >= 70) {
      reasons.push(`Strong skill match: You have ${Math.round(skillCoverage)}% of required skills.`);
    } else {
      reasons.push(`Partial skill match: You have ${Math.round(skillCoverage)}% of the skills, with other factors boosting your score.`);
    }
  } else {
    if (skillCoverage < 50) {
      reasons.push(`Low skill overlap: You are missing ${Math.round(100 - skillCoverage)}% of key skills.`);
    } else {
      reasons.push(`Moderate skill overlap: You have ${Math.round(skillCoverage)}% of required skills, but there are gaps.`);
    }
  }

  const expMatch = details.experience_match ?? 0;
  if (isHigh) {
    if (expMatch >= 90) {
      reasons.push(`Solid experience: Your professional experience matches or exceeds the requirements.`);
    }
  } else {
    if (expMatch < 50) {
      reasons.push(`Experience gap: Your years of experience do not meet the minimum requirement.`);
    } else if (expMatch < 80) {
      reasons.push(`Partial experience: Your background meets only some of the experience criteria.`);
    }
  }

  const eduMatch = details.education_match ?? 0;
  if (isHigh) {
    if (eduMatch >= 90) {
      reasons.push(`Education aligned: Your degree background perfectly matches requirements.`);
    }
  } else {
    if (eduMatch < 70) {
      reasons.push(`Education gap: Your educational credentials do not fully align with requirements.`);
    }
  }

  if (details.embedding_score != null) {
    const semScore = Math.round(details.embedding_score * 100);
    if (isHigh) {
      if (semScore >= 60) {
        reasons.push(`Contextual match: High semantic relevance between your resume text and the job description.`);
      }
    } else {
      if (semScore < 40) {
        reasons.push(`Low contextual match: The overall focus of your resume doesn't strongly relate to this job.`);
      }
    }
  }

  if (reasons.length === 0) {
    if (isHigh) {
      reasons.push(`Good overall fit: Your combined profile matches the position requirements well.`);
    } else {
      reasons.push(`Profile mismatch: Minor gaps in skill alignment and required experience.`);
    }
  }
  return reasons;
};

export default function JobAnalysisPage() {
  const [form, setForm] = useState({
    title: '', company: '', location: '', portal: 'manual',
    job_url: '', raw_description: '',
  });
  const [matchResult, setMatchResult] = useState<any>(null);
  const [analyzedJobId, setAnalyzedJobId] = useState<string | null>(null);
  const [step, setStep] = useState<'form' | 'results'>('form');
  const [selectedResumeId, setSelectedResumeId] = useState<string>('');

  const { data: resumes } = useQuery({
    queryKey: ['resumes'],
    queryFn: () => api.get('/resumes/').then((r) => r.data),
  });

  const primaryResume = resumes?.items?.find((r: any) => r.is_primary) || resumes?.items?.[0];

  useEffect(() => {
    if (resumes?.items?.length > 0 && !selectedResumeId) {
      const primary = resumes.items.find((r: any) => r.is_primary) || resumes.items[0];
      setSelectedResumeId(primary.id);
    }
  }, [resumes, selectedResumeId]);

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      // 1. Analyze the job
      const jobRes = await api.post('/jobs/analyze', form);
      setAnalyzedJobId(jobRes.data.id);

      // 2. Get match score if resume exists
      const resumeIdToUse = selectedResumeId || primaryResume?.id;
      if (resumeIdToUse) {
        const matchRes = await api.post('/matching/score', {
          resume_id: resumeIdToUse,
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
                    <option key={p} value={p} className="bg-slate-900 text-white">{p.charAt(0).toUpperCase() + p.slice(1)}</option>
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

            {resumes?.items && resumes.items.length > 0 && (
              <div className="bg-green-900/20 border border-green-800/30 rounded-lg p-3 text-xs text-green-400 space-y-2">
                <div className="flex items-center gap-2">
                  <CheckCircle size={14} className="flex-shrink-0" />
                  <span>Select resume for matching:</span>
                </div>
                <select
                  value={selectedResumeId}
                  onChange={(e) => setSelectedResumeId(e.target.value)}
                  className="input py-1.5 text-xs bg-slate-900 text-white border-dark-600 focus:border-brand-500 w-full"
                >
                  {resumes.items.map((r: any) => (
                    <option key={r.id} value={r.id} className="bg-slate-900 text-white">
                      {r.title} ({r.file_name}){r.is_primary ? ' [Primary]' : ''}
                    </option>
                  ))}
                </select>
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
            {/* Left Column (Score + Explanation) */}
            <div className="space-y-6">
              {/* Score Card */}
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

              {/* Explanation Card */}
              {matchResult?.score != null && (
                <div className="card p-5 text-left space-y-3">
                  <h3 className={clsx(
                    'text-sm font-semibold flex items-center gap-2',
                    matchResult.score >= 80 ? 'text-green-400' : 'text-yellow-500'
                  )}>
                    {matchResult.score >= 80 ? 'Why the score is high' : 'Why the score is low'}
                  </h3>
                  <ul className="space-y-2">
                    {getScoreReasons(matchResult.score, matchResult.details).map((reason: string, i: number) => (
                      <li key={i} className="text-xs text-slate-300 flex items-start gap-2">
                        <span className={clsx(
                          'w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0',
                          matchResult.score >= 80 ? 'bg-green-400' : 'bg-yellow-500'
                        )} />
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
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
