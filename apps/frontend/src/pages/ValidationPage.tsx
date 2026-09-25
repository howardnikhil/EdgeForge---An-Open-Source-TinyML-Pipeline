import { useState, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import api from '../utils/api';
import { CheckCircle2, Scale } from 'lucide-react';

export default function ValidationPage() {
  const { currentProject, experiments, datasets, hardwareProfiles, addLog, loadHardwareProfiles, loadProjectData } = useAppStore();
  const [expId, setExpId] = useState('');
  const [datasetId, setDatasetId] = useState('');
  const [hwId, setHwId] = useState('');
  const [validating, setValidating] = useState(false);
  const [report, setReport] = useState<any>(null);

  useEffect(() => {
    if (currentProject?.id) {
      loadProjectData(currentProject.id);
      loadHardwareProfiles();
    }
  }, [currentProject?.id]);

  const completedExps = experiments.filter(e => e.status === 'completed');

  const handleRunValidation = async () => {
    if (!currentProject?.id || !expId || !datasetId || !hwId) {
      addLog('ERROR: Select project, experiment, dataset, and hardware target.');
      return;
    }
    setValidating(true);
    setReport(null);
    addLog('Executing Desktop vs MCU Comparative Validation...');

    try {
      const res = await api.runValidation({
        project_id: currentProject.id,
        experiment_id: expId,
        dataset_id: datasetId,
        hardware_id: hwId,
        max_samples: 50,
      });

      setReport(res.validation_report);
      addLog(`Validation complete! Agreement Rate: ${res.validation_report.agreement_rate}% (Desktop Acc: ${res.validation_report.desktop_accuracy}%, MCU Acc: ${res.validation_report.mcu_accuracy}%).`);
    } catch (err: any) {
      addLog(`ERROR Validation: ${err.message}`);
    } finally {
      setValidating(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Desktop vs MCU Validation</h1>
          <p className="page-subtitle">Verify inference consistency between Python host runtime and emulated MCU C executable.</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card__header"><span className="card__title">Validation Configuration</span></div>
        <div className="card__body" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, alignItems: 'end' }}>
          <div>
            <label className="form-label">Trained Model</label>
            <select className="form-select" value={expId} onChange={e => setExpId(e.target.value)}>
              <option value="">Select Experiment...</option>
              {completedExps.map(e => <option key={e.id} value={e.id}>{e.name} ({e.algorithm})</option>)}
            </select>
          </div>

          <div>
            <label className="form-label">Evaluation Dataset</label>
            <select className="form-select" value={datasetId} onChange={e => setDatasetId(e.target.value)}>
              <option value="">Select Dataset...</option>
              {datasets.map(d => <option key={d.id} value={d.id}>{d.name} ({d.num_samples} samples)</option>)}
            </select>
          </div>

          <div>
            <label className="form-label">Hardware Target</label>
            <select className="form-select" value={hwId} onChange={e => setHwId(e.target.value)}>
              <option value="">Select Hardware...</option>
              {hardwareProfiles.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}
            </select>
          </div>

          <button className="btn btn--primary" onClick={handleRunValidation} disabled={validating}>
            <Scale size={14} style={{ marginRight: 6 }} />
            {validating ? 'Validating...' : 'Run Validation'}
          </button>
        </div>
      </div>

      {report && (
        <div>
          {/* Top Comparative KPI Metrics */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 16, marginBottom: 24 }}>
            <div className="card" style={{ padding: 16 }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Agreement Rate</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: report.agreement_rate >= 95 ? 'var(--accent-success)' : 'var(--accent-warning)' }}>
                {report.agreement_rate}%
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Prediction Consistency</div>
            </div>

            <div className="card" style={{ padding: 16 }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Desktop Python Accuracy</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--accent-primary)' }}>
                {report.desktop_accuracy}%
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Host Model Benchmark</div>
            </div>

            <div className="card" style={{ padding: 16 }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>MCU C Runtime Accuracy</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#8b5cf6' }}>
                {report.mcu_accuracy}%
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Emulated C Executable</div>
            </div>

            <div className="card" style={{ padding: 16 }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Disagreement Count</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: report.mismatch_count === 0 ? 'var(--accent-success)' : 'var(--accent-error)' }}>
                {report.mismatch_count} / {report.emulated_mcu_samples}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Mismatched Predictions</div>
            </div>
          </div>

          {/* Measured vs Estimated Status Breakdown */}
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card__header"><span className="card__title">Validation Metric Classification</span></div>
            <div className="card__body" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', gap: 12 }}>
              {Object.entries(report.metrics_status || {}).map(([key, val]: any) => (
                <div key={key} style={{ background: 'var(--bg-elevated)', padding: 12, borderRadius: 6, fontSize: 12 }}>
                  <div style={{ color: 'var(--text-muted)', textTransform: 'capitalize', fontSize: 11 }}>{key.replace(/_/g, ' ')}</div>
                  <span className={`badge ${val === 'MEASURED' ? 'badge--success' : val === 'ESTIMATED' ? 'badge--warning' : 'badge--secondary'}`} style={{ marginTop: 6, display: 'inline-block' }}>
                    {val}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Mismatch Inspector Table */}
          <div className="card">
            <div className="card__header">
              <span className="card__title">Prediction Disagreements & Mismatches</span>
            </div>
            {report.mismatches?.length === 0 ? (
              <div className="card__body" style={{ color: 'var(--accent-success)', display: 'flex', alignItems: 'center', gap: 8, padding: 24 }}>
                <CheckCircle2 size={18} /> 100% Prediction Agreement! MCU C runtime matches Desktop model predictions exactly across all evaluation samples.
              </div>
            ) : (
              <div className="table-container" style={{ maxHeight: 350, overflow: 'auto' }}>
                <table>
                  <thead>
                    <tr>
                      <th>Sample Index</th>
                      <th>Ground Truth</th>
                      <th>Desktop Prediction</th>
                      <th>MCU C Prediction</th>
                      <th>MCU Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.mismatches?.map((m: any) => (
                      <tr key={m.sample_index}>
                        <td>#{m.sample_index}</td>
                        <td>Class {m.ground_truth}</td>
                        <td>Class {m.desktop_prediction}</td>
                        <td style={{ color: 'var(--accent-error)', fontWeight: 600 }}>Class {m.mcu_prediction}</td>
                        <td>{(m.mcu_confidence * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
