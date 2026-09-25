import { useState, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import api from '../utils/api';
import { Play, Wand2 } from 'lucide-react';

const ALGORITHMS = [
  { value: 'decision_tree', label: 'Decision Tree', tasks: ['classification', 'regression'] },
  { value: 'random_forest', label: 'Random Forest', tasks: ['classification', 'regression'] },
  { value: 'gradient_boosting', label: 'Gradient Boosting', tasks: ['classification', 'regression'] },
  { value: 'svm', label: 'SVM', tasks: ['classification', 'regression'] },
  { value: 'knn', label: 'K-Nearest Neighbors', tasks: ['classification', 'regression'] },
  { value: 'logistic_regression', label: 'Logistic Regression', tasks: ['classification'] },
  { value: 'linear_regression', label: 'Linear Regression', tasks: ['regression'] },
  { value: 'mlp', label: 'MLP Neural Network', tasks: ['classification', 'regression'] },
];

export default function TrainingPage() {
  const { currentProject, datasets, addLog, loadProjectData } = useAppStore();
  const [datasetId, setDatasetId] = useState('');
  const [algorithm, setAlgorithm] = useState('random_forest');
  const [taskType, setTaskType] = useState('classification');
  const [training, setTraining] = useState(false);
  const [autoMLRunning, setAutoMLRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [autoMLResult, setAutoMLResult] = useState<any>(null);

  useEffect(() => {
    if (datasets.length > 0 && !datasetId) setDatasetId(datasets[0].id);
  }, [datasets]);

  const filteredAlgorithms = ALGORITHMS.filter(a => a.tasks.includes(taskType));

  const handleTrain = async () => {
    if (!datasetId || !currentProject?.id) return;
    setTraining(true);
    setResult(null);
    addLog(`Training ${algorithm} on dataset...`);
    try {
      const res = await api.trainModel({
        project_id: currentProject.id,
        dataset_id: datasetId,
        algorithm,
        task_type: taskType,
        seed: 42,
        test_size: 0.2,
      });
      setResult(res);
      addLog(`Training complete: ${algorithm} — accuracy ${(res.metrics.accuracy * 100).toFixed(2)}%`);
      await loadProjectData(currentProject.id);
    } catch (err: any) {
      addLog(`ERROR training: ${err.message}`);
    }
    setTraining(false);
  };

  const handleAutoML = async () => {
    if (!datasetId || !currentProject?.id) return;
    setAutoMLRunning(true);
    setAutoMLResult(null);
    addLog('Starting AutoML...');
    try {
      const res = await api.runAutoML({
        project_id: currentProject.id,
        dataset_id: datasetId,
        task_type: taskType,
        target_column: 'label',
        max_models: 8,
        seed: 42,
      });
      setAutoMLResult(res);
      addLog(`AutoML complete: ${res.summary.completed} models trained`);
      await loadProjectData(currentProject.id);
    } catch (err: any) {
      addLog(`ERROR AutoML: ${err.message}`);
    }
    setAutoMLRunning(false);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Training</h1>
          <p className="page-subtitle">Train ML models on your data</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Manual training */}
        <div className="card">
          <div className="card__header"><span className="card__title">Single Model Training</span></div>
          <div className="card__body">
            <div className="form-group">
              <label className="form-label">Dataset</label>
              <select className="select" value={datasetId} onChange={(e) => setDatasetId(e.target.value)}>
                {datasets.map(d => <option key={d.id} value={d.id}>{d.name} ({d.num_samples} samples)</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Task Type</label>
              <select className="select" value={taskType} onChange={(e) => setTaskType(e.target.value)}>
                <option value="classification">Classification</option>
                <option value="regression">Regression</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Algorithm</label>
              <select className="select" value={algorithm} onChange={(e) => setAlgorithm(e.target.value)}>
                {filteredAlgorithms.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
              </select>
            </div>
            <button className="btn btn--primary" onClick={handleTrain} disabled={training || !datasetId} style={{ width: '100%', justifyContent: 'center' }}>
              <Play size={14} /> {training ? 'Training...' : 'Train Model'}
            </button>
          </div>
        </div>

        {/* AutoML */}
        <div className="card">
          <div className="card__header"><span className="card__title">AutoML</span></div>
          <div className="card__body">
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
              Automatically analyze your dataset and train the best candidate models.
              EdgeForge will select algorithms based on your data characteristics.
            </p>
            <div className="form-group">
              <label className="form-label">Dataset</label>
              <select className="select" value={datasetId} onChange={(e) => setDatasetId(e.target.value)}>
                {datasets.map(d => <option key={d.id} value={d.id}>{d.name} ({d.num_samples} samples)</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Task Type</label>
              <select className="select" value={taskType} onChange={(e) => setTaskType(e.target.value)}>
                <option value="classification">Classification</option>
                <option value="regression">Regression</option>
              </select>
            </div>
            <button className="btn btn--success" onClick={handleAutoML} disabled={autoMLRunning || !datasetId} style={{ width: '100%', justifyContent: 'center' }}>
              <Wand2 size={14} /> {autoMLRunning ? 'Running AutoML...' : 'Train Automatically'}
            </button>
          </div>
        </div>
      </div>

      {/* Training result */}
      {result && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card__header">
            <span className="card__title">Training Result</span>
            <span className="badge badge--success">completed</span>
          </div>
          <div className="card__body">
            <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
              <div className="stat-card">
                <div className="stat-card__label">Algorithm</div>
                <div className="stat-card__value" style={{ fontSize: 14 }}>{result.algorithm}</div>
              </div>
              <div className="stat-card">
                <div className="stat-card__label">Accuracy</div>
                <div className="stat-card__value" style={{ fontSize: 18, color: 'var(--accent-success)' }}>
                  {(result.metrics.accuracy * 100).toFixed(2)}%
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-card__label">F1 Score</div>
                <div className="stat-card__value" style={{ fontSize: 18 }}>
                  {(result.metrics.f1_score * 100).toFixed(2)}%
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-card__label">Model Size</div>
                <div className="stat-card__value" style={{ fontSize: 14 }}>
                  {formatBytes(result.model_size_bytes)}
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-card__label">Duration</div>
                <div className="stat-card__value" style={{ fontSize: 14 }}>
                  {result.duration_seconds.toFixed(2)}s
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AutoML results */}
      {autoMLResult && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card__header">
            <span className="card__title">AutoML Results</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {autoMLResult.summary.completed} / {autoMLResult.summary.total_models} models
            </span>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Algorithm</th>
                  <th>Status</th>
                  <th>Accuracy</th>
                  <th>F1</th>
                  <th>Model Size</th>
                  <th>Duration</th>
                </tr>
              </thead>
              <tbody>
                {autoMLResult.results.map((r: any, i: number) => (
                  <tr key={i}>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{i + 1}</td>
                    <td style={{ fontWeight: 500 }}>{r.algorithm}</td>
                    <td><span className={`badge badge--${r.status === 'completed' ? 'success' : 'error'}`}>{r.status}</span></td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {r.metrics?.accuracy ? `${(r.metrics.accuracy * 100).toFixed(2)}%` : '—'}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {r.metrics?.f1_score ? `${(r.metrics.f1_score * 100).toFixed(2)}%` : '—'}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                      {r.model_size_bytes ? formatBytes(r.model_size_bytes) : '—'}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                      {r.duration_seconds ? `${r.duration_seconds.toFixed(2)}s` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {datasets.length === 0 && (
        <div className="empty-state" style={{ marginTop: 32 }}>
          <div className="empty-state__icon">📊</div>
          <div className="empty-state__title">No Datasets Available</div>
          <div className="empty-state__description">Import a dataset first before training models.</div>
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
