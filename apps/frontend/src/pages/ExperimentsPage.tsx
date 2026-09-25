import { useEffect, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import api from '../utils/api';
import { Download, Trash2, AlertTriangle, Info } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import {
  detectTaskType,
  formatExperimentMetric,
  prepareChartData,
} from '../utils/metrics';

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4'];

export default function ExperimentsPage() {
  const { currentProject, experiments, addLog, loadProjectData, setInspectorData } = useAppStore();
  const [selected, setSelected] = useState<any>(null);
  const [taskFilter, setTaskFilter] = useState<'all' | 'classification' | 'regression'>('all');

  useEffect(() => {
    if (currentProject?.id) loadProjectData(currentProject.id);
  }, [currentProject?.id]);

  const selectExperiment = async (exp: any) => {
    try {
      const detail = await api.getExperiment(exp.id);
      setSelected(detail);
      setInspectorData(detail);
    } catch (err: any) {
      addLog(`ERROR: ${err.message}`);
    }
  };

  const exportOnnx = async (expId: string) => {
    try {
      const result = await api.exportOnnx(expId);
      addLog(`ONNX export: ${formatBytes(result.size_bytes)} (original: ${formatBytes(result.original_size_bytes)})`);
    } catch (err: any) {
      addLog(`ERROR ONNX export: ${err.message}`);
    }
  };

  const exportCArray = async (expId: string) => {
    try {
      const result = await api.exportCArray(expId);
      addLog(`C array export: ${formatBytes(result.size_bytes)}`);
    } catch (err: any) {
      addLog(`ERROR C array export: ${err.message}`);
    }
  };

  const deleteExp = async (id: string) => {
    if (!confirm('Delete experiment?')) return;
    try {
      await api.deleteExperiment(id);
      await loadProjectData(currentProject!.id);
      if (selected?.id === id) setSelected(null);
      addLog('Experiment deleted');
    } catch (err: any) {
      addLog(`ERROR: ${err.message}`);
    }
  };

  const completed = experiments.filter(e => e.status === 'completed');
  const classCount = completed.filter(e => detectTaskType(e) === 'classification').length;
  const regCount = completed.filter(e => detectTaskType(e) === 'regression').length;

  const classChartData = prepareChartData(completed, 'classification');
  const regChartData = prepareChartData(completed, 'regression');

  const filteredExperiments = experiments.filter(e => {
    if (taskFilter === 'all') return true;
    return detectTaskType(e) === taskFilter;
  });

  const getRegressionDomain = (data: any[]): [number, number] => {
    if (data.length === 0) return [-0.5, 1.0];
    const scores = data.map(d => d.score);
    const minS = Math.min(...scores);
    const maxS = Math.max(...scores);
    const pad = Math.abs(maxS - minS) * 0.15 || 0.2;
    const lower = minS < 0 ? Math.floor((minS - pad) * 10) / 10 : 0;
    const upper = Math.min(1.0, Math.ceil((maxS + pad) * 10) / 10);
    return [lower, upper];
  };

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Experiments</h1>
          <p className="page-subtitle">
            {experiments.length} experiments · {completed.length} completed
            {classCount > 0 && regCount > 0 && ` (${classCount} classification, ${regCount} regression)`}
          </p>
        </div>

        {/* Task Filter Toolbar */}
        {(classCount > 0 && regCount > 0) && (
          <div style={{ display: 'flex', gap: 6, background: 'var(--bg-elevated)', padding: 4, borderRadius: 8, border: '1px solid var(--border-primary)' }}>
            <button
              className={`btn btn--sm ${taskFilter === 'all' ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setTaskFilter('all')}
            >
              All Tasks ({experiments.length})
            </button>
            <button
              className={`btn btn--sm ${taskFilter === 'classification' ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setTaskFilter('classification')}
            >
              Classification ({classCount})
            </button>
            <button
              className={`btn btn--sm ${taskFilter === 'regression' ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setTaskFilter('regression')}
            >
              Regression ({regCount})
            </button>
          </div>
        )}
      </div>

      {/* Classification Chart */}
      {(taskFilter === 'all' || taskFilter === 'classification') && classChartData.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card__header">
            <span className="card__title">Model Comparison — Test Accuracy</span>
          </div>
          <div className="card__body" style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={classChartData}>
                <XAxis dataKey="name" fontSize={11} stroke="var(--text-muted)" />
                <YAxis
                  fontSize={11}
                  stroke="var(--text-muted)"
                  domain={[0, 100]}
                  unit="%"
                />
                <Tooltip
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-secondary)', borderRadius: 6, fontSize: 12 }}
                  formatter={(_val: any, _, item: any) => [`${item.payload.displayValue}`, 'Test Accuracy']}
                />
                <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                  {classChartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Regression Chart */}
      {(taskFilter === 'all' || taskFilter === 'regression') && regChartData.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="card__title">Model Comparison — Test R²</span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Baseline: Mean Predictor (R² = 0.000)</span>
          </div>
          <div className="card__body" style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={regChartData}>
                <XAxis dataKey="name" fontSize={11} stroke="var(--text-muted)" />
                <YAxis
                  fontSize={11}
                  stroke="var(--text-muted)"
                  domain={getRegressionDomain(regChartData)}
                />
                <ReferenceLine
                  y={0}
                  stroke="#f59e0b"
                  strokeDasharray="3 3"
                  label={{ value: 'Mean Baseline (R²=0)', fill: 'var(--text-muted)', fontSize: 10, position: 'insideTopRight' }}
                />
                <Tooltip
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-secondary)', borderRadius: 6, fontSize: 12 }}
                  formatter={(_val: any, _, item: any) => [`R² ${item.payload.displayValue}`, 'Test R²']}
                />
                <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                  {regChartData.map((d, i) => (
                    <Cell key={i} fill={d.score < 0 ? '#ef4444' : COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {completed.length > 0 && classChartData.length === 0 && regChartData.length === 0 && (
        <div className="card" style={{ marginBottom: 24, padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
          No evaluation metrics available for the selected experiments.
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 1fr' : '1fr', gap: 24 }}>
        {/* Experiment list */}
        <div className="card">
          <div className="card__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="card__title">All Experiments</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{filteredExperiments.length} items</span>
          </div>
          <div className="table-container" style={{ maxHeight: 500, overflow: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>Algorithm</th>
                  <th>Status</th>
                  <th>Test Metric</th>
                  <th>CV Metric</th>
                  <th>Fit / Quality</th>
                  <th>Size</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filteredExperiments.map((exp) => {
                  const metricInfo = formatExperimentMetric(exp);
                  return (
                    <tr key={exp.id} onClick={() => selectExperiment(exp)} style={{ cursor: 'pointer' }}>
                      <td style={{ fontWeight: 500 }}>
                        {exp.algorithm}
                        <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 6 }}>({metricInfo.taskType})</span>
                      </td>
                      <td>
                        <span className={`badge badge--${exp.status === 'completed' ? 'success' : exp.status === 'failed' ? 'error' : 'warning'}`}>
                          {exp.status}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>
                        {metricInfo.value}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)' }}>
                        {metricInfo.cvValue}
                      </td>
                      <td>
                        {metricInfo.interpretation ? (
                          <span className={`badge badge--${metricInfo.interpretation.badgeVariant}`}>
                            {metricInfo.interpretation.rating}
                          </span>
                        ) : '—'}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                        {exp.model_size_bytes ? formatBytes(exp.model_size_bytes) : '—'}
                      </td>
                      <td>
                        <button className="btn btn--ghost btn--sm" onClick={(e) => { e.stopPropagation(); deleteExp(exp.id); }}>
                          <Trash2 size={12} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Experiment detail */}
        {selected && (
          <div>
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card__header">
                <span className="card__title">{selected.algorithm}</span>
                <span className={`badge badge--${selected.status === 'completed' ? 'success' : 'error'}`}>{selected.status}</span>
              </div>
              <div className="card__body">
                {(() => {
                  const selMetric = formatExperimentMetric(selected);
                  return (
                    <div>
                      <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 16 }}>
                        <div className="stat-card">
                          <div className="stat-card__label">{selMetric.label}</div>
                          <div
                            className="stat-card__value"
                            style={{
                              fontSize: 20,
                              color: selMetric.interpretation?.isWorseThanBaseline
                                ? 'var(--accent-error)'
                                : 'var(--accent-success)',
                            }}
                          >
                            {selMetric.value}
                          </div>
                        </div>

                        {selMetric.secondaryLabel && selMetric.secondaryValue && (
                          <div className="stat-card">
                            <div className="stat-card__label">{selMetric.secondaryLabel}</div>
                            <div className="stat-card__value" style={{ fontSize: 20 }}>
                              {selMetric.secondaryValue}
                            </div>
                          </div>
                        )}

                        <div className="stat-card">
                          <div className="stat-card__label">Duration</div>
                          <div className="stat-card__value" style={{ fontSize: 16 }}>
                            {selected.duration_seconds ? `${selected.duration_seconds.toFixed(2)}s` : '—'}
                          </div>
                        </div>
                      </div>

                      {/* Regression Interpretation & Baseline Box */}
                      {selMetric.taskType === 'regression' && selMetric.interpretation && (
                        <div
                          style={{
                            background: selMetric.interpretation.isWorseThanBaseline
                              ? 'rgba(239, 68, 68, 0.1)'
                              : 'var(--bg-elevated)',
                            border: `1px solid ${
                              selMetric.interpretation.isWorseThanBaseline
                                ? 'var(--accent-error)'
                                : 'var(--border-secondary)'
                            }`,
                            padding: 12,
                            borderRadius: 6,
                            marginBottom: 16,
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                            {selMetric.interpretation.isWorseThanBaseline ? (
                              <AlertTriangle size={16} color="var(--accent-error)" />
                            ) : (
                              <Info size={16} color="var(--accent-primary)" />
                            )}
                            <strong style={{ fontSize: 13 }}>{selMetric.interpretation.rating}</strong>
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                            {selMetric.interpretation.description}
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                            Baseline Predictor (Mean): R² 0.000
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })()}

                <div className="separator" />

                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  <div style={{ marginBottom: 4 }}><strong>Task Type:</strong> {detectTaskType(selected)}</div>
                  <div style={{ marginBottom: 4 }}><strong>Framework:</strong> {selected.framework} {selected.framework_version}</div>
                  <div style={{ marginBottom: 4 }}><strong>Seed:</strong> {selected.seed}</div>
                  <div style={{ marginBottom: 4 }}><strong>Input Shape:</strong> [{selected.input_shape?.join(', ')}]</div>
                  <div style={{ marginBottom: 4 }}><strong>Output Shape:</strong> [{selected.output_shape?.join(', ')}]</div>
                  <div style={{ marginBottom: 4 }}><strong>Quantization:</strong> {selected.quantization}</div>
                  {selected.config && Object.keys(selected.config).length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <strong>Config:</strong>
                      <pre style={{ background: 'var(--bg-primary)', padding: 8, borderRadius: 4, marginTop: 4, fontSize: 11 }}>
                        {JSON.stringify(selected.config, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>

                <div className="separator" />

                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn--secondary btn--sm" onClick={() => exportOnnx(selected.id)}>
                    <Download size={12} /> Export ONNX
                  </button>
                  <button className="btn btn--secondary btn--sm" onClick={() => exportCArray(selected.id)}>
                    <Download size={12} /> Export C Array
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {experiments.length === 0 && (
        <div className="empty-state" style={{ marginTop: 32 }}>
          <div className="empty-state__icon">🔬</div>
          <div className="empty-state__title">No Experiments</div>
          <div className="empty-state__description">Train a model to see experiments here.</div>
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
