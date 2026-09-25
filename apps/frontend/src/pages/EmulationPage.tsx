import { useState, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import api from '../utils/api';
import { Play, CheckCircle2, AlertTriangle, Terminal } from 'lucide-react';

export default function EmulationPage() {
  const { currentProject, experiments, datasets, hardwareProfiles, addLog, loadHardwareProfiles, loadProjectData } = useAppStore();
  const [expId, setExpId] = useState('');
  const [datasetId, setDatasetId] = useState('');
  const [hwId, setHwId] = useState('');
  const [emulatorType, setEmulatorType] = useState('native');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    if (currentProject?.id) {
      loadProjectData(currentProject.id);
      loadHardwareProfiles();
    }
  }, [currentProject?.id]);

  const completedExps = experiments.filter(e => e.status === 'completed');

  const handleRunEmulation = async () => {
    if (!currentProject?.id || !expId || !datasetId || !hwId) {
      addLog('ERROR: Select project, experiment, dataset, and hardware target.');
      return;
    }
    setRunning(true);
    setResult(null);
    addLog(`Starting MCU Firmware Emulation (${emulatorType})...`);

    try {
      const res = await api.runEmulation({
        project_id: currentProject.id,
        experiment_id: expId,
        dataset_id: datasetId,
        hardware_id: hwId,
        emulator_type: emulatorType,
        max_samples: 50,
      });

      setResult(res.emulation_result);
      if (res.emulation_result?.success) {
        addLog(`MCU Emulation completed! Avg Latency: ${res.emulation_result.avg_latency_us} μs across ${res.emulation_result.samples_processed} samples.`);
      } else {
        addLog(`MCU Emulation error: ${res.emulation_result?.error || 'Execution failed'}`);
      }
    } catch (err: any) {
      addLog(`ERROR Emulation: ${err.message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">MCU Firmware Emulation</h1>
          <p className="page-subtitle">Execute MCU firmware binaries and replay sensor datasets deterministically over UART.</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card__header"><span className="card__title">Emulation & Sensor Replay Configuration</span></div>
        <div className="card__body" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, alignItems: 'end' }}>
          <div>
            <label className="form-label">Trained Experiment</label>
            <select className="form-select" value={expId} onChange={e => setExpId(e.target.value)}>
              <option value="">Select Experiment...</option>
              {completedExps.map(e => <option key={e.id} value={e.id}>{e.name} ({e.algorithm})</option>)}
            </select>
          </div>

          <div>
            <label className="form-label">Replay Dataset</label>
            <select className="form-select" value={datasetId} onChange={e => setDatasetId(e.target.value)}>
              <option value="">Select Dataset...</option>
              {datasets.map(d => <option key={d.id} value={d.id}>{d.name} ({d.num_samples} samples)</option>)}
            </select>
          </div>

          <div>
            <label className="form-label">Target MCU</label>
            <select className="form-select" value={hwId} onChange={e => setHwId(e.target.value)}>
              <option value="">Select Hardware...</option>
              {hardwareProfiles.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}
            </select>
          </div>

          <div>
            <label className="form-label">Emulator Core</label>
            <select className="form-select" value={emulatorType} onChange={e => setEmulatorType(e.target.value)}>
              <option value="native">Native Host MCU Target</option>
              <option value="renode">Renode Emulator</option>
              <option value="qemu">QEMU Target</option>
            </select>
          </div>

          <button className="btn btn--primary" onClick={handleRunEmulation} disabled={running}>
            <Play size={14} style={{ marginRight: 6 }} />
            {running ? 'Emulating...' : 'Run Emulation'}
          </button>
        </div>
      </div>

      {result && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
          {/* Summary Metrics */}
          <div className="card">
            <div className="card__header"><span className="card__title">Execution Performance</span></div>
            <div className="card__body" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div style={{ background: 'var(--bg-elevated)', padding: 16, borderRadius: 6 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Status</div>
                <div style={{ fontSize: 18, fontWeight: 600, color: result.success ? 'var(--accent-success)' : 'var(--accent-error)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  {result.success ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
                  {result.success ? 'SUCCESS' : 'FAILED'}
                </div>
              </div>

              <div style={{ background: 'var(--bg-elevated)', padding: 16, borderRadius: 6 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Avg Inference Latency</div>
                <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--accent-primary)' }}>
                  {result.avg_latency_us} μs
                </div>
              </div>

              <div style={{ background: 'var(--bg-elevated)', padding: 16, borderRadius: 6 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Replayed Samples</div>
                <div style={{ fontSize: 18, fontWeight: 600 }}>
                  {result.samples_processed} / {result.samples_total}
                </div>
              </div>

              <div style={{ background: 'var(--bg-elevated)', padding: 16, borderRadius: 6 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Emulator Engine</div>
                <div style={{ fontSize: 18, fontWeight: 600, textTransform: 'capitalize' }}>
                  {result.emulator_used}
                </div>
              </div>
            </div>

            {/* Raw Logs */}
            <div style={{ padding: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Terminal size={14} /> UART Console Telemetry
              </div>
              <pre style={{ background: '#090d16', padding: 12, borderRadius: 6, fontSize: 11, fontFamily: 'var(--font-mono)', maxHeight: 250, overflow: 'auto', color: '#a0aec0' }}>
                {result.raw_logs || 'No output stream captured.'}
              </pre>
            </div>
          </div>

          {/* Parsed Telemetry Table */}
          <div className="card">
            <div className="card__header"><span className="card__title">Parsed Embedded Telemetry</span></div>
            <div className="table-container" style={{ maxHeight: 420, overflow: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th># Index</th>
                    <th>Prediction</th>
                    <th>Confidence</th>
                    <th>Latency (μs)</th>
                    <th>Free Heap</th>
                  </tr>
                </thead>
                <tbody>
                  {result.telemetry?.map((t: any) => (
                    <tr key={t.sample_index}>
                      <td>#{t.sample_index}</td>
                      <td><span className="badge badge--success">Class {t.prediction}</span></td>
                      <td>{(t.confidence * 100).toFixed(1)}%</td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>{t.time_us} μs</td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>{(t.heap_free_bytes / 1024).toFixed(1)} KB</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
