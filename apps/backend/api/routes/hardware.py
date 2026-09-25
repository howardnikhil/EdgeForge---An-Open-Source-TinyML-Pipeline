"""Hardware profile management and compatibility analysis API."""
import os
import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session
from models.db_models import HardwareProfile, Experiment

router = APIRouter()

# Built-in hardware profiles
BUILTIN_PROFILES = [
    {
        "name": "Native Host MCU Target",
        "architecture": "x86_64 / arm64",
        "flash_bytes": 16 * 1024 * 1024,
        "ram_bytes": 8 * 1024 * 1024,
        "cpu_freq_mhz": 2000,
        "toolchain": "gcc / g++",
        "runtime": "native-c",
        "emulator": "native",
        "deployment_formats": ["platformio", "native"],
        "supported_operators": ["ALL_OPERATORS"],
        "config": {"platform": "native"},
    },
    {
        "name": "ESP32",
        "architecture": "xtensa-lx6",
        "flash_bytes": 4 * 1024 * 1024,  # 4MB
        "ram_bytes": 520 * 1024,  # 520KB
        "cpu_freq_mhz": 240,
        "toolchain": "xtensa-esp32-elf-gcc",
        "runtime": "tflite-micro",
        "emulator": "renode",
        "deployment_formats": ["platformio", "esp-idf", "arduino"],
        "supported_operators": [
            "FULLY_CONNECTED", "CONV_2D", "DEPTHWISE_CONV_2D", "AVERAGE_POOL_2D",
            "MAX_POOL_2D", "SOFTMAX", "RESHAPE", "ADD", "MUL", "RELU", "RELU6",
            "QUANTIZE", "DEQUANTIZE", "LOGISTIC", "CONCATENATION",
        ],
        "config": {
            "board": "esp32dev",
            "framework": "arduino",
            "platform": "espressif32",
            "flash_mode": "dio",
            "flash_speed": "40000000",
        },
    },
    {
        "name": "ESP32-S3",
        "architecture": "xtensa-lx7",
        "flash_bytes": 8 * 1024 * 1024,  # 8MB
        "ram_bytes": 512 * 1024,  # 512KB SRAM
        "cpu_freq_mhz": 240,
        "toolchain": "xtensa-esp32s3-elf-gcc",
        "runtime": "tflite-micro",
        "emulator": "renode",
        "deployment_formats": ["platformio", "esp-idf", "arduino"],
        "supported_operators": [
            "FULLY_CONNECTED", "CONV_2D", "DEPTHWISE_CONV_2D", "AVERAGE_POOL_2D",
            "MAX_POOL_2D", "SOFTMAX", "RESHAPE", "ADD", "MUL", "RELU", "RELU6",
            "QUANTIZE", "DEQUANTIZE", "LOGISTIC", "CONCATENATION",
            "CONV_1D", "BATCH_NORM",
        ],
        "config": {
            "board": "esp32-s3-devkitc-1",
            "framework": "arduino",
            "platform": "espressif32",
            "psram": True,
        },
    },
    {
        "name": "RP2040",
        "architecture": "arm-cortex-m0+",
        "flash_bytes": 2 * 1024 * 1024,  # 2MB
        "ram_bytes": 264 * 1024,  # 264KB
        "cpu_freq_mhz": 133,
        "toolchain": "arm-none-eabi-gcc",
        "runtime": "tflite-micro",
        "emulator": "renode",
        "deployment_formats": ["platformio", "arduino", "cmake"],
        "supported_operators": [
            "FULLY_CONNECTED", "CONV_2D", "AVERAGE_POOL_2D", "MAX_POOL_2D",
            "SOFTMAX", "RESHAPE", "ADD", "RELU", "QUANTIZE", "DEQUANTIZE",
        ],
        "config": {
            "board": "pico",
            "framework": "arduino",
            "platform": "raspberrypi",
        },
    },
    {
        "name": "Arduino UNO",
        "architecture": "avr-atmega328p",
        "flash_bytes": 32 * 1024,  # 32KB
        "ram_bytes": 2 * 1024,  # 2KB
        "cpu_freq_mhz": 16,
        "toolchain": "avr-gcc",
        "runtime": "custom-c",
        "emulator": "",
        "deployment_formats": ["arduino", "platformio"],
        "supported_operators": [
            "FULLY_CONNECTED", "SOFTMAX",
        ],
        "config": {
            "board": "uno",
            "framework": "arduino",
            "platform": "atmelavr",
            "note": "Very limited memory — only tiny models (decision trees, small lookup tables)",
        },
    },
]


@router.get("/profiles")
async def list_profiles(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(HardwareProfile))
    profiles = result.scalars().all()

    # If no profiles exist, seed built-in ones
    if not profiles:
        for p in BUILTIN_PROFILES:
            existing = await session.execute(select(HardwareProfile).where(HardwareProfile.name == p["name"]))
            if not existing.scalar_one_or_none():
                profile = HardwareProfile(
                    name=p["name"],
                    architecture=p["architecture"],
                    flash_bytes=p["flash_bytes"],
                    ram_bytes=p["ram_bytes"],
                    cpu_freq_mhz=p["cpu_freq_mhz"],
                    toolchain=p["toolchain"],
                    runtime=p["runtime"],
                    emulator=p["emulator"],
                    deployment_formats=p["deployment_formats"],
                    supported_operators=p["supported_operators"],
                    config=p["config"],
                    is_builtin=True,
                )
                session.add(profile)
        try:
            await session.commit()
        except Exception:
            await session.rollback()
        result = await session.execute(select(HardwareProfile))
        profiles = result.scalars().all()

    return [
        {
            "id": p.id, "name": p.name, "architecture": p.architecture,
            "flash_bytes": p.flash_bytes, "ram_bytes": p.ram_bytes,
            "flash_display": _format_bytes(p.flash_bytes),
            "ram_display": _format_bytes(p.ram_bytes),
            "cpu_freq_mhz": p.cpu_freq_mhz,
            "toolchain": p.toolchain, "runtime": p.runtime,
            "emulator": p.emulator,
            "deployment_formats": p.deployment_formats,
            "is_builtin": p.is_builtin,
        }
        for p in profiles
    ]


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(HardwareProfile).where(HardwareProfile.id == profile_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Hardware profile not found")

    return {
        "id": p.id, "name": p.name, "architecture": p.architecture,
        "flash_bytes": p.flash_bytes, "ram_bytes": p.ram_bytes,
        "cpu_freq_mhz": p.cpu_freq_mhz,
        "toolchain": p.toolchain, "runtime": p.runtime,
        "emulator": p.emulator,
        "deployment_formats": p.deployment_formats,
        "supported_operators": p.supported_operators,
        "config": p.config,
    }


@router.post("/compatibility")
async def check_compatibility(
    experiment_id: str,
    hardware_id: str,
    session: AsyncSession = Depends(get_session),
):
    exp_result = await session.execute(select(Experiment).where(Experiment.id == experiment_id))
    exp = exp_result.scalar_one_or_none()
    if not exp:
        raise HTTPException(404, "Experiment not found")

    hw_result = await session.execute(select(HardwareProfile).where(HardwareProfile.id == hardware_id))
    hw = hw_result.scalar_one_or_none()
    if not hw:
        raise HTTPException(404, "Hardware profile not found")

    from core.hardware.compatibility import analyze_hardware_compatibility
    
    hw_dict = {
        "name": hw.name,
        "flash_bytes": hw.flash_bytes,
        "ram_bytes": hw.ram_bytes,
    }
    n_features = exp.input_shape[0] if exp.input_shape else 4
    n_classes = len(exp.output_shape) if exp.output_shape else 2

    analysis = analyze_hardware_compatibility(
        model_size_bytes=exp.model_size_bytes,
        n_features=n_features,
        n_classes=n_classes,
        algorithm=exp.algorithm,
        hardware_profile=hw_dict
    )

    issues = []
    if not analysis["compatible"]:
        for r in analysis["remediations"]:
            issues.append({
                "type": "MEMORY_EXCEEDED",
                "severity": "error",
                "message": r,
                "remedies": [r],
            })

    flash_breakdown = analysis["breakdown"]["flash"]
    ram_breakdown = analysis["breakdown"]["ram"]

    return {
        "hardware": {
            "name": hw.name,
            "architecture": hw.architecture,
        },
        "experiment": {
            "name": exp.name,
            "algorithm": exp.algorithm,
        },
        "compatible": analysis["compatible"],
        "issues": issues,
        "remediations": analysis["remediations"],
        "flash": {
            "ok": flash_breakdown["required_bytes"] <= hw.flash_bytes,
            "usage_percent": round(flash_breakdown["used_percentage"], 1),
            "model_bytes": exp.model_size_bytes,
            "total_bytes": hw.flash_bytes,
            "required_bytes": flash_breakdown["required_bytes"],
            "sdk_base_bytes": flash_breakdown["sdk_base_bytes"],
            "runtime_code_bytes": flash_breakdown["runtime_code_bytes"],
        },
        "ram": {
            "ok": ram_breakdown["required_bytes"] <= hw.ram_bytes,
            "estimated_bytes": ram_breakdown["required_bytes"],
            "total_bytes": hw.ram_bytes,
            "available_bytes": hw.ram_bytes - ram_breakdown["required_bytes"],
            "stack_bytes": ram_breakdown["stack_bytes"],
            "heap_bytes": ram_breakdown["heap_bytes"],
            "tensor_arena_bytes": ram_breakdown["tensor_arena_bytes"],
            "note": "Estimated — actual heap usage depends on runtime and SDK." if ram_breakdown["used_percentage"] > 60 else None,
        },
        "model_size_bytes": exp.model_size_bytes,
    }


@router.post("/compatibility-matrix")
async def compatibility_matrix(
    experiment_ids: list[str],
    session: AsyncSession = Depends(get_session),
):
    """Check multiple experiments against all hardware profiles."""
    # Get all hardware profiles
    hw_result = await session.execute(select(HardwareProfile))
    profiles = hw_result.scalars().all()

    # Get experiments
    exp_result = await session.execute(
        select(Experiment).where(Experiment.id.in_(experiment_ids))
    )
    experiments = exp_result.scalars().all()

    matrix = {}
    for exp in experiments:
        matrix[exp.id] = {"name": exp.name, "algorithm": exp.algorithm, "targets": {}}
        for hw in profiles:
            firmware_overhead = 100 * 1024
            available_flash = hw.flash_bytes - firmware_overhead
            available_ram = hw.ram_bytes - 32 * 1024
            estimated_ram = int(exp.model_size_bytes * 0.3 + 4096)

            fits = exp.model_size_bytes <= available_flash and estimated_ram <= available_ram
            matrix[exp.id]["targets"][hw.name] = {
                "compatible": fits,
                "flash_usage_percent": round(exp.model_size_bytes / hw.flash_bytes * 100, 1),
                "ram_usage_percent": round(estimated_ram / hw.ram_bytes * 100, 1),
            }

    return {"matrix": matrix, "hardware": [p.name for p in profiles]}


def _format_bytes(b: int) -> str:
    if b >= 1024 * 1024:
        return f"{b / (1024*1024):.2f} MB"
    elif b >= 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b} B"
