import { useEffect, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import api from '../utils/api';
import { formatExperimentMetric } from '../utils/metrics';
import { Cpu, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

export default function HardwarePage() {
  const { hardwareProfiles, experiments, addLog, loadHardwareProfiles } = useAppStore();
  const [selectedProfile, setSelectedProfile] = useState<any>(null);
  const [compatibility, setCompatibility] = useState<any>(null);
  const [selectedExpId, setSelectedExpId] = useState('');

  useEffect(() => { loadHardwareProfiles(); }, []);

  const completedExps = experiments.filter(e => e.status === 'completed');

  useEffect(() => {
    if (completedExps.length > 0 && !selectedExpId) setSelectedExpId(completedExps[0].id);
  }, [completedExps]);

  const checkCompatibility = async (hwId: string) => {
    if (!selectedExpId) { addLog('Select an experiment first'); return; }
    try {
      const result = await api.checkCompatibility(selectedExpId, hwId);
      setCompatibility(result);
      addLog(`Compatibility: ${result.compatible ? 'COMPATIBLE' : 'NOT COMPATIBLE'}`);
    } catch (err: any) {
      addLog(`ERROR: ${err.message}`);
    }
  };

  const viewProfile = async (id: string) => {
    try {
      const profile = await api.getHardwareProfile(id);
      setSelectedProfile(profile);
    } catch (err: any) {
      addLog(`ERROR: ${err.message}`);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Hardware Targets</h1>
          <p className="page-subtitle">Select and analyze MCU compatibility</p>
        </div>
      </div>

      {completedExps.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card__body" style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <label className="form-label" style={{ marginBottom: 0, whiteSpace: 'nowrap' }}>Check model:</label>
            <select className="select" style={{ maxWidth: 400 }} value={selectedExpId} onChange={(e) => { setSelectedExpId(e.target.value); setCompatibility(null); }}>
              {completedExps.map(e => (
                <option key={e.id} value={e.id}>
                  {e.algorithm} — {formatExperimentMetric(e).value} — {formatBytes(e.model_size_bytes || 0)}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Hardware profiles grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16, marginBottom: 24 }}>
        {hardwareProfiles.map((hw: any) => (
          <div key={hw.id} className="card" style={{ cursor: 'pointer' }} onClick={() => { viewProfile(hw.id); if (selectedExpId) checkCompatibility(hw.id); }}>
            <div className="card__body">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                <Cpu size={20} style={{ color: 'var(--accent-primary)' }} />
                <span style={{ fontWeight: 700, fontSize: 16 }}>{hw.name}</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 12px' }}>
                <div>Architecture</div><div style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{hw.architecture}</div>
                <div>Flash</div><div style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{hw.flash_display}</div>
                <div>RAM</div><div style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{hw.ram_display}</div>
                <div>CPU</div><div style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{hw.cpu_freq_mhz} MHz</div>
              </div>
              <div style={{ marginTop: 10, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {hw.deployment_formats?.map((f: string) => <span key={f} className="chip">{f}</span>)}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Compatibility result */}
      {compatibility && (
        <div className="card" style={{ borderColor: compatibility.compatible ? 'var(--accent-success)' : 'var(--accent-error)' }}>
          <div className="card__header">
            <span className="card__title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {compatibility.compatible
                ? <><CheckCircle size={18} style={{ color: 'var(--accent-success)' }} /> Compatible</>
                : <><XCircle size={18} style={{ color: 'var(--accent-error)' }} /> Not Compatible</>
              }
            </span>
            <span style={{ fontSize: 13 }}>{compatibility.hardware.name}</span>
          </div>
          <div className="card__body">
            <div className="grid-2">
              {/* Flash */}
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Flash Memory</div>
                <div className="metric-bar">
                  <span className="metric-bar__label">Usage</span>
                  <div className="metric-bar__track">
                    <div
                      className={`metric-bar__fill ${compatibility.flash.ok ? 'metric-bar__fill--good' : 'metric-bar__fill--danger'}`}
                      style={{ width: `${Math.min(100, compatibility.flash.usage_percent)}%` }}
                    />
                  </div>
                  <span className="metric-bar__value">{compatibility.flash.usage_percent}%</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  Model: {formatBytes(compatibility.flash.model_bytes)} / {formatBytes(compatibility.flash.total_bytes)}
                </div>
              </div>

              {/* RAM */}
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>RAM</div>
                <div className="metric-bar">
                  <span className="metric-bar__label">Estimated</span>
                  <div className="metric-bar__track">
                    <div
                      className={`metric-bar__fill ${compatibility.ram.ok ? 'metric-bar__fill--good' : 'metric-bar__fill--danger'}`}
                      style={{ width: `${Math.min(100, (compatibility.ram.estimated_bytes / compatibility.ram.total_bytes * 100))}%` }}
                    />
                  </div>
                  <span className="metric-bar__value">
                    {formatBytes(compatibility.ram.estimated_bytes)}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  Available: {formatBytes(compatibility.ram.available_bytes)} / {formatBytes(compatibility.ram.total_bytes)}
                </div>
                {compatibility.ram.note && (
                  <div style={{ fontSize: 10, color: 'var(--accent-warning)', marginTop: 4 }}>
                    ⚠ {compatibility.ram.note}
                  </div>
                )}
              </div>
            </div>

            {/* Issues */}
            {compatibility.issues.length > 0 && (
              <div style={{ marginTop: 16 }}>
                {compatibility.issues.map((issue: any, i: number) => (
                  <div key={i} style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: 8, padding: 12, marginBottom: 8 }}>
                    <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--accent-error)', marginBottom: 6 }}>
                      <AlertTriangle size={14} style={{ marginRight: 4, verticalAlign: -2 }} />
                      {issue.type}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>{issue.message}</div>
                    {issue.remedies && (
                      <div style={{ fontSize: 12 }}>
                        <div style={{ fontWeight: 500, color: 'var(--text-muted)', marginBottom: 4 }}>Possible remedies:</div>
                        <ul style={{ margin: 0, paddingLeft: 16, color: 'var(--text-secondary)' }}>
                          {issue.remedies.map((r: string, j: number) => <li key={j}>{r}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Profile detail */}
      {selectedProfile && !compatibility && (
        <div className="card">
          <div className="card__header"><span className="card__title">{selectedProfile.name} — Details</span></div>
          <div className="card__body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, fontSize: 13 }}>
              <div><span style={{ color: 'var(--text-muted)' }}>Architecture:</span> {selectedProfile.architecture}</div>
              <div><span style={{ color: 'var(--text-muted)' }}>Toolchain:</span> {selectedProfile.toolchain}</div>
              <div><span style={{ color: 'var(--text-muted)' }}>Runtime:</span> {selectedProfile.runtime}</div>
              <div><span style={{ color: 'var(--text-muted)' }}>Emulator:</span> {selectedProfile.emulator || 'none'}</div>
            </div>
            {selectedProfile.supported_operators && (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Supported Operators:</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {selectedProfile.supported_operators.map((op: string) => <span key={op} className="chip">{op}</span>)}
                </div>
              </div>
            )}
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
