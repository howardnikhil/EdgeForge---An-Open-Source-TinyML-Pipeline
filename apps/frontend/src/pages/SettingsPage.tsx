import { useState, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import api from '../utils/api';
import { Save, Eye, EyeOff } from 'lucide-react';

const AI_PROVIDERS = [
  { id: 'openai', name: 'OpenAI', keyName: 'ai_api_key_openai', modelKey: 'ai_model_openai', defaultModel: 'gpt-4o-mini' },
  { id: 'anthropic', name: 'Anthropic', keyName: 'ai_api_key_anthropic', modelKey: 'ai_model_anthropic', defaultModel: 'claude-3-5-haiku-20241022' },
  { id: 'gemini', name: 'Google Gemini', keyName: 'ai_api_key_gemini', modelKey: 'ai_model_gemini', defaultModel: 'gemini-2.0-flash' },
  { id: 'openrouter', name: 'OpenRouter', keyName: 'ai_api_key_openrouter', modelKey: 'ai_model_openrouter', defaultModel: 'auto' },
  { id: 'ollama', name: 'Ollama (Local)', keyName: 'ai_api_key_ollama', modelKey: 'ai_model_ollama', defaultModel: 'llama3' },
];

export default function SettingsPage() {
  const { environment, addLog } = useAppStore();
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [models, setModels] = useState<Record<string, string>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('general');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const settings = await api.listSettings();
      const keys: Record<string, string> = {};
      const mods: Record<string, string> = {};
      settings.forEach((s: any) => {
        if (s.key.startsWith('ai_api_key_')) keys[s.key] = s.has_value ? '********' : '';
        if (s.key.startsWith('ai_model_')) mods[s.key] = s.value || '';
      });
      setApiKeys(keys);
      setModels(mods);
    } catch (err: any) {
      addLog(`Failed to load settings: ${err.message}`);
    }
  };

  const saveApiKey = async (keyName: string, value: string) => {
    if (value === '********') return; // Don't save masked value
    setSaving(true);
    try {
      await api.updateSetting(keyName, value, 'ai_providers');
      addLog(`API key saved: ${keyName}`);
    } catch (err: any) {
      addLog(`ERROR: ${err.message}`);
    }
    setSaving(false);
  };

  const saveModel = async (modelKey: string, value: string) => {
    try {
      await api.updateSetting(modelKey, value, 'ai_providers');
      addLog(`Model setting saved: ${modelKey}`);
    } catch (err: any) {
      addLog(`ERROR: ${err.message}`);
    }
  };

  const tabs = [
    { id: 'general', label: 'General' },
    { id: 'ai', label: 'AI Providers' },
    { id: 'environment', label: 'Environment' },
    { id: 'about', label: 'About' },
  ];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
      </div>

      <div style={{ display: 'flex', gap: 24 }}>
        {/* Tab nav */}
        <div style={{ width: 180, flexShrink: 0 }}>
          {tabs.map(t => (
            <button
              key={t.id}
              className={`sidebar__item ${activeTab === t.id ? 'sidebar__item--active' : ''}`}
              onClick={() => setActiveTab(t.id)}
              style={{ borderRight: 'none' }}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div style={{ flex: 1 }}>
          {activeTab === 'general' && (
            <div className="card">
              <div className="card__header"><span className="card__title">General Settings</span></div>
              <div className="card__body">
                <div className="form-group">
                  <label className="form-label">Theme</label>
                  <select className="select" style={{ maxWidth: 200 }}>
                    <option>Dark</option>
                  </select>
                  <div className="form-help">More themes coming in future versions.</div>
                </div>
                <div className="form-group">
                  <label className="form-label">Default Training Seed</label>
                  <input className="input" type="number" defaultValue={42} style={{ maxWidth: 120 }} />
                </div>
                <div className="form-group">
                  <label className="form-label">Default Test Split</label>
                  <input className="input" type="number" defaultValue={0.2} step={0.05} min={0.1} max={0.5} style={{ maxWidth: 120 }} />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'ai' && (
            <div>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
                Configure AI providers for the assistant. Your API keys are stored locally and never sent to EdgeForge servers.
              </p>
              {AI_PROVIDERS.map(p => (
                <div key={p.id} className="card" style={{ marginBottom: 16 }}>
                  <div className="card__header"><span className="card__title">{p.name}</span></div>
                  <div className="card__body">
                    <div className="form-group">
                      <label className="form-label">API Key</label>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <input
                          className="input"
                          type={showKeys[p.id] ? 'text' : 'password'}
                          value={apiKeys[p.keyName] || ''}
                          onChange={(e) => setApiKeys(prev => ({ ...prev, [p.keyName]: e.target.value }))}
                          placeholder={p.id === 'ollama' ? 'Not required for Ollama' : `Enter ${p.name} API key`}
                        />
                        <button className="btn btn--ghost" onClick={() => setShowKeys(prev => ({ ...prev, [p.id]: !prev[p.id] }))}>
                          {showKeys[p.id] ? <EyeOff size={14} /> : <Eye size={14} />}
                        </button>
                        <button className="btn btn--secondary" onClick={() => saveApiKey(p.keyName, apiKeys[p.keyName] || '')} disabled={saving}>
                          <Save size={14} />
                        </button>
                      </div>
                    </div>
                    <div className="form-group" style={{ marginBottom: 0 }}>
                      <label className="form-label">Model</label>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <input
                          className="input"
                          value={models[p.modelKey] || p.defaultModel}
                          onChange={(e) => setModels(prev => ({ ...prev, [p.modelKey]: e.target.value }))}
                          placeholder={p.defaultModel}
                        />
                        <button className="btn btn--secondary" onClick={() => saveModel(p.modelKey, models[p.modelKey] || p.defaultModel)}>
                          <Save size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'environment' && environment && (
            <div className="card">
              <div className="card__header"><span className="card__title">System Environment</span></div>
              <div className="card__body">
                <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: '8px 16px', fontSize: 13 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Operating System</span>
                  <span>{environment.os.system} {environment.os.release}</span>
                  <span style={{ color: 'var(--text-muted)' }}>Architecture</span>
                  <span>{environment.os.machine}</span>
                  <span style={{ color: 'var(--text-muted)' }}>Python</span>
                  <span>{environment.python.version}</span>
                  <span style={{ color: 'var(--text-muted)' }}>GPU</span>
                  <span>{environment.gpu?.available ? `${environment.gpu.name} (${environment.gpu.type})` : 'None detected'}</span>
                </div>

                <div className="separator" />
                <h4 style={{ fontSize: 13, marginBottom: 8 }}>ML Frameworks</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: '4px 16px', fontSize: 12 }}>
                  {Object.entries(environment.ml_frameworks).map(([name, info]: [string, any]) => (
                    <div key={name} style={{ display: 'contents' }}>
                      <span style={{ color: 'var(--text-muted)' }}>{name}</span>
                      <span style={{ color: info.available ? 'var(--accent-success)' : 'var(--text-muted)' }}>
                        {info.available ? `✓ ${info.version}` : '✗ Not installed'}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="separator" />
                <h4 style={{ fontSize: 13, marginBottom: 8 }}>Toolchains</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: '4px 16px', fontSize: 12 }}>
                  {Object.entries(environment.toolchains).map(([name, available]: [string, any]) => (
                    <div key={name} style={{ display: 'contents' }}>
                      <span style={{ color: 'var(--text-muted)' }}>{name}</span>
                      <span style={{ color: available ? 'var(--accent-success)' : 'var(--text-muted)' }}>
                        {available ? '✓ Installed' : '✗ Not installed'}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="separator" />
                <h4 style={{ fontSize: 13, marginBottom: 8 }}>Emulators</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: '4px 16px', fontSize: 12 }}>
                  {Object.entries(environment.emulators).map(([name, available]: [string, any]) => (
                    <div key={name} style={{ display: 'contents' }}>
                      <span style={{ color: 'var(--text-muted)' }}>{name}</span>
                      <span style={{ color: available ? 'var(--accent-success)' : 'var(--text-muted)' }}>
                        {available ? '✓ Available' : '✗ Not installed'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'about' && (
            <div className="card">
              <div className="card__header"><span className="card__title">About EdgeForge</span></div>
              <div className="card__body" style={{ textAlign: 'center', padding: 32 }}>
                <div style={{ marginBottom: 16 }}>
                  <img
                    src="/assets/edgeforge-logo.png"
                    alt="HowNik's EdgeForge"
                    style={{ width: 64, height: 64, objectFit: 'contain' }}
                  />
                </div>
                <h2 style={{ fontSize: 24, fontWeight: 800, marginBottom: 8 }}>
                  <span className="gradient-text">HowNik's EdgeForge</span>
                </h2>
                <p style={{ color: 'var(--text-secondary)', marginBottom: 4 }}>Version 0.1.0</p>
                <p style={{ color: 'var(--text-muted)', fontSize: 13, maxWidth: 400, margin: '0 auto' }}>
                  Open-source TinyML / Edge-AI Engineering IDE.
                  Local-first. From sensor data to deployed firmware.
                </p>
                <div className="separator" />
                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Apache License 2.0</p>
                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>© 2024 HowNik. All rights reserved.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
