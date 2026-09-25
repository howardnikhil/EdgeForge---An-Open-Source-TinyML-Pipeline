import { useState } from 'react';
import { useAppStore } from '../stores/appStore';
import api from '../utils/api';
import { Plus, FolderOpen, Trash2, Zap, Cpu, Database, Bot } from 'lucide-react';

export default function WelcomePage() {
  const { projects, loadProjects, setCurrentProject, setActiveView, addLog, backendConnected, environment } = useAppStore();
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [projectType, setProjectType] = useState('generic');
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setCreating(true);
    try {
      const project = await api.createProject({ name, description, project_type: projectType });
      addLog(`Project created: ${project.name}`);
      await loadProjects();
      setCurrentProject(project);
      setActiveView('dashboard');
      setShowCreate(false);
      setName('');
      setDescription('');
    } catch (e: any) {
      addLog(`ERROR: ${e.message}`);
    }
    setCreating(false);
  };

  const openProject = async (project: any) => {
    try {
      const full = await api.getProject(project.id);
      setCurrentProject(full);
      setActiveView('dashboard');
      addLog(`Opened project: ${full.name}`);
    } catch (e: any) {
      addLog(`ERROR: ${e.message}`);
    }
  };

  const deleteProject = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this project?')) return;
    try {
      await api.deleteProject(id, true);
      await loadProjects();
      addLog('Project deleted');
    } catch (err: any) {
      addLog(`ERROR: ${err.message}`);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', paddingTop: 40 }}>
      {/* Hero */}
      <div style={{ textAlign: 'center', marginBottom: 48 }}>
        <div style={{ marginBottom: 16 }}>
          <img
            src="/assets/edgeforge-logo.png"
            alt="HowNik's EdgeForge"
            style={{ width: 64, height: 64, objectFit: 'contain' }}
          />
        </div>
        <h1 style={{ fontSize: 32, fontWeight: 800, marginBottom: 8 }}>
          <span className="gradient-text">HowNik's EdgeForge</span>
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 15, maxWidth: 500, margin: '0 auto' }}>
          Open-source TinyML / Edge-AI Engineering IDE.
          From sensor data to deployed firmware.
        </p>
        <div style={{ display: 'flex', gap: 24, justifyContent: 'center', marginTop: 24 }}>
          {[
            { icon: Database, label: 'Data Collection' },
            { icon: Zap, label: 'AutoML Training' },
            { icon: Cpu, label: 'MCU Deployment' },
            { icon: Bot, label: 'AI Assistant' },
          ].map((f) => (
            <div key={f.label} style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: 12 }}>
              <f.icon size={14} /> {f.label}
            </div>
          ))}
        </div>
      </div>

      {!backendConnected && (
        <div className="card" style={{ marginBottom: 24, borderColor: 'var(--accent-error)' }}>
          <div className="card__body" style={{ textAlign: 'center', color: 'var(--accent-error)' }}>
            <p style={{ fontWeight: 600, marginBottom: 4 }}>Backend Not Connected</p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Start the backend: <code style={{ color: 'var(--text-primary)' }}>cd apps/backend && python main.py</code>
            </p>
          </div>
        </div>
      )}

      {/* Create project */}
      {!showCreate ? (
        <button className="btn btn--primary btn--lg" onClick={() => setShowCreate(true)} style={{ width: '100%', justifyContent: 'center', marginBottom: 32 }}>
          <Plus size={18} /> New Project
        </button>
      ) : (
        <div className="card" style={{ marginBottom: 32 }}>
          <div className="card__header">
            <span className="card__title">New Project</span>
            <button className="btn btn--ghost btn--sm" onClick={() => setShowCreate(false)}>Cancel</button>
          </div>
          <div className="card__body">
            <div className="form-group">
              <label className="form-label">Project Name</label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="My TinyML Project" autoFocus />
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea className="textarea" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional description..." rows={2} />
            </div>
            <div className="form-group">
              <label className="form-label">Project Type</label>
              <div className="radio-group">
                {[
                  { value: 'sensor', label: 'Sensor / Time Series', desc: 'IMU, temperature, pressure, etc.' },
                  { value: 'audio', label: 'Audio', desc: 'Microphone, sound classification' },
                  { value: 'vision', label: 'Vision', desc: 'Camera, image classification' },
                  { value: 'generic', label: 'Generic ML', desc: 'Custom data and models' },
                ].map((opt) => (
                  <label key={opt.value} className={`radio-option ${projectType === opt.value ? 'radio-option--selected' : ''}`}>
                    <input type="radio" name="type" value={opt.value} checked={projectType === opt.value} onChange={() => setProjectType(opt.value)} />
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 500 }}>{opt.label}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{opt.desc}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
            <button className="btn btn--primary" onClick={handleCreate} disabled={!name.trim() || creating} style={{ width: '100%', justifyContent: 'center' }}>
              {creating ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </div>
      )}

      {/* Project list */}
      {projects.length > 0 && (
        <div>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>Recent Projects</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {projects.map((p) => (
              <div
                key={p.id}
                className="card"
                style={{ cursor: 'pointer', transition: 'var(--transition-fast)' }}
                onClick={() => openProject(p)}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--border-secondary)')}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-primary)')}
              >
                <div className="card__body" style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
                  <FolderOpen size={18} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{p.name}</div>
                    {p.description && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{p.description}</div>}
                  </div>
                  <span className="badge badge--neutral">{p.project_type}</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {new Date(p.updated_at).toLocaleDateString()}
                  </span>
                  <button
                    className="btn btn--ghost btn--sm"
                    onClick={(e) => deleteProject(p.id, e)}
                    title="Delete project"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{ textAlign: 'center', marginTop: 48, paddingBottom: 32 }}>
        <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          HowNik's EdgeForge v0.1.0 · Apache License 2.0 · Open Source
        </p>
        {environment && (
          <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
            {environment.os.system} {environment.os.machine} · Python {environment.python.version}
          </p>
        )}
      </div>
    </div>
  );
}
