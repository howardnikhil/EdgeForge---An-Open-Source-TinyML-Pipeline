# HowNik's EdgeForge — Architecture

## Overview

EdgeForge is a local-first TinyML / Edge-AI engineering IDE. It runs as a localhost web application with a Python backend (FastAPI) and React/TypeScript frontend (Vite).

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Browser (localhost:5173)                   │
│                                                                │
│  React + TypeScript + Vite                                     │
│  ┌──────────┬──────────────────────────┬──────────────┐       │
│  │ Project  │    Main Workspace        │  Inspector   │       │
│  │ Explorer │    (Context-dependent)   │  Panel       │       │
│  │          │                          │              │       │
│  └──────────┴──────────────────────────┴──────────────┘       │
│  └─────────────── Terminal / Logs Panel ──────────────────┘   │
└───────────────────────────┬──────────────────────────────────┘
                            │ REST + WebSocket
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (localhost:8000)              │
│                                                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │ Project    │  │ Dataset    │  │ ML Engine  │              │
│  │ Manager    │  │ Manager    │  │            │              │
│  ├────────────┤  ├────────────┤  ├────────────┤              │
│  │ Serial     │  │ Preprocess │  │ AutoML     │              │
│  │ Manager    │  │ Engine     │  │ Engine     │              │
│  ├────────────┤  ├────────────┤  ├────────────┤              │
│  │ Hardware   │  │ Firmware   │  │ Emulation  │              │
│  │ Profiles   │  │ Generator  │  │ Engine     │              │
│  ├────────────┤  ├────────────┤  ├────────────┤              │
│  │ Job        │  │ AI Agent   │  │ Validation │              │
│  │ Manager    │  │ Engine     │  │ Engine     │              │
│  └────────────┘  └────────────┘  └────────────┘              │
│                                                                │
│  ┌─────────────────────────────────────────────┐              │
│  │              SQLite Database                 │              │
│  └─────────────────────────────────────────────┘              │
│                                                                │
│  ┌─────────────────────────────────────────────┐              │
│  │           Background Job Runner              │              │
│  │  (asyncio + multiprocessing)                 │              │
│  └─────────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for build/dev
- **Zustand** for state management (lightweight, no boilerplate)
- **React Flow** for node-based pipeline editor
- **Recharts** for data visualization
- **Monaco Editor** for code viewing
- **xterm.js** for terminal emulation
- Vanilla CSS with CSS custom properties (design tokens)

### Backend
- **Python 3.10+** with **FastAPI**
- **SQLAlchemy 2.0** with **SQLite**
- **Alembic** for migrations
- **asyncio** + **multiprocessing** for background jobs
- **pyserial** for serial communication
- **WebSocket** for real-time updates (training progress, serial data, logs)

### ML Frameworks
- **scikit-learn** — classical ML (Decision Trees, Random Forest, SVM, KNN, etc.)
- **PyTorch** — neural networks (CNN, DS-CNN, RNN)
- **ONNX** — model interchange format
- **TensorFlow Lite** — quantization and MCU runtime (via `tflite-runtime`)

### Embedded Toolchain
- **PlatformIO** — firmware compilation (ESP32, RP2040, Arduino)
- **Renode** — embedded system emulation (where supported)

## MVP Scope Decision

Based on the environment assessment and the requirement for NO FAKE FUNCTIONALITY, the MVP will implement these genuinely working features:

### ✓ Fully Implemented
1. **Project System** — Create, save, load, export/import projects with YAML config
2. **Serial Data Collection** — USB serial port enumeration, connection, data capture
3. **Dataset Management** — Import (CSV/serial), labeling, splitting, statistics, versioning
4. **Data Visualization** — Time-series plots, statistics, distribution charts
5. **Preprocessing Engine** — Normalization, windowing, feature extraction, reproducible pipelines
6. **ML Training** — scikit-learn models (Decision Tree, Random Forest, SVM, KNN, etc.)
7. **AutoML** — Dataset analysis → algorithm selection → hyperparameter search → training
8. **Experiment Tracking** — Full experiment records with reproducibility metadata
9. **Model Export** — ONNX export, C array export for MCU deployment
10. **Hardware Profiles** — ESP32, ESP32-S3, RP2040, Arduino UNO profiles with memory/arch specs
11. **Hardware Compatibility Analysis** — Model size vs target memory, operator compatibility
12. **Firmware Generation** — PlatformIO/Arduino project generation with model + inference code
13. **AI Assistant** — Multi-provider chat with project context inspection
14. **Settings System** — Complete settings with API key management, compute, appearance
15. **Job System** — Background training/processing with progress, cancellation, logs
16. **Pipeline Editor** — Visual node-based pipeline with real execution
17. **Custom Sensor Editor** — Define custom sensor types with fields/units
18. **Quantization** — INT8 quantization with accuracy comparison

### ⚡ Architectural Extension Points (NOT exposed as features)
- Firmware compilation (requires PlatformIO installation — detected at runtime)
- MCU emulation (requires Renode/QEMU — detected at runtime)
- Physical flashing
- Power measurement
- Plugin loading

These become available when the user installs the required toolchains. The UI gracefully detects and enables them.

## Database Schema

```sql
-- Core entities
projects          (id, name, description, type, path, created, updated)
datasets          (id, project_id, name, version, type, path, split_config, stats)
sensors           (id, project_id, name, interface, fields_json, sample_rate)
pipelines         (id, project_id, name, nodes_json, edges_json, config)
experiments       (id, project_id, dataset_id, pipeline_id, algorithm, config,
                   metrics, model_path, status, created, seed, framework_version)
models            (id, experiment_id, name, format, path, size, input_shape,
                   output_shape, quantization, metadata)
hardware_profiles (id, name, architecture, flash, ram, cpu_freq, toolchain,
                   runtime, emulator, operators_json)
jobs              (id, project_id, type, status, progress, config, result,
                   logs, created, started, completed)
ai_conversations  (id, project_id, messages_json, provider, created)
settings          (key, value, category)
```

## API Structure

```
/api/v1/
  /projects/          CRUD + export/import
  /datasets/          CRUD + import/split/stats/visualize
  /sensors/           CRUD + enumerate ports + connect
  /serial/            connect/disconnect/monitor (+ WebSocket)
  /pipelines/         CRUD + execute
  /training/          start/stop/status
  /experiments/       CRUD + compare
  /models/            CRUD + export/quantize/analyze
  /hardware/          profiles + compatibility check
  /firmware/          generate + compile status
  /emulation/         start/stop/status/report
  /jobs/              list/status/cancel
  /ai/                chat + providers + actions
  /settings/          CRUD
  /system/            health + environment + capabilities
```

## Security Model
- Backend binds to 127.0.0.1 only
- Path traversal protection on all file operations
- API keys stored in OS keyring (via `keyring` library), fallback to encrypted local file
- AI agent commands requiring confirmation: flash, delete, shell exec, install
- No credentials in logs or project files

## Job System
- Uses Python `multiprocessing.Process` for CPU-intensive work (training)
- `asyncio` tasks for I/O-bound work (serial, AI API calls)
- WebSocket channels for real-time progress updates
- Job states: QUEUED → RUNNING → COMPLETED/FAILED/CANCELLED
- Each job has its own log file in the project directory

## File System Layout
```
edgeforge/
├── apps/
│   ├── frontend/          # React + Vite
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── pages/
│   │   │   ├── stores/
│   │   │   ├── hooks/
│   │   │   ├── utils/
│   │   │   ├── types/
│   │   │   └── styles/
│   │   └── package.json
│   └── backend/           # FastAPI
│       ├── api/
│       ├── core/
│       ├── models/        # SQLAlchemy models
│       ├── services/
│       ├── jobs/
│       └── main.py
├── core/
│   ├── datasets/
│   ├── preprocessing/
│   ├── automl/
│   ├── ml/
│   ├── quantization/
│   ├── hardware/
│   ├── firmware/
│   ├── emulation/
│   ├── validation/
│   └── plugins/
├── hardware/
│   └── profiles/          # YAML hardware profiles
├── examples/
├── docs/
├── tests/
├── scripts/
├── start.sh
├── LICENSE
├── NOTICE
├── README.md
├── CONTRIBUTING.md
└── ARCHITECTURE.md
```
