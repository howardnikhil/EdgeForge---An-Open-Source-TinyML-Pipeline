import { useState, useRef, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import api from '../utils/api';
import { Send, Bot, User } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function AIAssistantPage() {
  const { currentProject, addLog } = useAppStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState('openai');
  const [providers, setProviders] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listAIProviders().then(setProviders).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: 'user', content: input.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const result = await api.chat({
        project_id: currentProject?.id,
        messages: [...messages, userMsg].map(m => ({ role: m.role, content: m.content })),
        provider,
      });
      setMessages(prev => [...prev, { role: 'assistant', content: result.response }]);
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
      addLog(`AI ERROR: ${err.message}`);
    }
    setLoading(false);
  };

  const configuredProviders = providers.filter(p => p.configured);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="page-header" style={{ flexShrink: 0 }}>
        <div>
          <h1 className="page-title">AI Assistant</h1>
          <p className="page-subtitle">Ask questions about your project, models, and hardware</p>
        </div>
        <select className="select" style={{ width: 180 }} value={provider} onChange={(e) => setProvider(e.target.value)}>
          {providers.map(p => (
            <option key={p.id} value={p.id}>{p.name} {p.configured ? '✓' : '(no key)'}</option>
          ))}
        </select>
      </div>

      {configuredProviders.length === 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card__body" style={{ textAlign: 'center', color: 'var(--accent-warning)', fontSize: 13 }}>
            No AI providers configured. Go to Settings → AI Providers to add your API key.
          </div>
        </div>
      )}

      {/* Messages */}
      <div style={{ flex: 1, overflow: 'auto', marginBottom: 16 }}>
        {messages.length === 0 && (
          <div className="empty-state" style={{ padding: 48 }}>
            <Bot size={40} style={{ color: 'var(--text-muted)', marginBottom: 16 }} />
            <div className="empty-state__title">EdgeForge AI</div>
            <div className="empty-state__description">
              Ask about your data, models, hardware compatibility, or get help with TinyML workflows.
            </div>
            <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
              {[
                'Analyze my dataset',
                'Which model fits ESP32-S3?',
                'Explain INT8 quantization',
                'Compare my experiments',
              ].map(q => (
                <button key={q} className="btn btn--secondary btn--sm" onClick={() => { setInput(q); }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{
            display: 'flex', gap: 12, padding: '12px 0',
            borderBottom: '1px solid var(--border-primary)',
          }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
              background: msg.role === 'user' ? 'var(--accent-primary)' : 'var(--accent-secondary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              {msg.role === 'user' ? <User size={14} color="white" /> : <Bot size={14} color="white" />}
            </div>
            <div style={{ flex: 1, fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', gap: 12, padding: '12px 0' }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
              background: 'var(--accent-secondary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Bot size={14} color="white" />
            </div>
            <div className="loading-pulse" style={{ fontSize: 13, color: 'var(--text-muted)' }}>Thinking...</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
        <input
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask EdgeForge AI..."
          disabled={loading}
        />
        <button className="btn btn--primary" onClick={send} disabled={loading || !input.trim()}>
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
