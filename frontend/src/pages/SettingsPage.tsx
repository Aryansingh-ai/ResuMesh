import { useState, useEffect } from 'react';
import { Settings, Key, Check, Eye, EyeOff, Zap } from 'lucide-react';
import clsx from 'clsx';

const LLM_PROVIDERS = [
  {
    id: 'groq',
    label: 'Groq',
    badge: 'Default',
    description: 'Free & fast · llama-3.1-8b-instant',
    requiresKey: true,
    keyPlaceholder: 'gsk_...',
    keyLink: 'https://console.groq.com/keys',
  },
  {
    id: 'gemini',
    label: 'Google Gemini',
    badge: 'Free tier',
    description: 'gemini-1.5-flash · generous free quota',
    requiresKey: true,
    keyPlaceholder: 'AIza...',
    keyLink: 'https://aistudio.google.com/app/apikey',
  },
  {
    id: 'openai',
    label: 'OpenAI ChatGPT',
    badge: 'Paid',
    description: 'gpt-4o-mini · best quality',
    requiresKey: true,
    keyPlaceholder: 'sk-...',
    keyLink: 'https://platform.openai.com/api-keys',
  },
  {
    id: 'deepseek',
    label: 'DeepSeek',
    badge: 'Cheap',
    description: 'deepseek-chat · very affordable',
    requiresKey: true,
    keyPlaceholder: 'sk-...',
    keyLink: 'https://platform.deepseek.com/api_keys',
  },
  {
    id: 'openrouter',
    label: 'OpenRouter',
    badge: 'Multi-model',
    description: 'Access 100+ models with one key',
    requiresKey: true,
    keyPlaceholder: 'sk-or-...',
    keyLink: 'https://openrouter.ai/keys',
  },
  {
    id: 'ollama',
    label: 'Ollama',
    badge: 'Self-hosted',
    description: 'Run locally · no API key needed',
    requiresKey: false,
    keyPlaceholder: '',
    keyLink: 'https://ollama.com',
  },
];

const STORAGE_KEY_PROVIDER = 'resumesh_llm_provider';
const STORAGE_KEY_APIKEY = 'resumesh_llm_apikey';

export function getLLMHeaders(): Record<string, string> {
  const provider = localStorage.getItem(STORAGE_KEY_PROVIDER) || 'groq';
  const apiKey = localStorage.getItem(STORAGE_KEY_APIKEY) || '';
  const headers: Record<string, string> = { 'x-llm-provider': provider };
  if (apiKey) headers['x-llm-api-key'] = apiKey;
  return headers;
}

export default function SettingsPage() {
  const [selectedProvider, setSelectedProvider] = useState('groq');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSelectedProvider(localStorage.getItem(STORAGE_KEY_PROVIDER) || 'groq');
    setApiKey(localStorage.getItem(STORAGE_KEY_APIKEY) || '');
  }, []);

  const handleSave = () => {
    localStorage.setItem(STORAGE_KEY_PROVIDER, selectedProvider);
    localStorage.setItem(STORAGE_KEY_APIKEY, apiKey);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const currentProvider = LLM_PROVIDERS.find((p) => p.id === selectedProvider)!;

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title flex items-center gap-2">
          <Settings size={22} className="text-brand-400" /> Settings
        </h1>
        <p className="page-subtitle">Configure your ResuMesh preferences and AI provider.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-3xl">
        {/* LLM Provider */}
        <div className="lg:col-span-2 card p-6">
          <h2 className="font-semibold text-white mb-1 flex items-center gap-2">
            <Zap size={16} className="text-brand-400" /> LLM Provider
          </h2>
          <p className="text-slate-400 text-sm mb-5">
            Choose your AI backend for cover letter generation and career coaching.
          </p>

          <div className="space-y-2 mb-5">
            {LLM_PROVIDERS.map((p) => (
              <label
                key={p.id}
                onClick={() => { setSelectedProvider(p.id); setApiKey(''); }}
                className={clsx(
                  'flex items-center gap-3 p-3.5 rounded-xl cursor-pointer border transition-all duration-150',
                  selectedProvider === p.id
                    ? 'border-brand-500 bg-brand-900/20'
                    : 'border-dark-500 bg-dark-800 hover:border-brand-600/40'
                )}
              >
                <div className={clsx(
                  'w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all',
                  selectedProvider === p.id ? 'border-brand-400 bg-brand-500' : 'border-dark-400'
                )}>
                  {selectedProvider === p.id && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white">{p.label}</span>
                    <span className={clsx(
                      'text-[10px] px-1.5 py-0.5 rounded font-medium',
                      p.badge === 'Default' ? 'bg-brand-900/60 text-brand-300 border border-brand-700/40' :
                      p.badge === 'Free tier' ? 'bg-green-900/50 text-green-300' :
                      p.badge === 'Self-hosted' ? 'bg-slate-800 text-slate-400' :
                      'bg-dark-700 text-slate-400'
                    )}>
                      {p.badge}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">{p.description}</p>
                </div>
              </label>
            ))}
          </div>

          {/* API Key input — shown for providers that require a key */}
          {currentProvider?.requiresKey && (
            <div className="mb-5 p-4 bg-dark-800 rounded-xl border border-dark-600">
              <label className="label flex items-center gap-1.5 mb-2">
                <Key size={12} className="text-brand-400" />
                {currentProvider.label} API Key
                <a
                  href={currentProvider.keyLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] text-brand-400 hover:text-brand-300 underline ml-auto"
                >
                  Get key ↗
                </a>
              </label>
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={currentProvider.keyPlaceholder}
                  className="input pr-10 font-mono text-sm"
                />
                <button
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              <p className="text-[11px] text-slate-600 mt-2">
                🔒 Stored locally in your browser only — never sent to our servers except as an API call header.
              </p>
            </div>
          )}

          <button
            onClick={handleSave}
            className={clsx('btn-primary flex items-center gap-2', saved && 'bg-green-600 border-green-500 hover:bg-green-600')}
          >
            {saved ? <><Check size={15} /> Saved!</> : 'Save Settings'}
          </button>
        </div>

        {/* Notifications */}
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
