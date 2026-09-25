const API_BASE = 'http://127.0.0.1:8000/api/v1';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(error.detail || `HTTP ${resp.status}`);
  }

  return resp.json();
}

export const api = {
  // System
  health: () => request<any>('/system/health'),
  environment: () => request<any>('/system/environment'),
  capabilities: () => request<any>('/system/capabilities'),

  // Projects
  listProjects: () => request<any[]>('/projects'),
  createProject: (data: { name: string; description?: string; project_type?: string }) =>
    request<any>('/projects', { method: 'POST', body: JSON.stringify(data) }),
  getProject: (id: string) => request<any>(`/projects/${id}`),
  deleteProject: (id: string, deleteFiles = false) =>
    request<any>(`/projects/${id}?delete_files=${deleteFiles}`, { method: 'DELETE' }),

  // Datasets
  listDatasets: (projectId: string) => request<any[]>(`/datasets?project_id=${projectId}`),
  getDataset: (id: string) => request<any>(`/datasets/${id}`),
  getDatasetStats: (id: string) => request<any>(`/datasets/${id}/statistics`),
  splitDataset: (id: string, config: any) =>
    request<any>(`/datasets/${id}/split`, { method: 'POST', body: JSON.stringify(config) }),
  updateLabels: (id: string, data: any) =>
    request<any>(`/datasets/${id}/label`, { method: 'POST', body: JSON.stringify(data) }),
  importCsv: async (projectId: string, name: string, file: File, datasetType = 'timeseries') => {
    const formData = new FormData();
    formData.append('project_id', projectId);
    formData.append('name', name);
    formData.append('dataset_type', datasetType);
    formData.append('file', file);
    const resp = await fetch(`${API_BASE}/datasets/import-csv`, { method: 'POST', body: formData });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || 'Import failed');
    }
    return resp.json();
  },
  deleteDataset: (id: string) => request<any>(`/datasets/${id}`, { method: 'DELETE' }),

  // Serial
  listPorts: () => request<any>('/serial/ports'),
  connectPort: (port: string, baudRate: number) =>
    request<any>('/serial/connect', { method: 'POST', body: JSON.stringify({ port, baud_rate: baudRate }) }),
  disconnectPort: (port: string) =>
    request<any>(`/serial/disconnect?port=${encodeURIComponent(port)}`, { method: 'POST' }),
  serialStatus: () => request<any>('/serial/status'),

  // Training
  trainModel: (data: any) => request<any>('/training/train', { method: 'POST', body: JSON.stringify(data) }),
  runAutoML: (data: any) => request<any>('/training/automl', { method: 'POST', body: JSON.stringify(data) }),

  // Experiments
  listExperiments: (projectId: string) => request<any[]>(`/experiments?project_id=${projectId}`),
  getExperiment: (id: string) => request<any>(`/experiments/${id}`),
  compareExperiments: (ids: string[]) =>
    request<any>('/experiments/compare', { method: 'POST', body: JSON.stringify(ids) }),
  deleteExperiment: (id: string) => request<any>(`/experiments/${id}`, { method: 'DELETE' }),

  // Models
  listModels: (projectId: string) => request<any[]>(`/models?project_id=${projectId}`),
  getModel: (id: string) => request<any>(`/models/${id}`),
  exportOnnx: (experimentId: string) =>
    request<any>(`/models/export-onnx?experiment_id=${experimentId}`, { method: 'POST' }),
  exportCArray: (experimentId: string) =>
    request<any>(`/models/export-c-array?experiment_id=${experimentId}`, { method: 'POST' }),

  // Hardware
  listHardwareProfiles: () => request<any[]>('/hardware/profiles'),
  getHardwareProfile: (id: string) => request<any>(`/hardware/profiles/${id}`),
  checkCompatibility: (experimentId: string, hardwareId: string) =>
    request<any>(`/hardware/compatibility?experiment_id=${experimentId}&hardware_id=${hardwareId}`, { method: 'POST' }),
  compatibilityMatrix: (experimentIds: string[]) =>
    request<any>('/hardware/compatibility-matrix', { method: 'POST', body: JSON.stringify(experimentIds) }),

  // Firmware
  generateFirmware: (data: any) =>
    request<any>('/firmware/generate', { method: 'POST', body: JSON.stringify(data) }),
  compileFirmware: (data: { project_id: string; experiment_id: string; hardware_id: string }) =>
    request<any>('/firmware/compile', { method: 'POST', body: JSON.stringify(data) }),
  getBuildLog: (firmwarePath: string) =>
    request<any>(`/firmware/build-log?firmware_path=${encodeURIComponent(firmwarePath)}`),

  // Emulation
  runEmulation: (data: { project_id: string; experiment_id: string; dataset_id: string; hardware_id: string; emulator_type?: string; max_samples?: number }) =>
    request<any>('/emulation/run', { method: 'POST', body: JSON.stringify(data) }),

  // Validation
  runValidation: (data: { project_id: string; experiment_id: string; dataset_id: string; hardware_id: string; max_samples?: number }) =>
    request<any>('/validation/run', { method: 'POST', body: JSON.stringify(data) }),

  // Pipelines
  listPipelines: (projectId: string) => request<any[]>(`/pipelines?project_id=${projectId}`),
  createPipeline: (data: any) =>
    request<any>('/pipelines', { method: 'POST', body: JSON.stringify(data) }),
  updatePipeline: (id: string, data: any) =>
    request<any>(`/pipelines/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  // Jobs
  listJobs: (projectId?: string) =>
    request<any[]>(`/jobs${projectId ? `?project_id=${projectId}` : ''}`),
  getJob: (id: string) => request<any>(`/jobs/${id}`),
  cancelJob: (id: string) => request<any>(`/jobs/${id}/cancel`, { method: 'POST' }),

  // AI
  listAIProviders: () => request<any[]>('/ai/providers'),
  chat: (data: any) => request<any>('/ai/chat', { method: 'POST', body: JSON.stringify(data) }),

  // Settings
  listSettings: (category?: string) =>
    request<any[]>(`/settings${category ? `?category=${category}` : ''}`),
  updateSetting: (key: string, value: string, category = 'general') =>
    request<any>('/settings', { method: 'PUT', body: JSON.stringify({ key, value, category }) }),
  deleteSetting: (key: string) => request<any>(`/settings/${key}`, { method: 'DELETE' }),
};

export default api;
