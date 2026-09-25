import { useAppStore } from '../stores/appStore';

export default function BottomPanel() {
  const { logs, bottomPanelTab, setBottomPanelTab } = useAppStore();

  return (
    <div className="bottom-panel">
      <div className="bottom-panel__tabs">
        {['output', 'logs', 'serial'].map((tab) => (
          <button
            key={tab}
            className={`bottom-panel__tab ${bottomPanelTab === tab ? 'bottom-panel__tab--active' : ''}`}
            onClick={() => setBottomPanelTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>
      <div className="bottom-panel__content">
        {bottomPanelTab === 'output' && (
          logs.length === 0
            ? <span style={{ color: 'var(--text-muted)' }}>No output yet.</span>
            : logs.map((log, i) => <div key={i}>{log}</div>)
        )}
        {bottomPanelTab === 'logs' && (
          logs.filter(l => l.includes('ERROR') || l.includes('WARN')).length === 0
            ? <span style={{ color: 'var(--text-muted)' }}>No errors or warnings.</span>
            : logs.filter(l => l.includes('ERROR') || l.includes('WARN')).map((log, i) => (
              <div key={i} style={{ color: log.includes('ERROR') ? 'var(--accent-error)' : 'var(--accent-warning)' }}>{log}</div>
            ))
        )}
        {bottomPanelTab === 'serial' && (
          <span style={{ color: 'var(--text-muted)' }}>Connect a serial device to see output.</span>
        )}
      </div>
    </div>
  );
}
