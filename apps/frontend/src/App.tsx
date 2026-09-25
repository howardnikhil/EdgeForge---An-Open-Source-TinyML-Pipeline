import { useEffect } from 'react';
import { useAppStore } from './stores/appStore';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import BottomPanel from './components/BottomPanel';
import Inspector from './components/Inspector';
import WelcomePage from './pages/WelcomePage';
import ProjectDashboard from './pages/ProjectDashboard';
import DatasetPage from './pages/DatasetPage';
import TrainingPage from './pages/TrainingPage';
import ExperimentsPage from './pages/ExperimentsPage';
import HardwarePage from './pages/HardwarePage';
import FirmwarePage from './pages/FirmwarePage';
import EmulationPage from './pages/EmulationPage';
import ValidationPage from './pages/ValidationPage';
import SettingsPage from './pages/SettingsPage';
import AIAssistantPage from './pages/AIAssistantPage';
import SerialPage from './pages/SerialPage';
import ErrorBoundary from './components/ErrorBoundary';
import './App.css';

function App() {
  const { activeView, currentProject, showInspector, loadProjects, loadEnvironment } = useAppStore();

  useEffect(() => {
    loadEnvironment();
    loadProjects();
  }, []);

  const renderMainContent = () => {
    if (!currentProject && activeView !== 'settings' && activeView !== 'welcome') {
      return <WelcomePage />;
    }

    switch (activeView) {
      case 'welcome': return <WelcomePage />;
      case 'dashboard': return <ProjectDashboard />;
      case 'datasets': return <DatasetPage />;
      case 'serial': return <SerialPage />;
      case 'training': return <TrainingPage />;
      case 'experiments': return <ExperimentsPage />;
      case 'hardware': return <HardwarePage />;
      case 'firmware': return <FirmwarePage />;
      case 'emulation': return <EmulationPage />;
      case 'validation': return <ValidationPage />;
      case 'ai': return <AIAssistantPage />;
      case 'settings': return <SettingsPage />;
      default: return <WelcomePage />;
    }
  };

  return (
    <div className="app-layout">
      <Header />
      <div className="app-body">
        {currentProject && <Sidebar />}
        <div className="main-content">
          <div className="workspace">
            <ErrorBoundary fallbackTitle={`Error rendering ${activeView} page`}>
              {renderMainContent()}
            </ErrorBoundary>
          </div>
          {currentProject && <BottomPanel />}
        </div>
        {currentProject && showInspector && <Inspector />}
      </div>
    </div>
  );
}

export default App;
