import { useState, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import api from '../utils/api';
import { formatExperimentMetric } from '../utils/metrics';
import { Code } from 'lucide-react';

export default function FirmwarePage() {
  const { currentProject, experiments, hardwareProfiles, addLog, loadHardwareProfiles } = useAppStore();
  const [expId, setExpId] = useState('');
  const [hwId, setHwId] = useState('');
  const [format, setFormat] = useState('platformio');
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<any>(null);

  const completedExps = experiments.filter(e => e.status === 'completed');

  useEffect(() => { loadHardwareProfiles(); }, []);
  useEffect(() => { if (completedExps.length && !expId) setExpId(completedExps[0].id); }, [completedExps]);
  useEffect(() => { if (hardwareProfiles.length && !hwId) setHwId(hardwareProfiles[0]?.id || ''); }, [hardwareProfiles]);

  const generate = async () => {
    if (!currentProject?.id || !expId || !hwId) return;
    setGenerating(true);
    setResult(null);
    try {
      const res = await api.generateFirmware({ project_id: currentProject.id, experiment_id: expId, hardware_id: hwId, deployment_format: format });
      setResult(res);
      addLog(`Firmware generated: ${res.files.length} files`);
    } catch (err: any) {
      addLog(`ERROR: ${err.message}`);
    }
    setGenerating(false);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Firmware Generation</h1>
          <p className="page-subtitle">Generate deployable firmware for your trained model</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card__body">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <div className="form-group">
              <label className="form-label">Model / Experiment</label>
              <select className="select" value={expId} onChange={(e) => setExpId(e.target.value)}>
                {completedExps.map(e => (
                  <option key={e.id} value={e.id}>
                    {e.algorithm} — {formatExperimentMetric(e).value} — {formatBytes(e.model_size_bytes||0)}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Target Hardware</label>
              <select className="select" value={hwId} onChange={(e) => setHwId(e.target.value)}>
                {hardwareProfiles.map((h: any) => <option key={h.id} value={h.id}>{h.name}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Format</label>
              <select className="select" value={format} onChange={(e) => setFormat(e.target.value)}>
                <option value="platformio">PlatformIO</option>
                <option value="arduino">Arduino</option>
              </select>
            </div>
          </div>
          <button className="btn btn--primary" onClick={generate} disabled={generating || !expId || !hwId} style={{ width: '100%', justifyContent: 'center' }}>
            <Code size={14} /> {generating ? 'Generating...' : 'Generate Firmware'}
          </button>
        </div>
      </div>

      {result && (
        <div className="card">
          <div className="card__header">
            <span className="card__title">Generated Firmware</span>
            <span className="badge badge--success">✓ Generated</span>
          </div>
          <div className="card__body">
            <div style={{ marginBottom: 16, fontSize: 13 }}>
              <div><strong>Hardware:</strong> {result.hardware}</div>
              <div><strong>Format:</strong> {result.deployment_format}</div>
              <div><strong>Path:</strong> <code style={{ fontSize: 11 }}>{result.firmware_path}</code></div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8 }}>Build Command</div>
              <div style={{ background: 'var(--bg-primary)', padding: '8px 12px', borderRadius: 6, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                {result.build_command}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8 }}>Generated Files</div>
              {result.files.map((f: string, i: number) => (
                <div key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)', padding: '2px 0' }}>
                  📄 {f}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {completedExps.length === 0 && (
        <div className="empty-state" style={{ marginTop: 32 }}>
          <div className="empty-state__icon">🔧</div>
          <div className="empty-state__title">No Trained Models</div>
          <div className="empty-state__description">Train a model first, then generate firmware.</div>
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
