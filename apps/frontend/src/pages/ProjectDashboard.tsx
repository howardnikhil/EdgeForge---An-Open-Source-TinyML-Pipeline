import { useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import { formatExperimentMetric, detectTaskType, formatAccuracy, formatR2 } from '../utils/metrics';

export default function ProjectDashboard() {
  const { currentProject, datasets, experiments, models, loadProjectData } = useAppStore();

  useEffect(() => {
    if (currentProject?.id) {
      loadProjectData(currentProject.id);
    }
  }, [currentProject?.id]);

  const completedExps = experiments.filter(e => e.status === 'completed');

  const classExps = completedExps.filter(e => detectTaskType(e) === 'classification');
  const regExps = completedExps.filter(e => detectTaskType(e) === 'regression');

  // Best classification accuracy
  let bestClassAcc: number | null = null;
  for (const exp of classExps) {
    const formatted = formatExperimentMetric(exp);
    if (formatted.raw !== null) {
      if (bestClassAcc === null || formatted.raw > bestClassAcc) {
        bestClassAcc = formatted.raw;
      }
    }
  }

  // Best regression R²
  let bestRegR2: number | null = null;
  for (const exp of regExps) {
    const formatted = formatExperimentMetric(exp);
    if (formatted.raw !== null) {
      if (bestRegR2 === null || formatted.raw > bestRegR2) {
        bestRegR2 = formatted.raw;
      }
    }
  }

  const hasClass = classExps.length > 0;
  const hasReg = regExps.length > 0;
  const isMixed = hasClass && hasReg;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">{currentProject?.name}</h1>
          <p className="page-subtitle">{currentProject?.description || currentProject?.project_type + ' project'}</p>
        </div>
      </div>

      <div className="stat-grid" style={{ marginBottom: 32 }}>
        <div className="stat-card">
          <div className="stat-card__label">Datasets</div>
          <div className="stat-card__value">{datasets.length}</div>
          <div className="stat-card__sub">
            {datasets.reduce((sum, d) => sum + (d.num_samples || 0), 0).toLocaleString()} total samples
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">Experiments</div>
          <div className="stat-card__value">{experiments.length}</div>
          <div className="stat-card__sub">{completedExps.length} completed</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">Models</div>
          <div className="stat-card__value">{models.length}</div>
        </div>

        {/* Task-Aware Best Metric Cards */}
        {isMixed ? (
          <>
            <div className="stat-card">
              <div className="stat-card__label">BEST CLASSIFICATION ACCURACY</div>
              <div className="stat-card__value" style={{ color: bestClassAcc !== null ? 'var(--accent-success)' : 'var(--text-muted)' }}>
                {formatAccuracy(bestClassAcc)}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-card__label">BEST REGRESSION R²</div>
              <div className="stat-card__value" style={{ color: bestRegR2 !== null ? 'var(--accent-primary)' : 'var(--text-muted)' }}>
                {formatR2(bestRegR2)}
              </div>
            </div>
          </>
        ) : hasReg ? (
          <div className="stat-card">
            <div className="stat-card__label">BEST TEST R²</div>
            <div className="stat-card__value" style={{ color: bestRegR2 !== null ? 'var(--accent-primary)' : 'var(--text-muted)' }}>
              {formatR2(bestRegR2)}
            </div>
          </div>
        ) : (
          <div className="stat-card">
            <div className="stat-card__label">BEST TEST ACCURACY</div>
            <div className="stat-card__value" style={{ color: bestClassAcc !== null ? 'var(--accent-success)' : 'var(--text-muted)' }}>
              {formatAccuracy(bestClassAcc)}
            </div>
          </div>
        )}
      </div>

      {/* Recent experiments */}
      {completedExps.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card__header">
            <span className="card__title">Recent Experiments</span>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Algorithm</th>
                  <th>Status</th>
                  <th>Test Metric</th>
                  <th>Model Size</th>
                  <th>Duration</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {completedExps.slice(0, 10).map((exp) => {
                  const metricInfo = formatExperimentMetric(exp);
                  return (
                    <tr key={exp.id}>
                      <td style={{ fontWeight: 500 }}>{exp.algorithm}</td>
                      <td>
                        <span className={`badge badge--${exp.status === 'completed' ? 'success' : exp.status === 'failed' ? 'error' : 'warning'}`}>
                          {exp.status}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>
                        {metricInfo.value}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                        {exp.model_size_bytes ? formatBytes(exp.model_size_bytes) : '—'}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                        {exp.duration_seconds ? `${exp.duration_seconds.toFixed(1)}s` : '—'}
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {new Date(exp.created_at).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Project files */}
      {currentProject?.files && currentProject.files.length > 0 && (
        <div className="card">
          <div className="card__header">
            <span className="card__title">Project Files</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{currentProject.files.length} files</span>
          </div>
          <div className="card__body" style={{ maxHeight: 300, overflow: 'auto' }}>
            {currentProject.files.map((f: string, i: number) => (
              <div key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)', padding: '2px 0' }}>
                {f}
              </div>
            ))}
          </div>
        </div>
      )}

      {datasets.length === 0 && experiments.length === 0 && (
        <div className="empty-state">
          <div className="empty-state__icon">📊</div>
          <div className="empty-state__title">Get Started</div>
          <div className="empty-state__description">
            Import a dataset or connect a serial device to begin collecting data.
          </div>
        </div>
      )}
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}
