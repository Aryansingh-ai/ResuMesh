import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  Zap, ArrowRight, Github, Star, Briefcase, FileText,
  MessageSquare, BarChart2, Shield, Cpu, Globe, CheckCircle,
} from 'lucide-react';

const features = [
  {
    icon: Cpu,
    title: 'AI Match Scoring',
    description: 'Instantly compute how well your resume matches any job description using NLP and semantic embeddings.',
    color: 'text-brand-400',
    bg: 'bg-brand-900/30',
  },
  {
    icon: Briefcase,
    title: 'Auto Job Extraction',
    description: 'Chrome extension automatically extracts job details from LinkedIn, Wellfound, Internshala, and Naukri.',
    color: 'text-accent-cyan',
    bg: 'bg-cyan-900/20',
  },
  {
    icon: FileText,
    title: 'Cover Letter Generator',
    description: 'Generate tailored cover letters in seconds using LangChain RAG and your personal resume context.',
    color: 'text-accent-green',
    bg: 'bg-green-900/20',
  },
  {
    icon: MessageSquare,
    title: 'Career Coach AI',
    description: 'Chat with your personal AI career coach powered by LangGraph to improve your application strategy.',
    color: 'text-accent-yellow',
    bg: 'bg-yellow-900/20',
  },
  {
    icon: BarChart2,
    title: 'Application Tracker',
    description: 'Track every application through your pipeline with rich analytics and timeline views.',
    color: 'text-accent-orange',
    bg: 'bg-orange-900/20',
  },
  {
    icon: Shield,
    title: 'Privacy First',
    description: 'All data is self-hosted. Your resume never leaves your control. Open source and auditable.',
    color: 'text-purple-400',
    bg: 'bg-purple-900/20',
  },
];

const portals = [
  { name: 'LinkedIn', icon: '💼' },
  { name: 'Wellfound', icon: '🚀' },
  { name: 'Internshala', icon: '🎓' },
  { name: 'Naukri', icon: '💡' },
];

const stats = [
  { value: '10x', label: 'Faster Applications' },
  { value: '85%', label: 'Average Match Accuracy' },
  { value: '4', label: 'Job Portals Supported' },
  { value: 'Free', label: 'Always Open Source' },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-dark-900 overflow-x-hidden">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-dark-900/80 backdrop-blur-md border-b border-dark-600">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-brand rounded-lg flex items-center justify-center shadow-glow-sm">
              <Zap size={16} className="text-white" />
            </div>
            <span className="font-bold text-white text-lg">ResuMesh</span>
          </div>
          <nav className="hidden md:flex items-center gap-6">
            <a href="#features" className="text-slate-400 hover:text-white text-sm transition-colors">Features</a>
            <a href="#how-it-works" className="text-slate-400 hover:text-white text-sm transition-colors">How it works</a>
            <a href="https://github.com/Aryansingh-ai/ResuMesh" target="_blank" rel="noopener noreferrer"
              className="text-slate-400 hover:text-white text-sm transition-colors flex items-center gap-1">
              <Github size={14} /> GitHub
            </a>
          </nav>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-slate-300 hover:text-white text-sm font-medium transition-colors">
              Sign In
            </Link>
            <Link to="/register" className="btn-primary text-sm py-2 px-4">
              Get Started Free
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-32 pb-24 px-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-mesh opacity-30 pointer-events-none" />
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-brand-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-5xl mx-auto text-center relative">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 badge-purple mb-6 text-sm py-1.5 px-4">
              <Star size={12} /> Open Source · Free · Self-Hosted
            </div>

            <h1 className="text-5xl md:text-7xl font-black text-white leading-tight mb-6">
              Your AI-Powered
              <br />
              <span className="gradient-text">Job Application</span>
              <br />
              Copilot
            </h1>

            <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
              ResuMesh automatically analyzes job postings, scores your resume match,
              identifies skill gaps, and generates tailored cover letters — all from your browser.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link to="/register" className="btn-primary text-base py-3 px-8">
                Start Free Today <ArrowRight size={18} />
              </Link>
              <a href="https://github.com/Aryansingh-ai/ResuMesh" target="_blank"
                className="btn-secondary text-base py-3 px-8">
                <Github size={18} /> View on GitHub
              </a>
            </div>

            <p className="text-slate-600 text-sm mt-5">No credit card required · 100% free · Open source</p>
          </motion.div>
        </div>
      </section>

      {/* Portals */}
      <section className="py-10 border-y border-dark-600 bg-dark-800/50">
        <div className="max-w-4xl mx-auto px-4">
          <p className="text-center text-slate-500 text-sm mb-6 uppercase tracking-widest">
            Works with your favorite job portals
          </p>
          <div className="flex flex-wrap items-center justify-center gap-8">
            {portals.map((p) => (
              <div key={p.name} className="flex items-center gap-2 text-slate-400">
                <span className="text-2xl">{p.icon}</span>
                <span className="font-semibold text-slate-300">{p.name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-20 px-4">
        <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="card p-6 text-center"
            >
              <div className="text-4xl font-black gradient-text mb-2">{stat.value}</div>
              <div className="text-sm text-slate-400">{stat.label}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 px-4 bg-dark-800/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-4xl font-bold text-white mb-4">Everything you need to land your dream job</h2>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              A complete ML-powered toolkit built for students and professionals who take their career seriously.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                className="card-hover p-6"
              >
                <div className={`w-11 h-11 ${feature.bg} rounded-xl flex items-center justify-center mb-4`}>
                  <feature.icon size={22} className={feature.color} />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-4xl font-bold text-white mb-4">How ResuMesh Works</h2>
          </div>

          <div className="space-y-6">
            {[
              { step: '01', title: 'Upload Your Resume', desc: 'Upload your PDF or DOCX resume. Our AI parser extracts skills, experience, education, and projects automatically.' },
              { step: '02', title: 'Install Chrome Extension', desc: 'Add the ResuMesh extension to Chrome. It automatically detects job pages on LinkedIn, Wellfound, Internshala, and Naukri.' },
              { step: '03', title: 'Get Instant Analysis', desc: 'A sidebar appears showing your match score, matched skills, missing skills, and personalized recommendations.' },
              { step: '04', title: 'Generate & Apply', desc: 'Generate a tailored cover letter, save the job to your tracker, and let the AI coach guide your interview prep.' },
            ].map((item, i) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="card p-6 flex gap-6 items-start"
              >
                <div className="text-5xl font-black gradient-text flex-shrink-0 leading-none">{item.step}</div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-1">{item.title}</h3>
                  <p className="text-slate-400 text-sm leading-relaxed">{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-4 relative">
        <div className="absolute inset-0 bg-gradient-mesh opacity-20 pointer-events-none" />
        <div className="max-w-3xl mx-auto text-center relative">
          <h2 className="text-4xl md:text-5xl font-black text-white mb-6">
            Ready to supercharge your job search?
          </h2>
          <p className="text-slate-400 text-lg mb-8">
            Join thousands of students and professionals using ResuMesh to land more interviews.
          </p>
          <Link to="/register" className="btn-primary text-base py-3.5 px-10">
            Get Started — It's Free <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-dark-600 py-8 px-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Zap size={16} className="text-brand-400" />
            <span className="text-slate-400 text-sm">ResuMesh — MIT License</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-slate-500">
            <a href="https://github.com/Aryansingh-ai/ResuMesh" className="hover:text-white transition-colors">GitHub</a>
            <a href="/docs" className="hover:text-white transition-colors">Docs</a>
            <span>Built with ❤️ for job seekers</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
