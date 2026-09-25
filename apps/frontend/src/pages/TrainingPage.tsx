import { useState, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import api from '../utils/api';
import { Play, Wand2, AlertTriangle, CheckCircle2 } from 'lucide-react';

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
  const [userCustomTask, setUserCustomTask] = useState(false);
  const [training, setTraining] = useState(false);
  const [autoMLRunning, setAutoMLRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [autoMLResult, setAutoMLResult] = useState<any>(null);
  const [errorState, setErrorState] = useState<any>(null);

  const selectedDs = datasets.find(d => d.id === datasetId);
  const targetInfo = selectedDs?.target_info || null;

  useEffect(() => {
    if (datasets.length > 0 && !datasetId) {
      setDatasetId(datasets[0].id);
    }
  }, [datasets]);

  // Auto-suggest task when dataset changes
  useEffect(() => {
    if (targetInfo?.task_suggestion && !userCustomTask) {
      setTaskType(targetInfo.task_suggestion);
    }
  }, [datasetId, targetInfo]);

  // Check compatibility
  const isCategorical = targetInfo?.target_type === 'categorical' || targetInfo?.target_type === 'boolean';
  const isContinuous = targetInfo?.target_type === 'numeric continuous';
  const isMismatch = (isCategorical && taskType === 'regression') || (isContinuous && taskType === 'classification');

  const filteredAlgorithms = ALGORITHMS.filter(a => a.tasks.includes(taskType));

  // Keep selected algorithm valid
  useEffect(() => {
    if (filteredAlgorithms.length > 0 && !filteredAlgorithms.some(a => a.value === algorithm)) {
      setAlgorithm(filteredAlgorithms[0].value);
    }
  }, [taskType]);

  const handleTaskTypeChange = (newType: string) => {
    setTaskType(newType);
    setUserCustomTask(true);
    setErrorState(null);
  };

  const handleTrain = async () => {
    if (!datasetId || !currentProject?.id || isMismatch) return;
    setTraining(true);
    setResult(null);
    setErrorState(null);
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
      const metricVal = res.metrics.accuracy !== undefined ? `${(res.metrics.accuracy * 100).toFixed(2)}% acc` : `R² ${res.metrics.r2?.toFixed(3)}`;
      addLog(`Training complete: ${algorithm} — ${metricVal}`);
      await loadProjectData(currentProject.id);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const errMsg = typeof detail === 'object' ? detail.message : (err.message || 'Training failed');
      setErrorState(typeof detail === 'object' ? detail : { message: errMsg });
      addLog(`ERROR training: ${errMsg}`);
    }
    setTraining(false);
  };

  const handleAutoML = async () => {
    if (!datasetId || !currentProject?.id) return;
    setAutoMLRunning(true);
    setAutoMLResult(null);
    setErrorState(null);
    addLog('Starting AutoML...');
    try {
      const res = await api.runAutoML({
        project_id: currentProject.id,
        dataset_id: datasetId,
        task_type: taskType,
        target_column: targetInfo?.target_column || 'label',
        max_models: 8,
        seed: 42,
      });
      setAutoMLResult(res);
      addLog(`AutoML complete: ${res.summary.completed} models trained`);
      await loadProjectData(currentProject.id);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const errMsg = typeof detail === 'object' ? detail.message : (err.message || 'AutoML failed');
      setErrorState(typeof detail === 'object' ? detail : { message: errMsg });
      addLog(`ERROR AutoML: ${errMsg}`);
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

      {/* Target compatibility warning banner */}
      {isMismatch && targetInfo && (
        <div style={{
          marginBottom: 16,
          padding: '14px 18px',
          background: 'rgba(234, 179, 8, 0.1)',
          border: '1px solid var(--accent-warning)',
          borderRadius: 8,
          fontSize: 13,
        }}>
          <div style={{ fontWeight: 600, color: 'var(--accent-warning)', display: 'flex', alignItems: 'center', gap: 6, fontSize: 14 }}>
            <AlertTriangle size={16} /> ⚠ Task Type Mismatch
          </div>
          <div style={{ marginTop: 6, color: 'var(--text-primary)' }}>
            Target column <code>{targetInfo.target_column}</code> ({targetInfo.target_type}) contains classes:{' '}
            <strong>{targetInfo.classes?.join(' · ') || 'categorical'}</strong>.
          </div>
          <div style={{ marginTop: 4, color: 'var(--text-secondary)' }}>
            {taskType === 'regression'
              ? 'Regression requires a numeric continuous target. String/categorical target labels require Classification.'
              : 'Classification requires discrete or categorical target labels.'}
          </div>
          <button
            className="btn btn--sm btn--primary"
            style={{ marginTop: 10 }}
            onClick={() => {
              setTaskType(targetInfo.task_suggestion);
              setUserCustomTask(false);
              setErrorState(null);
            }}
          >
            Switch to {targetInfo.task_suggestion.charAt(0).toUpperCase() + targetInfo.task_suggestion.slice(1)}
          </button>
        </div>
      )}

      {/* Dataset Size Warning Banner */}
      {targetInfo?.size_info?.size_warning && (
        <div style={{
          marginBottom: 16,
          padding: '12px 16px',
          background: 'rgba(59, 130, 246, 0.08)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          borderRadius: 8,
          fontSize: 13,
          color: 'var(--text-primary)',
        }}>
          <div style={{ fontWeight: 600, color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <AlertTriangle size={15} /> Dataset Evaluation Notice
          </div>
          <div style={{ marginTop: 4, color: 'var(--text-secondary)' }}>
            {targetInfo.size_info.size_warning}
          </div>
          <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-muted)' }}>
            Evidence level: <strong>{targetInfo.size_info.evidence_level}</strong> • {targetInfo.sensor_note}
          </div>
        </div>
      )}

      {/* Data Leakage Warning */}
      {targetInfo?.leakage_info?.warning && (
        <div style={{
          marginBottom: 16,
          padding: '12px 16px',
          background: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid var(--accent-error)',
          borderRadius: 8,
          fontSize: 13,
          color: 'var(--text-primary)',
        }}>
          <div style={{ fontWeight: 600, color: 'var(--accent-error)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <AlertTriangle size={15} /> Potential Data Leakage Notice
          </div>
          <div style={{ marginTop: 4, color: 'var(--text-secondary)' }}>
            {targetInfo.leakage_info.warning}
          </div>
        </div>
      )}

      {/* Structured API error banner */}
      {errorState && (
        <div style={{
          marginBottom: 20,
          padding: '14px 18px',
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid var(--accent-error)',
          borderRadius: 8,
          fontSize: 13,
        }}>
          <div style={{ fontWeight: 600, color: 'var(--accent-error)', display: 'flex', alignItems: 'center', gap: 6, fontSize: 14 }}>
            <AlertTriangle size={16} /> Training Could Not Start
          </div>
          <div style={{ marginTop: 6, color: 'var(--text-primary)' }}>
            <strong>Reason:</strong> {errorState.message || 'Validation error'}
          </div>
          {errorState.details?.suggested_task && (
            <button
              className="btn btn--sm btn--primary"
              style={{ marginTop: 10 }}
              onClick={() => {
                setTaskType(errorState.details.suggested_task);
                setErrorState(null);
              }}
            >
              Switch Task Type to {errorState.details.suggested_task}
            </button>
          )}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Single Model Training */}
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
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>Task Type</span>
                {targetInfo?.task_suggestion === taskType && (
                  <span style={{ fontSize: 11, color: 'var(--accent-success)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <CheckCircle2 size={12} /> Auto-detected from dataset
                  </span>
                )}
              </label>
              <select className="select" value={taskType} onChange={(e) => handleTaskTypeChange(e.target.value)}>
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
            <button
              className="btn btn--primary"
              onClick={handleTrain}
              disabled={training || !datasetId || isMismatch}
              style={{ width: '100%', justifyContent: 'center' }}
            >
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
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>Task Type</span>
                {targetInfo?.task_suggestion === taskType && (
                  <span style={{ fontSize: 11, color: 'var(--accent-success)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <CheckCircle2 size={12} /> Auto-detected from dataset
                  </span>
                )}
              </label>
              <select className="select" value={taskType} onChange={(e) => handleTaskTypeChange(e.target.value)}>
                <option value="classification">Classification</option>
                <option value="regression">Regression</option>
              </select>
            </div>
            <button
              className="btn btn--success"
              onClick={handleAutoML}
              disabled={autoMLRunning || !datasetId || isMismatch}
              style={{ width: '100%', justifyContent: 'center' }}
            >
              <Wand2 size={14} /> {autoMLRunning ? 'Running AutoML...' : 'Train Automatically'}
            </button>
          </div>
        </div>
      </div>

      {/* Training result */}
      {result && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card__header">
            <span className="card__title">Training Result ({result.algorithm})</span>
            <span className="badge badge--success">completed</span>
          </div>
          <div className="card__body">
            <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(6, 1fr)' }}>
              {result.metrics.test_accuracy !== undefined ? (
                <>
                  <div className="stat-card">
                    <div className="stat-card__label">Test Accuracy</div>
                    <div className="stat-card__value" style={{ fontSize: 18, color: 'var(--accent-success)' }}>
                      {(result.metrics.test_accuracy * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-card__label">Train Accuracy</div>
                    <div className="stat-card__value" style={{ fontSize: 18 }}>
                      {(result.metrics.train_accuracy * 100).toFixed(1)}%
                    </div>
                  </div>
                  {result.metrics.cv_accuracy_mean !== undefined && (
                    <div className="stat-card">
                      <div className="stat-card__label">Cross-Val Accuracy</div>
                      <div className="stat-card__value" style={{ fontSize: 15, color: 'var(--accent-primary)' }}>
                        {(result.metrics.cv_accuracy_mean * 100).toFixed(1)}% ± {(result.metrics.cv_accuracy_std * 100).toFixed(1)}%
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{result.metrics.cv_folds}-fold CV</div>
                    </div>
                  )}
                  <div className="stat-card">
                    <div className="stat-card__label">F1 Score (Weighted)</div>
                    <div className="stat-card__value" style={{ fontSize: 18 }}>
                      {(result.metrics.f1_score * 100).toFixed(1)}%
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div className="stat-card">
                    <div className="stat-card__label">Test R² Score</div>
                    <div className="stat-card__value" style={{ fontSize: 18, color: 'var(--accent-success)' }}>
                      {result.metrics.test_r2?.toFixed(3)}
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-card__label">Train R² Score</div>
                    <div className="stat-card__value" style={{ fontSize: 18 }}>
                      {result.metrics.train_r2?.toFixed(3)}
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-card__label">RMSE</div>
                    <div className="stat-card__value" style={{ fontSize: 18 }}>
                      {result.metrics.rmse?.toFixed(4)}
                    </div>
                  </div>
                </>
              )}

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

            {/* Split and Validation Details */}
            {result.metrics.split && (
              <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--border-color)', fontSize: 12, color: 'var(--text-secondary)', display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                <div>
                  <strong>Data Split:</strong> Train: {result.metrics.split.train_count} • Validation: {result.metrics.split.val_count} • Test: {result.metrics.split.test_count} (Total: {result.metrics.split.total_count})
                </div>
                <div>
                  <strong>Stratification:</strong> {result.metrics.split.stratification_applied ? 'Applied' : (result.metrics.split.stratification_reason || 'Disabled')}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* AutoML results */}
      {autoMLResult && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card__header">
            <span className="card__title">AutoML Results</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {autoMLResult.summary.completed} / {autoMLResult.summary.total_models} models ({autoMLResult.summary.dataset_analysis?.detected_task} task)
            </span>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Algorithm</th>
                  <th>Status</th>
                  <th>{autoMLResult.summary.dataset_analysis?.detected_task === 'regression' ? 'Test R²' : 'Test Accuracy'}</th>
                  <th>{autoMLResult.summary.dataset_analysis?.detected_task === 'regression' ? 'CV R²' : 'CV Accuracy'}</th>
                  <th>F1 Score</th>
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
                      {r.metrics?.test_accuracy !== undefined
                        ? `${(r.metrics.test_accuracy * 100).toFixed(1)}%`
                        : (r.metrics?.r2 !== undefined ? r.metrics.r2.toFixed(3) : '—')}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                      {r.metrics?.cv_accuracy_mean !== undefined
                        ? `${(r.metrics.cv_accuracy_mean * 100).toFixed(1)}% ± ${(r.metrics.cv_accuracy_std * 100).toFixed(1)}%`
                        : (r.metrics?.cv_r2_mean !== undefined ? `${r.metrics.cv_r2_mean.toFixed(3)} ± ${r.metrics.cv_r2_std.toFixed(3)}` : 'N/A')}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {r.metrics?.f1_score !== undefined
                        ? `${(r.metrics.f1_score * 100).toFixed(1)}%`
                        : '—'}
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

