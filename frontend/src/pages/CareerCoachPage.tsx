import { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Send, User, Bot, RefreshCw, Zap } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import api from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const STARTER_PROMPTS = [
  'Why is my match score low?',
  'What skills should I learn next?',
  'How can I improve my resume?',
  'What projects should I build to stand out?',
  'How do I negotiate a higher salary?',
  'How do I prepare for a technical interview?',
];

export default function CareerCoachPage() {
  const { user } = useAuthStore();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: `Hello ${user?.full_name?.split(' ')[0] || 'there'}! 👋 I'm your AI Career Coach powered by ResuMesh.\n\nI can help you with:\n- **Resume optimization** and ATS tips\n- **Skill gap analysis** and learning roadmaps\n- **Interview preparation** strategies\n- **Career trajectory** planning\n\nWhat would you like to work on today?`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const chatMutation = useMutation({
    mutationFn: async (message: string) => {
      const history = messages.slice(-10).map((m) => ({
        role: m.role,
        content: m.content,
      }));
      return api.post('/rag/chat', {
        message,
        history,
      }).then((r) => r.data);
    },
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.response, timestamp: new Date() },
      ]);
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please make sure your LLM service is running and try again.',
          timestamp: new Date(),
        },
      ]);
    },
  });

  const sendMessage = (text: string) => {
    if (!text.trim() || chatMutation.isPending) return;
    const userMessage: Message = {
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };
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

  return (
    <div className="page-container h-full flex flex-col" style={{ maxHeight: 'calc(100vh - 56px)' }}>
      {/* Header */}
      <div className="page-header mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="page-title flex items-center gap-2">
              <MessageSquare size={22} className="text-brand-400" /> Career Coach AI
            </h1>
            <p className="page-subtitle">Powered by LangGraph + RAG · Personalized to your resume</p>
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

      {/* Messages */}
      <div className="flex-1 overflow-y-auto card p-4 mb-4 space-y-4">
        <AnimatePresence>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
            >
              {/* Avatar */}
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

              {/* Bubble */}
              <div className={`max-w-[78%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-brand-600 text-white rounded-tr-sm'
                  : 'bg-dark-700 border border-dark-600 text-slate-100 rounded-tl-sm'
              }`}>
                {msg.role === 'assistant' ? (
                  <ReactMarkdown
                    className="prose prose-invert prose-sm max-w-none prose-p:my-1 prose-li:my-0.5"
                  >
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
