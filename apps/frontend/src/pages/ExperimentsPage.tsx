import { useEffect, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import api from '../utils/api';
import { Download, Trash2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4'];

export default function ExperimentsPage() {
  const { currentProject, experiments, addLog, loadProjectData, setInspectorData } = useAppStore();
  const [selected, setSelected] = useState<any>(null);

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

  const getMetricValue = (exp: any): number => {
    const m = exp.metrics;
    if (!m) return 0;
    if (m.accuracy !== undefined) return m.accuracy * 100;
    if (m.r2_score !== undefined) return m.r2_score * 100;
    if (m.r2 !== undefined) return m.r2 * 100;
    return 0;
  };

  const getMetricLabel = (exp: any): string => {
    const m = exp.metrics;
    if (!m) return '—';
    if (m.accuracy !== undefined) return `${(m.accuracy * 100).toFixed(2)}%`;
    if (m.r2_score !== undefined) return `R² ${(m.r2_score * 100).toFixed(2)}%`;
    if (m.r2 !== undefined) return `R² ${(m.r2 * 100).toFixed(2)}%`;
    return '—';
  };

  const isAnyRegression = completed.some(e => e.task_type === 'regression' || e.metrics?.r2_score !== undefined || e.metrics?.r2 !== undefined);
  const chartMetricLabel = isAnyRegression ? 'Score' : 'Accuracy';

  const comparisonData = completed.map(e => ({
    name: e.algorithm,
    score: getMetricValue(e),
    size: e.model_size_bytes ?? 0,
  }));

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Experiments</h1>
          <p className="page-subtitle">{experiments.length} experiments · {completed.length} completed</p>
        </div>
      </div>

      {/* Accuracy comparison chart */}
      {comparisonData.length > 1 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card__header"><span className="card__title">Model Comparison — {chartMetricLabel}</span></div>
          <div className="card__body" style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonData}>
                <XAxis dataKey="name" fontSize={11} stroke="var(--text-muted)" />
                <YAxis fontSize={11} stroke="var(--text-muted)" domain={[0, 100]} />
                <Tooltip
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-secondary)', borderRadius: 6, fontSize: 12 }}
                  formatter={(v: any) => `${typeof v === 'number' ? v.toFixed(2) : v}%`}
                />
                <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                  {comparisonData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 1fr' : '1fr', gap: 24 }}>
        {/* Experiment list */}
        <div className="card">
          <div className="card__header"><span className="card__title">All Experiments</span></div>
          <div className="table-container" style={{ maxHeight: 500, overflow: 'auto' }}>
            <table>
              <thead>
                <tr><th>Algorithm</th><th>Status</th><th>{isAnyRegression ? 'Score' : 'Accuracy'}</th><th>Size</th><th></th></tr>
              </thead>
              <tbody>
                {experiments.map((exp) => (
                  <tr key={exp.id} onClick={() => selectExperiment(exp)} style={{ cursor: 'pointer' }}>
                    <td style={{ fontWeight: 500 }}>{exp.algorithm}</td>
                    <td><span className={`badge badge--${exp.status === 'completed' ? 'success' : exp.status === 'failed' ? 'error' : 'warning'}`}>{exp.status}</span></td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {getMetricLabel(exp)}
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
                ))}
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
                <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 16 }}>
                  {selected.metrics?.accuracy !== undefined && (
                    <div className="stat-card">
                      <div className="stat-card__label">Accuracy</div>
                      <div className="stat-card__value" style={{ fontSize: 20, color: 'var(--accent-success)' }}>
                        {(selected.metrics.accuracy * 100).toFixed(2)}%
                      </div>
                    </div>
                  )}
                  {selected.metrics?.f1_score !== undefined && (
                    <div className="stat-card">
                      <div className="stat-card__label">F1 Score</div>
                      <div className="stat-card__value" style={{ fontSize: 20 }}>
                        {(selected.metrics.f1_score * 100).toFixed(2)}%
                      </div>
                    </div>
                  )}
                  <div className="stat-card">
                    <div className="stat-card__label">Duration</div>
                    <div className="stat-card__value" style={{ fontSize: 16 }}>
                      {selected.duration_seconds?.toFixed(2)}s
                    </div>
                  </div>
                </div>

                <div className="separator" />

                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
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
