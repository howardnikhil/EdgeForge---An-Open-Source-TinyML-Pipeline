import { useState, useRef } from 'react';
import { useAppStore } from '../stores/appStore';
import api from '../utils/api';
import { Upload, BarChart3, Split, Trash2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#f97316'];

export default function DatasetPage() {
  const { currentProject, datasets, addLog, loadProjectData } = useAppStore();
  const [importing, setImporting] = useState(false);
  const [datasetName, setDatasetName] = useState('');
  const [selectedDataset, setSelectedDataset] = useState<any>(null);
  const [datasetDetail, setDatasetDetail] = useState<any>(null);
  const [splitting, setSplitting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !currentProject?.id) return;
    const name = datasetName.trim() || file.name.replace('.csv', '');
    setImporting(true);
    try {
      const result = await api.importCsv(currentProject.id, name, file);
      addLog(`Dataset imported: ${result.name} (${result.num_samples} samples)`);
      await loadProjectData(currentProject.id);
      setDatasetName('');
    } catch (err: any) {
      addLog(`ERROR importing dataset: ${err.message}`);
    }
    setImporting(false);
    if (fileRef.current) fileRef.current.value = '';
  };

  const viewDataset = async (ds: any) => {
    setSelectedDataset(ds);
    try {
      const detail = await api.getDataset(ds.id);
      setDatasetDetail(detail);
    } catch (err: any) {
      addLog(`ERROR: ${err.message}`);
    }
  };

  const splitDataset = async () => {
    if (!selectedDataset) return;
    setSplitting(true);
    try {
      const result = await api.splitDataset(selectedDataset.id, { train_ratio: 0.7, val_ratio: 0.15, test_ratio: 0.15 });
      addLog(`Dataset split: train=${result.train.count}, val=${result.validation.count}, test=${result.test.count}`);
    } catch (err: any) {
      addLog(`ERROR: ${err.message}`);
    }
    setSplitting(false);
  };

  const deleteDataset = async (id: string) => {
    if (!confirm('Delete this dataset?')) return;
    try {
      await api.deleteDataset(id);
      await loadProjectData(currentProject.id);
      if (selectedDataset?.id === id) { setSelectedDataset(null); setDatasetDetail(null); }
      addLog('Dataset deleted');
    } catch (err: any) {
      addLog(`ERROR: ${err.message}`);
    }
  };

  const classData = datasetDetail?.class_labels
    ? Object.entries(datasetDetail.class_labels).map(([name, count]) => ({ name, count: count as number }))
    : [];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Datasets</h1>
          <p className="page-subtitle">Import, manage, and explore your data</p>
        </div>
      </div>

      {/* Import */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card__body" style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label className="form-label">Dataset Name</label>
            <input className="input" value={datasetName} onChange={(e) => setDatasetName(e.target.value)} placeholder="My Dataset" />
          </div>
          <div>
            <input type="file" ref={fileRef} accept=".csv" style={{ display: 'none' }} onChange={handleImport} />
            <button className="btn btn--primary" onClick={() => fileRef.current?.click()} disabled={importing}>
              <Upload size={14} /> {importing ? 'Importing...' : 'Import CSV'}
            </button>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selectedDataset ? '1fr 1.5fr' : '1fr', gap: 24 }}>
        {/* Dataset list */}
        <div>
          {datasets.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state__icon">📁</div>
              <div className="empty-state__title">No Datasets</div>
              <div className="empty-state__description">Import a CSV file to get started.</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {datasets.map((ds) => (
                <div
                  key={ds.id}
                  className="card"
                  style={{ cursor: 'pointer', borderColor: selectedDataset?.id === ds.id ? 'var(--accent-primary)' : undefined }}
                  onClick={() => viewDataset(ds)}
                >
                  <div className="card__body" style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 12 }}>
                    <BarChart3 size={16} style={{ color: 'var(--accent-info)' }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 500, fontSize: 13 }}>{ds.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {ds.num_samples.toLocaleString()} samples · {ds.num_classes} classes · v{ds.version}
                      </div>
                    </div>
                    <button className="btn btn--ghost btn--sm" onClick={(e) => { e.stopPropagation(); deleteDataset(ds.id); }}>
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Dataset detail */}
        {datasetDetail && (
          <div>
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card__header">
                <span className="card__title">{datasetDetail.name}</span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn--secondary btn--sm" onClick={splitDataset} disabled={splitting}>
                    <Split size={12} /> Split
                  </button>
                </div>
              </div>
              <div className="card__body">
                <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
                  <div className="stat-card">
                    <div className="stat-card__label">Samples</div>
                    <div className="stat-card__value" style={{ fontSize: 18 }}>{datasetDetail.num_samples.toLocaleString()}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-card__label">Columns</div>
                    <div className="stat-card__value" style={{ fontSize: 18 }}>{datasetDetail.columns?.length || 0}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-card__label">Classes</div>
                    <div className="stat-card__value" style={{ fontSize: 18 }}>{datasetDetail.num_classes}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-card__label">Version</div>
                    <div className="stat-card__value" style={{ fontSize: 18 }}>v{datasetDetail.version}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Class distribution */}
            {classData.length > 0 && (
              <div className="card" style={{ marginBottom: 16 }}>
                <div className="card__header"><span className="card__title">Class Distribution</span></div>
                <div className="card__body" style={{ height: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={classData}>
                      <XAxis dataKey="name" fontSize={11} stroke="var(--text-muted)" />
                      <YAxis fontSize={11} stroke="var(--text-muted)" />
                      <Tooltip
                        contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-secondary)', borderRadius: 6, fontSize: 12 }}
                      />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {classData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Column statistics */}
            {datasetDetail.statistics?.columns && (
              <div className="card" style={{ marginBottom: 16 }}>
                <div className="card__header"><span className="card__title">Column Statistics</span></div>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr><th>Column</th><th>Type</th><th>Min</th><th>Max</th><th>Mean</th><th>Std</th><th>Missing</th></tr>
                    </thead>
                    <tbody>
                      {Object.entries(datasetDetail.statistics.columns).map(([col, stats]: [string, any]) => (
                        <tr key={col}>
                          <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 500 }}>{col}</td>
                          <td><span className="chip">{stats.dtype}</span></td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{stats.min?.toFixed(3) ?? '—'}</td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{stats.max?.toFixed(3) ?? '—'}</td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{stats.mean?.toFixed(3) ?? '—'}</td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{stats.std?.toFixed(3) ?? '—'}</td>
                          <td>{datasetDetail.statistics.missing_values?.[col] ?? 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Data preview */}
            {datasetDetail.preview && datasetDetail.preview.length > 0 && (
              <div className="card">
                <div className="card__header">
                  <span className="card__title">Data Preview</span>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>First {datasetDetail.preview.length} rows</span>
                </div>
                <div className="table-container" style={{ maxHeight: 300, overflow: 'auto' }}>
                  <table>
                    <thead>
                      <tr>{datasetDetail.columns.map((c: string) => <th key={c}>{c}</th>)}</tr>
                    </thead>
                    <tbody>
                      {datasetDetail.preview.slice(0, 30).map((row: any, i: number) => (
                        <tr key={i}>
                          {datasetDetail.columns.map((c: string) => (
                            <td key={c} style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                              {typeof row[c] === 'number' ? row[c].toFixed(4) : String(row[c] ?? '')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
