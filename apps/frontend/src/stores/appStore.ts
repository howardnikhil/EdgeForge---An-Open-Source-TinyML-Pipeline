import { create } from 'zustand';
import api from '../utils/api';

interface AppState {
  // Current project
  currentProject: any | null;
  projects: any[];
  activeView: string;

  // Data
  datasets: any[];
  experiments: any[];
  models: any[];
  hardwareProfiles: any[];
  jobs: any[];

  // System
  environment: any | null;
  capabilities: any | null;
  backendConnected: boolean;

  // UI
  logs: string[];
  bottomPanelTab: string;
  showInspector: boolean;
  inspectorData: any | null;

  // Actions
  setActiveView: (view: string) => void;
  setCurrentProject: (project: any | null) => void;
  addLog: (log: string) => void;
  setBottomPanelTab: (tab: string) => void;
  toggleInspector: () => void;
  setInspectorData: (data: any) => void;

  // Async actions
  loadProjects: () => Promise<void>;
  loadEnvironment: () => Promise<void>;
  loadProjectData: (projectId: string) => Promise<void>;
  loadHardwareProfiles: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  currentProject: null,
  projects: [],
  activeView: 'welcome',

  datasets: [],
  experiments: [],
  models: [],
  hardwareProfiles: [],
  jobs: [],

  environment: null,
  capabilities: null,
  backendConnected: false,

  logs: [],
  bottomPanelTab: 'output',
  showInspector: true,
  inspectorData: null,

  setActiveView: (view) => set({ activeView: view }),
  setCurrentProject: (project) => set({ currentProject: project }),
  addLog: (log) => set((s) => ({ logs: [...s.logs.slice(-500), `[${new Date().toLocaleTimeString()}] ${log}`] })),
  setBottomPanelTab: (tab) => set({ bottomPanelTab: tab }),
  toggleInspector: () => set((s) => ({ showInspector: !s.showInspector })),
  setInspectorData: (data) => set({ inspectorData: data, showInspector: true }),

  loadProjects: async () => {
    try {
      const projects = await api.listProjects();
      set({ projects, backendConnected: true });
      get().addLog('Projects loaded');
    } catch (e) {
      set({ backendConnected: false });
      get().addLog(`Failed to load projects: ${e}`);
    }
  },

  loadEnvironment: async () => {
    try {
      const [env, caps] = await Promise.all([api.environment(), api.capabilities()]);
      set({ environment: env, capabilities: caps, backendConnected: true });
      get().addLog('Environment detected');
    } catch (e) {
      set({ backendConnected: false });
      get().addLog(`Backend connection failed: ${e}`);
    }
  },

  loadProjectData: async (projectId: string) => {
    try {
      const [datasets, experiments, models, jobs] = await Promise.all([
        api.listDatasets(projectId),
        api.listExperiments(projectId),
        api.listModels(projectId),
        api.listJobs(projectId),
      ]);
      set({ datasets, experiments, models, jobs });
    } catch (e) {
      get().addLog(`Failed to load project data: ${e}`);
    }
  },

  loadHardwareProfiles: async () => {
    try {
      const profiles = await api.listHardwareProfiles();
      set({ hardwareProfiles: profiles });
    } catch (e) {
      get().addLog(`Failed to load hardware profiles: ${e}`);
    }
  },
}));
