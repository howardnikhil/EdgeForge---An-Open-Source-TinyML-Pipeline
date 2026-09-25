import { useAppStore } from '../stores/appStore';
import { Database, Cpu, Layers, FlaskConical, Box, Radio, Bot, Settings, Zap, Play, Scale } from 'lucide-react';

const navItems = [
  { id: 'dashboard', label: 'Project', icon: Box },
  { id: 'serial', label: 'Serial / Collect', icon: Radio },
  { id: 'datasets', label: 'Datasets', icon: Database },
  { id: 'training', label: 'Training', icon: Zap },
  { id: 'experiments', label: 'Experiments', icon: FlaskConical },
  { id: 'hardware', label: 'Hardware', icon: Cpu },
  { id: 'firmware', label: 'Firmware', icon: Layers },
  { id: 'emulation', label: 'MCU Emulation', icon: Play },
  { id: 'validation', label: 'Validation', icon: Scale },
  { id: 'ai', label: 'AI Assistant', icon: Bot },
];

export default function Sidebar() {
  const { activeView, setActiveView, datasets, experiments } = useAppStore();

  return (
    <aside className="sidebar">
      <div className="sidebar__section">
        <div className="sidebar__section-title">Workspace</div>
        {navItems.map((item) => {
          const Icon = item.icon;
          let badge = '';
          if (item.id === 'datasets') badge = datasets.length > 0 ? String(datasets.length) : '';
          if (item.id === 'experiments') badge = experiments.length > 0 ? String(experiments.length) : '';
          return (
            <button
              key={item.id}
              className={`sidebar__item ${activeView === item.id ? 'sidebar__item--active' : ''}`}
              onClick={() => setActiveView(item.id)}
            >
              <Icon size={16} className="sidebar__item-icon" />
              {item.label}
              {badge && <span className="sidebar__item-badge">{badge}</span>}
            </button>
          );
        })}
      </div>

      <div className="sidebar__section" style={{ marginTop: 'auto' }}>
        <button
          className={`sidebar__item ${activeView === 'settings' ? 'sidebar__item--active' : ''}`}
          onClick={() => setActiveView('settings')}
        >
          <Settings size={16} className="sidebar__item-icon" />
          Settings
        </button>
      </div>
    </aside>
  );
}
