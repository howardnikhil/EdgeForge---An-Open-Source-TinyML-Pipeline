# HowNik's EdgeForge ⚡

<div align="center">

<img src="apps/frontend/public/assets/edgeforge-logo.png" alt="HowNik's EdgeForge Logo" width="120" height="120" />

### An Open-Source, Local-First TinyML & Edge-AI Engineering IDE

*From raw sensor data collection and dataset preparation to hardware-aware AutoML, real MCU firmware compilation, embedded emulation, and cross-platform validation.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Vite](https://img.shields.io/badge/Vite-5.0%2B-646cff.svg)](https://vitejs.dev/)

[Quick Start](#-quick-start) • [Core Features](#-core-features) • [System Architecture](#-system-architecture) • [Hardware Target Matrix](#-hardware-target-matrix) • [Contributing](#-contributing)

</div>

---

## 🚀 Overview

**HowNik's EdgeForge** is a local-first, privacy-focused TinyML / Edge-AI engineering platform built to bridge the gap between machine learning models and resource-constrained embedded hardware.

Unlike traditional cloud-based ML dashboards, EdgeForge runs 100% locally on your machine, providing **hardware-aware model development + real embedded firmware compilation + real MCU emulation & parity validation**.

---

## ✨ Core Features

### 🔌 1. Real-Time Data Collection & Serial Streaming
- Connect directly to physical microcontrollers via USB Serial (`/dev/tty*` / `COM*`).
- Real-time time-series graphing and automated sample chunking.
- Multi-format import support (`CSV`, raw time-series data, serial stream dumps).

### 🧹 2. Dataset Engineering & Preprocessing
- Automated signal preprocessing (normalization, sliding window extraction, FFT, statistical features).
- Interactive visual dataset splitters (train, validation, test).
- Reproducible, version-controlled preprocessing pipeline configurations (`project.yaml`).

### 🤖 3. Hardware-Aware AutoML & ML Training
- Automated algorithm selection tuned for embedded microcontrollers (Decision Trees, Random Forests, SVMs, KNN, PyTorch Neural Networks, DS-CNN).
- Quantization tools (Float32 to INT8/UINT8) with real-time accuracy vs. memory tradeoff reporting.
- Model exports in `C/C++ Header Byte Arrays`, `ONNX`, and `TFLite` formats.

### 🛠️ 4. Real Firmware Generation & Compilation
- Generates production-ready C/C++ firmware projects for embedded platforms.
- Integrates directly with build toolchains (PlatformIO, GCC ARM, Xtensa) to produce true executable binaries (`.elf`, `.bin`).
- Dynamic memory calculation (SRAM / Flash footprint) against target hardware profiles.

### 📟 5. MCU Emulation & Desktop vs. MCU Validation
- Real embedded system emulation runtime (Renode / QEMU pipeline integration).
- Replays dataset samples directly through emulated MCU firmware.
- Captures MCU-side inference results and measures accuracy parity between Desktop ML and MCU target execution.

### 🧠 6. Context-Aware AI Engineering Assistant
- Built-in multi-provider LLM assistant (OpenAI, Anthropic, Ollama, Custom API).
- Live inspection of active project datasets, trained model performance, C firmware source code, and hardware specifications.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Browser UI (localhost:5173)                 │
│                                                                 │
│  React 18 + TypeScript + Vite + Zustand                        │
│  ┌────────────┬──────────────────────────────┬───────────────┐  │
│  │ Project    │ Main Workspace               │ Inspector     │  │
│  │ Navigation │ (Datasets, Training, Firmware)│ Panel         │  │
│  └────────────┴──────────────────────────────┴───────────────┘  │
│  └──────────────── Bottom Development Console ─────────────────┘  │
└────────────────────────────────┬────────────────────────────────┘
                                 │ REST APIs + WebSockets
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (localhost:8000)              │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐         │
│  │ Serial & USB │   │ Preprocess & │   │ AutoML & ML  │         │
│  │ Streamer     │   │ Dataset Mgt  │   │ Trainer      │         │
│  ├──────────────┤   ├──────────────┤   ├──────────────┤         │
│  │ Hardware     │   │ Firmware C   │   │ MCU          │         │
│  │ Inspector    │   │ Generator    │   │ Emulator     │         │
│  ├──────────────┤   ├──────────────┤   ├──────────────┤         │
│  │ Job Runner   │   │ AI Agent     │   │ Validation   │         │
│  │ (Async/MP)   │   │ Engine       │   │ Pipeline     │         │
│  └──────────────┘   └──────────────┘   └──────────────┘         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    SQLite Database                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Hardware Target Matrix

EdgeForge includes pre-configured hardware profiles and RAM/Flash constraints for popular microcontrollers:

| Target MCU / Board | Architecture | Max RAM | Max Flash | Clock Speed | Compiler Toolchain | Emulation Support |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ESP32** | Xtensa LX6 | 520 KB | 4 MB | 240 MHz | `espressif32` | Supported |
| **ESP32-S3** | Xtensa LX7 (Vector AI) | 512 KB + PSRAM | 8 MB | 240 MHz | `espressif32` | Supported |
| **RP2040 (Raspberry Pi Pico)** | Dual ARM Cortex-M0+ | 264 KB | 2 MB | 133 MHz | `earlephilhower` / `gcc-arm` | Supported |
| **Arduino Uno** | ATmega328P | 2 KB | 32 KB | 16 MHz | `avr-gcc` | Direct Static |
| **STM32F401 (BlackPill)** | ARM Cortex-M4F | 96 KB | 512 KB | 84 MHz | `ststm32` | Supported |

---

## 🏁 Quick Start

### Prerequisites
- **Python**: `3.10` or higher
- **Node.js**: `18.0` or higher (`npm`)
- **Git**

### Automated Launch (One-Line)

Clone the repository and run the startup script:

```bash
git clone https://github.com/howardnikhil/EdgeForge---An-Open-Source-TinyML-Pipeline.git
cd EdgeForge---An-Open-Source-TinyML-Pipeline
chmod +x start.sh
./start.sh
```

The script will automatically set up Python virtual environments, install dependencies, build the frontend, launch the FastAPI server at `http://127.0.0.1:8000`, and start the Vite frontend at `http://127.0.0.1:5173`.

---

## 📁 Repository Structure

```
EdgeForge/
├── apps/
│   ├── frontend/                 # React 18 + Vite Web Application
│   │   ├── public/assets/        # Static EdgeForge assets & icons
│   │   ├── src/
│   │   │   ├── components/       # Layout, Header, Console, Inspector
│   │   │   ├── pages/            # Workspace view pages (Datasets, AutoML, Firmware, Emulation, etc.)
│   │   │   ├── stores/           # Zustand state store
│   │   │   └── utils/            # REST & WebSocket API clients
│   │   └── package.json
│   │
│   └── backend/                  # FastAPI Python Server
│       ├── api/routes/           # API endpoints (serial, datasets, training, emulation, validation)
│       ├── core/                 # Core engines (preprocessing, c_generator, compiler, emulator)
│       ├── models/               # Database schemas & models
│       ├── main.py               # Application entrypoint
│       └── pyproject.toml
│
├── examples/                     # Sample TinyML projects & datasets
│   └── imu_gesture_classifier/   # 6-axis IMU Gesture recognition example
├── tests/                        # Backend and real embedded pipeline test suites
├── start.sh                      # Launch script for development & production
├── ARCHITECTURE.md               # Technical architecture specification
└── README.md                     # Project documentation
```

---

## 🧪 Testing & Verification

Run the full backend test suite:

```bash
cd apps/backend
pytest ../../tests/backend/test_api.py ../../tests/backend/test_real_embedded_pipeline.py -v
```

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more details.

---

<div align="center">
  <b>Developed by HowNik</b> • <i>Open-Source TinyML for Everyone</i>
</div>
