import { useAppStore } from '../stores/appStore';

export default function Inspector() {
  const { currentProject, inspectorData, environment } = useAppStore();

  return (
    <aside className="inspector">
      <div className="inspector__header">Inspector</div>

      {inspectorData && (
        <div className="inspector__section">
          <div className="inspector__label">Selected</div>
          <div className="inspector__value" style={{ fontSize: 13, fontFamily: 'var(--font-sans)' }}>
            {inspectorData.name || inspectorData.algorithm || 'Item'}
          </div>
          {inspectorData.metrics && (
            <div style={{ marginTop: 12 }}>
              {Object.entries(inspectorData.metrics).map(([key, val]) => {
                if (key === 'confusion_matrix' || key === 'class_names') return null;
                return (
                  <div key={key} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span className="inspector__label" style={{ marginBottom: 0 }}>{key}</span>
                    <span className="inspector__value">{typeof val === 'number' ? (val as number).toFixed(4) : String(val)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {currentProject && (
        <div className="inspector__section">
          <div className="inspector__label">Project</div>
          <div className="inspector__value" style={{ fontSize: 12, fontFamily: 'var(--font-sans)' }}>
            {currentProject.name}
          </div>
          <div className="inspector__label" style={{ marginTop: 8 }}>Type</div>
          <div className="inspector__value">{currentProject.project_type}</div>
          <div className="inspector__label" style={{ marginTop: 8 }}>Path</div>
          <div className="inspector__value" style={{ fontSize: 10, wordBreak: 'break-all' }}>{currentProject.path}</div>
        </div>
      )}

      {environment && (
        <div className="inspector__section">
          <div className="inspector__label">Environment</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
            {environment.os.system} {environment.os.machine}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Python {environment.python.version}
          </div>
          {environment.gpu?.available && (
            <div style={{ fontSize: 11, color: 'var(--accent-success)', marginTop: 4 }}>
              GPU: {environment.gpu.name}
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
