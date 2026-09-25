import { useAppStore } from '../stores/appStore';
import { PanelRight, ChevronLeft } from 'lucide-react';

export default function Header() {
  const { currentProject, backendConnected, toggleInspector, setActiveView, setCurrentProject } = useAppStore();

  return (
    <header className="app-header">
      <div className="app-header__logo">
        <img
          src="/assets/edgeforge-logo.png"
          alt="HowNik's EdgeForge"
          style={{ width: 26, height: 26, objectFit: 'contain' }}
        />
        <span>EdgeForge</span>
        <span style={{ fontWeight: 400, fontSize: 11, color: 'var(--text-muted)', marginLeft: 4 }}>by HowNik</span>
      </div>

      {currentProject && (
        <div className="app-header__nav">
          <button
            className="app-header__nav-btn"
            onClick={() => { setCurrentProject(null); setActiveView('welcome'); }}
            title="Back to projects"
          >
            <ChevronLeft size={14} style={{ marginRight: 2 }} />
            Projects
          </button>
          <span style={{ color: 'var(--text-muted)', fontSize: 12, display: 'flex', alignItems: 'center' }}>
            /&nbsp; {currentProject.name}
          </span>
        </div>
      )}

      <div className="app-header__spacer" />

      <div className="app-header__status">
        <div className={`app-header__status-dot`} style={{
          background: backendConnected ? 'var(--accent-success)' : 'var(--accent-error)',
          boxShadow: `0 0 6px ${backendConnected ? 'var(--accent-success)' : 'var(--accent-error)'}`,
        }} />
        {backendConnected ? 'Backend Connected' : 'Backend Offline'}
      </div>

      {currentProject && (
        <button
          className="app-header__nav-btn"
          onClick={toggleInspector}
          title="Toggle inspector"
        >
          <PanelRight size={14} />
        </button>
      )}
    </header>
  );
}
