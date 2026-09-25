"""System health and environment detection API."""
import platform
import shutil
import sys
from fastapi import APIRouter

router = APIRouter()


def _check_command(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _check_python_module(module: str) -> dict:
    try:
        mod = __import__(module)
        return {"available": True, "version": getattr(mod, "__version__", "unknown")}
    except ImportError:
        return {"available": False, "version": None}


@router.get("/health")
async def health():
    return {"status": "ok", "name": "HowNik's EdgeForge", "version": "0.1.0"}


@router.get("/environment")
async def environment():
    """Detect system environment and available toolchains."""
    ml_frameworks = {
        "scikit-learn": _check_python_module("sklearn"),
        "numpy": _check_python_module("numpy"),
        "pandas": _check_python_module("pandas"),
        "pytorch": _check_python_module("torch"),
        "tensorflow": _check_python_module("tensorflow"),
        "xgboost": _check_python_module("xgboost"),
        "lightgbm": _check_python_module("lightgbm"),
        "onnx": _check_python_module("onnx"),
    }

    toolchains = {
        "platformio": _check_command("pio"),
        "arduino_cli": _check_command("arduino-cli"),
    }

    emulators = {
        "renode": _check_command("renode"),
        "qemu": _check_command("qemu-system-arm"),
    }

    # Detect GPU
    gpu = {"available": False, "type": None, "name": None}
    try:
        import torch
        if torch.cuda.is_available():
            gpu = {"available": True, "type": "cuda", "name": torch.cuda.get_device_name(0)}
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            gpu = {"available": True, "type": "mps", "name": "Apple Silicon GPU"}
    except ImportError:
        pass

    return {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "python": {
            "version": platform.python_version(),
            "path": sys.executable,
        },
        "node": _check_command("node"),
        "git": _check_command("git"),
        "ml_frameworks": ml_frameworks,
        "toolchains": toolchains,
        "emulators": emulators,
        "gpu": gpu,
    }


@router.get("/capabilities")
async def capabilities():
    """Return which EdgeForge features are available based on installed tools."""
    caps = {
        "serial_collection": True,  # pyserial based
        "dataset_management": True,
        "preprocessing": True,
        "ml_training_sklearn": _check_python_module("sklearn")["available"],
        "ml_training_pytorch": _check_python_module("torch")["available"],
        "ml_training_xgboost": _check_python_module("xgboost")["available"],
        "model_export_onnx": _check_python_module("onnx")["available"],
        "quantization_int8": _check_python_module("onnx")["available"],
        "firmware_generation": True,  # code generation always works
        "firmware_compilation": _check_command("pio"),
        "emulation_renode": _check_command("renode"),
        "emulation_qemu": _check_command("qemu-system-arm"),
        "hardware_flashing": _check_command("pio"),
        "ai_assistant": True,  # requires user API key config
    }
    return caps
