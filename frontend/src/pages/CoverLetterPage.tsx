import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Mail, Zap, Copy, CheckCircle } from 'lucide-react';
import api from '@/lib/api';
import clsx from 'clsx';
import { getLLMHeaders } from './SettingsPage';

const TONES = [
  { id: 'professional', label: 'Professional', emoji: '👔' },
  { id: 'enthusiastic', label: 'Enthusiastic', emoji: '🚀' },
  { id: 'technical', label: 'Technical', emoji: '💻' },
];

export default function CoverLetterPage() {
  const [selectedResume, setSelectedResume] = useState('');
  const [selectedJob, setSelectedJob] = useState('');
  const [tone, setTone] = useState('professional');
  const [additionalContext, setAdditionalContext] = useState('');
  const [generatedLetter, setGeneratedLetter] = useState('');
  const [copied, setCopied] = useState(false);

  const { data: resumesData } = useQuery({
    queryKey: ['resumes'],
    queryFn: () => api.get('/resumes/').then((r) => r.data),
  });

  const { data: jobsData } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => api.get('/jobs/').then((r) => r.data),
  });

  // Jobs the user has actually matched/applied to (from Applications tracker)
  const { data: applicationsData } = useQuery({
    queryKey: ['applications'],
    queryFn: () => api.get('/applications/').then((r) => r.data),
  });

  const { data: savedLetters } = useQuery({
    queryKey: ['cover-letters'],
    queryFn: () => api.get('/coverletters/').then((r) => r.data),
  });

  const generateMutation = useMutation({
    mutationFn: () => api.post('/coverletters/generate', {
      resume_id: selectedResume,
      job_id: selectedJob,
      tone,
      additional_context: additionalContext,
      save: true,
    }, { headers: getLLMHeaders() }).then((r) => r.data),
    onSuccess: (data) => setGeneratedLetter(data.content),
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Generation failed. Check your LLM settings.';
      alert(msg);
    },
  });

  const handleCopy = () => {
    navigator.clipboard.writeText(generatedLetter);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const resumes = resumesData?.items?.filter((r: any) => r.is_parsed) || [];

  // Jobs from Applications (matched jobs the user has already analyzed against their resume)
  const applicationJobs: any[] = (applicationsData?.items || [])
    .map((app: any) => app.job)
    .filter(Boolean);
  const applicationJobIds = new Set(applicationJobs.map((j: any) => j.id));

  // All analyzed jobs (from /jobs/ endpoint)
  const allAnalyzedJobs: any[] = jobsData?.items || [];

  // Remaining jobs not already in applications
  const otherJobs = allAnalyzedJobs.filter((j: any) => !applicationJobIds.has(j.id));

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Cover Letter Generator</h1>
        <p className="page-subtitle">Generate tailored cover letters using AI. Your resume + job description = perfect letter.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Config */}
        <div className="card p-6 space-y-5">
          <h2 className="font-semibold text-white flex items-center gap-2">
            <Mail size={16} className="text-brand-400" /> Generate Cover Letter
          </h2>

          <div>
            <label className="label">Select Resume</label>
            <select className="input" value={selectedResume} onChange={(e) => setSelectedResume(e.target.value)}>
              <option value="" className="bg-slate-900 text-white">— Choose resume —</option>
              {resumes.map((r: any) => (
                <option key={r.id} value={r.id} className="bg-slate-900 text-white">{r.title} {r.is_primary ? '(Primary)' : ''}</option>
              ))}
            </select>
            {resumes.length === 0 && (
              <p className="text-xs text-yellow-400 mt-1">Upload and wait for a resume to be parsed first.</p>
            )}
          </div>

          <div>
            <label className="label">Select Job</label>
            <select className="input" value={selectedJob} onChange={(e) => setSelectedJob(e.target.value)}>
              <option value="" className="bg-slate-900 text-white">— Choose a job —</option>

              {/* Jobs from applications — shown first */}
              {applicationJobs.length > 0 && (
                <optgroup label="✅ Matched Jobs (from Applications)" style={{ color: '#a78bfa', background: '#0f0f17' }}>
                  {applicationJobs.map((j: any) => (
                    <option key={j.id} value={j.id} className="bg-slate-900 text-white">
                      {j.title} @ {j.company}
                    </option>
                  ))}
                </optgroup>
              )}

              {/* Other analyzed jobs not in applications */}
              {otherJobs.length > 0 && (
                <optgroup label="📋 All Analyzed Jobs" style={{ color: '#94a3b8', background: '#0f0f17' }}>
                  {otherJobs.map((j: any) => (
                    <option key={j.id} value={j.id} className="bg-slate-900 text-white">
                      {j.title} @ {j.company}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
            {applicationJobs.length === 0 && otherJobs.length === 0 && (
              <p className="text-xs text-yellow-400 mt-1">Analyze a job first to use it here.</p>
            )}
          </div>

          <div>
            <label className="label">Tone</label>
            <div className="grid grid-cols-3 gap-2">
              {TONES.map((t) => (
                <button key={t.id} onClick={() => setTone(t.id)}
                  className={clsx(
                    'py-2.5 px-3 rounded-lg border text-sm font-medium transition-all text-center',
                    tone === t.id
                      ? 'bg-brand-600 border-brand-500 text-white'
                      : 'bg-dark-700 border-dark-500 text-slate-400 hover:border-brand-600/40'
                  )}>
                  <div className="text-lg mb-0.5">{t.emoji}</div>
                  <div className="text-[11px]">{t.label}</div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="label">Additional Context (optional)</label>
            <textarea
              className="input resize-none h-24 text-sm"
              placeholder="Any specific achievements or skills to emphasize..."
              value={additionalContext}
              onChange={(e) => setAdditionalContext(e.target.value)}
            />
          </div>

          <button
            onClick={() => generateMutation.mutate()}
            disabled={!selectedResume || !selectedJob || generateMutation.isPending}
            className="btn-primary w-full justify-center"
          >
            {generateMutation.isPending ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Generating...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Zap size={15} /> Generate Cover Letter
              </span>
            )}
          </button>
        </div>

        {/* Output */}
        <div className="card p-6 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">Generated Letter</h2>
            {generatedLetter && (
              <div className="flex gap-2">
                <button onClick={handleCopy} className="btn-ghost text-sm">
                  {copied ? <><CheckCircle size={14} className="text-green-400" /> Copied!</> : <><Copy size={14} /> Copy</>}
                </button>
              </div>
            )}
          </div>

          {generatedLetter ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex-1"
            >
              <textarea
                className="input h-full min-h-[400px] text-sm leading-relaxed resize-none font-sans"
                value={generatedLetter}
                onChange={(e) => setGeneratedLetter(e.target.value)}
              />
              <div className="text-xs text-slate-500 mt-2 flex items-center justify-between">
                <span>{generatedLetter.split(/\s+/).length} words</span>
                <span className="text-green-400 flex items-center gap-1">
                  <CheckCircle size={10} /> Saved to your library
                </span>
              </div>
            </motion.div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-500 flex-col gap-3">
              <Mail size={40} className="text-slate-600" />
              <div className="text-sm">Your cover letter will appear here</div>
              <div className="text-xs text-slate-600">Select a resume and job, then click Generate</div>
            </div>
          )}
        </div>
      </div>

      {/* Saved letters */}
      {(savedLetters?.items || []).length > 0 && (
        <div className="mt-8">
          <h2 className="font-semibold text-white mb-4">Saved Cover Letters</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(savedLetters.items || []).map((cl: any) => (
              <div key={cl.id} className="card-hover p-4">
                <div className="font-medium text-white text-sm mb-1 truncate">{cl.title}</div>
                <div className="text-xs text-slate-500">{cl.tone} · {cl.word_count} words</div>
                <div className="text-xs text-slate-600 mt-1">{new Date(cl.created_at).toLocaleDateString()}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
