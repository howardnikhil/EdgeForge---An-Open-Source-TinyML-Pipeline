import { useState, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import api from '../utils/api';
import { Radio, RefreshCw, Plug, Unplug } from 'lucide-react';

export default function SerialPage() {
  const { addLog } = useAppStore();
  const [ports, setPorts] = useState<any[]>([]);
  const [selectedPort, setSelectedPort] = useState('');
  const [baudRate, setBaudRate] = useState(115200);
  const [connected, setConnected] = useState(false);
  const [connectedPort, setConnectedPort] = useState('');
  const [scanning, setScanning] = useState(false);
  const [status, setStatus] = useState<any>(null);

  const scanPorts = async () => {
    setScanning(true);
    try {
      const result = await api.listPorts();
      setPorts(result.ports || []);
      addLog(`Found ${result.ports?.length || 0} serial ports`);
      if (result.ports?.length > 0 && !selectedPort) {
        setSelectedPort(result.ports[0].device);
      }
    } catch (err: any) {
      addLog(`ERROR scanning ports: ${err.message}`);
    }
    setScanning(false);
  };

  const connect = async () => {
    if (!selectedPort) return;
    try {
      await api.connectPort(selectedPort, baudRate);
      setConnected(true);
      setConnectedPort(selectedPort);
      addLog(`Connected to ${selectedPort} at ${baudRate} baud`);
    } catch (err: any) {
      addLog(`ERROR connecting: ${err.message}`);
    }
  };

  const disconnect = async () => {
    try {
      await api.disconnectPort(connectedPort);
      setConnected(false);
      setConnectedPort('');
      addLog('Disconnected from serial port');
    } catch (err: any) {
      addLog(`ERROR disconnecting: ${err.message}`);
    }
  };

  const refreshStatus = async () => {
    try {
      const s = await api.serialStatus();
      setStatus(s);
    } catch (err: any) {
      // silent
    }
  };

  useEffect(() => {
    scanPorts();
    const interval = setInterval(refreshStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Serial / Data Collection</h1>
          <p className="page-subtitle">Connect to sensors and collect data via USB serial</p>
        </div>
        <button className="btn btn--secondary" onClick={scanPorts} disabled={scanning}>
          <RefreshCw size={14} className={scanning ? 'loading-pulse' : ''} /> Scan Ports
        </button>
      </div>

      <div className="grid-2">
        {/* Connection */}
        <div className="card">
          <div className="card__header"><span className="card__title">Device Connection</span></div>
          <div className="card__body">
            <div className="form-group">
              <label className="form-label">Port</label>
              <select className="select" value={selectedPort} onChange={(e) => setSelectedPort(e.target.value)} disabled={connected}>
                {ports.length === 0 && <option value="">No ports found</option>}
                {ports.map((p) => (
                  <option key={p.device} value={p.device}>
                    {p.device} — {p.description || p.product || 'Unknown'}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Baud Rate</label>
              <select className="select" value={baudRate} onChange={(e) => setBaudRate(Number(e.target.value))} disabled={connected}>
                {[9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600].map(b => (
                  <option key={b} value={b}>{b.toLocaleString()}</option>
                ))}
              </select>
            </div>
            {!connected ? (
              <button className="btn btn--primary" onClick={connect} disabled={!selectedPort} style={{ width: '100%', justifyContent: 'center' }}>
                <Plug size={14} /> Connect
              </button>
            ) : (
              <button className="btn btn--danger" onClick={disconnect} style={{ width: '100%', justifyContent: 'center' }}>
                <Unplug size={14} /> Disconnect
              </button>
            )}
          </div>
        </div>

        {/* Status */}
        <div className="card">
          <div className="card__header"><span className="card__title">Connection Status</span></div>
          <div className="card__body">
            {connected ? (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--accent-success)', boxShadow: '0 0 8px var(--accent-success)' }} />
                  <span style={{ fontWeight: 600, color: 'var(--accent-success)' }}>Connected</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div className="stat-card">
                    <div className="stat-card__label">Port</div>
                    <div className="stat-card__value" style={{ fontSize: 12 }}>{connectedPort}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-card__label">Baud</div>
                    <div className="stat-card__value" style={{ fontSize: 14 }}>{baudRate.toLocaleString()}</div>
                  </div>
                  {status && Object.values(status).map((s: any, i: number) => (
                    <div key={i}>
                      <div className="stat-card">
                        <div className="stat-card__label">RX Bytes</div>
                        <div className="stat-card__value" style={{ fontSize: 14 }}>{formatBytes(s.rx_bytes || 0)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="empty-state" style={{ padding: 24 }}>
                <Radio size={32} style={{ color: 'var(--text-muted)', marginBottom: 12 }} />
                <div className="empty-state__title" style={{ fontSize: 14 }}>Not Connected</div>
                <div className="empty-state__description">Select a port and click Connect.</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Available ports */}
      {ports.length > 0 && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card__header">
            <span className="card__title">Available Ports</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{ports.length} found</span>
          </div>
          <div className="table-container">
            <table>
              <thead><tr><th>Device</th><th>Description</th><th>Manufacturer</th><th>VID:PID</th></tr></thead>
              <tbody>
                {ports.map((p) => (
                  <tr key={p.device}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 500 }}>{p.device}</td>
                    <td>{p.description || '—'}</td>
                    <td>{p.manufacturer || '—'}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{p.vid && p.pid ? `${p.vid}:${p.pid}` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
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
