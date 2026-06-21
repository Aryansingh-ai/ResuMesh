import { Settings } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title flex items-center gap-2"><Settings size={22} className="text-brand-400" /> Settings</h1>
        <p className="page-subtitle">Configure your ResuMesh preferences.</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-3xl">
        <div className="card p-6">
          <h2 className="font-semibold text-white mb-4">LLM Provider</h2>
          <p className="text-slate-400 text-sm mb-4">Choose your AI backend for career coaching and cover letter generation.</p>
          <div className="space-y-2">
            {['Ollama (Self-hosted)', 'Groq (Free API)', 'Google Gemini (Free tier)'].map((opt) => (
              <label key={opt} className="flex items-center gap-3 p-3 bg-dark-800 rounded-lg cursor-pointer border border-dark-500 hover:border-brand-600/40">
                <input type="radio" name="llm" className="accent-brand-500" defaultChecked={opt.includes('Ollama')} />
                <span className="text-sm text-slate-300">{opt}</span>
              </label>
            ))}
          </div>
        </div>
        <div className="card p-6">
          <h2 className="font-semibold text-white mb-4">Notifications</h2>
          <div className="space-y-3">
            {['Email on new match', 'Weekly summary report', 'Interview reminders'].map((opt) => (
              <label key={opt} className="flex items-center justify-between p-3 bg-dark-800 rounded-lg cursor-pointer">
                <span className="text-sm text-slate-300">{opt}</span>
                <input type="checkbox" className="accent-brand-500" />
              </label>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
