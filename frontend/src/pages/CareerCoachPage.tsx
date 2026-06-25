import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Send, User, Bot, RefreshCw, Zap, ChevronDown } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import api from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { getLLMHeaders } from './SettingsPage';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const STARTER_PROMPTS = [
  'Why is my match score low for this job?',
  'What skills should I add for this role?',
  'How can I improve my resume for this position?',
  'What interview questions should I prepare?',
  'How do I negotiate a higher salary?',
  'How does my experience compare to the job requirements?',
];

export default function CareerCoachPage() {
  const { user } = useAuthStore();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: `Hello ${user?.full_name?.split(' ')[0] || 'there'}! 👋 I'm your AI Career Coach powered by ResuMesh.\n\nSelect a **Resume** and **Job** above to get personalized advice — or just ask me anything!\n\nI can help you with:\n- **Resume optimization** and ATS tips\n- **Skill gap analysis** for specific roles\n- **Interview preparation** strategies\n- **Career trajectory** planning`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [selectedResume, setSelectedResume] = useState('');
  const [selectedJob, setSelectedJob] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const { data: resumesData } = useQuery({
    queryKey: ['resumes'],
    queryFn: () => api.get('/resumes/').then((r) => r.data),
  });

  const { data: jobsData } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => api.get('/jobs/').then((r) => r.data),
  });

  const resumes = resumesData?.items?.filter((r: any) => !r.is_deleted) || [];
  const jobs = jobsData?.items || [];

  const chatMutation = useMutation({
    mutationFn: async (message: string) => {
      const history = messages.slice(-10).map((m) => ({
        role: m.role,
        content: m.content,
      }));
      return api.post(
        '/rag/chat',
        {
          message,
          history,
          resume_id: selectedResume || undefined,
          job_id: selectedJob || undefined,
        },
        { headers: getLLMHeaders() }
      ).then((r) => r.data);
    },
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.response, timestamp: new Date() },
      ]);
    },
    onError: (err: any) => {
      const errMsg = err.response?.data?.detail || 'Sorry, I encountered an error. Please check your LLM settings.';
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: errMsg, timestamp: new Date() },
      ]);
    },
  });

  const sendMessage = (text: string) => {
    if (!text.trim() || chatMutation.isPending) return;
    const userMessage: Message = { role: 'user', content: text.trim(), timestamp: new Date() };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    chatMutation.mutate(text.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const selectedResumeLabel = resumes.find((r: any) => r.id === selectedResume)?.title || 'All resumes';
  const selectedJobLabel = jobs.find((j: any) => j.id === selectedJob)
    ? `${jobs.find((j: any) => j.id === selectedJob).title} @ ${jobs.find((j: any) => j.id === selectedJob).company}`
    : 'No job selected';

  return (
    <div className="page-container h-full flex flex-col" style={{ maxHeight: 'calc(100vh - 56px)' }}>
      {/* Header */}
      <div className="page-header mb-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="page-title flex items-center gap-2">
              <MessageSquare size={22} className="text-brand-400" /> Career Coach AI
            </h1>
            <p className="page-subtitle">Select a resume and job for personalized advice</p>
          </div>
          <button
            onClick={() => setMessages([{
              role: 'assistant',
              content: 'Chat cleared! How can I help you today?',
              timestamp: new Date(),
            }])}
            className="btn-ghost text-sm"
          >
            <RefreshCw size={14} /> New Chat
          </button>
        </div>
      </div>

      {/* Context selectors */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <label className="label text-[11px] mb-1">Resume Context</label>
          <div className="relative">
            <select
              value={selectedResume}
              onChange={(e) => setSelectedResume(e.target.value)}
              className="input text-sm pr-8 appearance-none"
            >
              <option value="" className="bg-slate-900">— All resumes —</option>
              {resumes.map((r: any) => (
                <option key={r.id} value={r.id} className="bg-slate-900">
                  {r.title}{r.is_primary ? ' ★' : ''}
                </option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          </div>
        </div>
        <div>
          <label className="label text-[11px] mb-1">Job Context</label>
          <div className="relative">
            <select
              value={selectedJob}
              onChange={(e) => setSelectedJob(e.target.value)}
              className="input text-sm pr-8 appearance-none"
            >
              <option value="" className="bg-slate-900">— No job selected —</option>
              {jobs.map((j: any) => (
                <option key={j.id} value={j.id} className="bg-slate-900">
                  {j.title} @ {j.company}
                </option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Active context pill */}
      {(selectedResume || selectedJob) && (
        <div className="flex flex-wrap gap-2 mb-3">
          {selectedResume && (
            <span className="text-[11px] bg-brand-900/40 border border-brand-700/40 text-brand-300 px-2.5 py-1 rounded-full flex items-center gap-1.5">
              📄 {selectedResumeLabel}
            </span>
          )}
          {selectedJob && (
            <span className="text-[11px] bg-purple-900/40 border border-purple-700/40 text-purple-300 px-2.5 py-1 rounded-full flex items-center gap-1.5">
              💼 {selectedJobLabel}
            </span>
          )}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto card p-4 mb-3 space-y-4">
        <AnimatePresence>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                msg.role === 'assistant'
                  ? 'bg-gradient-brand shadow-glow-sm'
                  : 'bg-dark-600 border border-dark-400'
              }`}>
                {msg.role === 'assistant'
                  ? <Zap size={14} className="text-white" />
                  : <User size={14} className="text-slate-400" />
                }
              </div>
              <div className={`max-w-[78%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-brand-600 text-white rounded-tr-sm'
                  : 'bg-dark-700 border border-dark-600 text-slate-100 rounded-tl-sm'
              }`}>
                {msg.role === 'assistant' ? (
                  <ReactMarkdown className="prose prose-invert prose-sm max-w-none prose-p:my-1 prose-li:my-0.5">
                    {msg.content}
                  </ReactMarkdown>
                ) : (
                  <p className="text-sm leading-relaxed">{msg.content}</p>
                )}
                <div className="text-[10px] opacity-50 mt-1.5">
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </motion.div>
          ))}

          {chatMutation.isPending && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-brand shadow-glow-sm flex items-center justify-center">
                <Zap size={14} className="text-white" />
              </div>
              <div className="bg-dark-700 border border-dark-600 rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex gap-1 items-center">
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="w-2 h-2 bg-brand-400 rounded-full animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Starter prompts */}
      {messages.length <= 1 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {STARTER_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => sendMessage(prompt)}
              className="text-xs bg-dark-700 border border-dark-500 hover:border-brand-600/50 text-slate-300 hover:text-white px-3 py-1.5 rounded-full transition-all"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="flex gap-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask your career coach anything... (Shift+Enter for new line)"
          rows={1}
          className="input flex-1 resize-none min-h-[44px] max-h-32"
          style={{ height: 'auto' }}
          onInput={(e: any) => {
            e.target.style.height = 'auto';
            e.target.style.height = e.target.scrollHeight + 'px';
          }}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={!input.trim() || chatMutation.isPending}
          className="btn-primary px-4 self-end"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
