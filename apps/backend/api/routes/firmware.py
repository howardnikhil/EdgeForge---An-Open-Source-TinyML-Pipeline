"""Firmware generation and real compilation API for EdgeForge."""
import os
import pickle
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from models.db_models import Experiment, HardwareProfile, Project
from core.firmware.c_generator import generate_embedded_firmware_project
from core.firmware.compiler import compile_firmware

router = APIRouter()


class FirmwareGenerateRequest(BaseModel):
    project_id: str
    experiment_id: str
    hardware_id: str
    deployment_format: str = "platformio"  # platformio, arduino


class FirmwareCompileRequest(BaseModel):
    project_id: str
    experiment_id: str
    hardware_id: str


@router.post("/generate")
async def generate_firmware(req: FirmwareGenerateRequest, session: AsyncSession = Depends(get_session)):
    """Generate MCU-executable C/C++ firmware source code."""
    # Load entities
    proj_r = await session.execute(select(Project).where(Project.id == req.project_id))
    project = proj_r.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    exp_r = await session.execute(select(Experiment).where(Experiment.id == req.experiment_id))
    exp = exp_r.scalar_one_or_none()
    if not exp:
        raise HTTPException(404, "Experiment not found")

    hw_r = await session.execute(select(HardwareProfile).where(HardwareProfile.id == req.hardware_id))
    hw = hw_r.scalar_one_or_none()
    if not hw:
        raise HTTPException(404, "Hardware profile not found")

    # Load Python model
    model_obj = None
    if exp.model_path and os.path.exists(exp.model_path):
        with open(exp.model_path, "rb") as f:
            model_obj = pickle.load(f).get("model")

    fw_dir = os.path.join(project.path, "firmware", f"{exp.name}_{hw.name.lower().replace(' ', '_').replace('-', '_')}")
    
    n_features = exp.input_shape[0] if exp.input_shape else 4
    class_labels = exp.reproducibility.get("class_labels", ["class_0", "class_1"])

    target_board_map = {
        "ESP32": "esp32",
        "ESP32-S3": "esp32",
        "RP2040": "rp2040",
    }
    board_key = target_board_map.get(hw.name, "native")

    res = generate_embedded_firmware_project(
        output_dir=fw_dir,
        model=model_obj,
        algorithm=exp.algorithm,
        n_features=n_features,
        class_labels=class_labels,
        target_board=board_key,
    )

    generated_files = []
    for root, dirs, files in os.walk(fw_dir):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), fw_dir)
            generated_files.append(rel)

    return {
        "firmware_path": fw_dir,
        "deployment_format": req.deployment_format,
        "hardware": hw.name,
        "files": generated_files,
        "build_command": f"cd {fw_dir} && pio run",
    }


@router.post("/compile")
async def compile_firmware_endpoint(req: FirmwareCompileRequest, session: AsyncSession = Depends(get_session)):
    """Perform real firmware compilation using PlatformIO or GCC toolchain."""
    proj_r = await session.execute(select(Project).where(Project.id == req.project_id))
    project = proj_r.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    exp_r = await session.execute(select(Experiment).where(Experiment.id == req.experiment_id))
    exp = exp_r.scalar_one_or_none()
    if not exp:
        raise HTTPException(404, "Experiment not found")

    hw_r = await session.execute(select(HardwareProfile).where(HardwareProfile.id == req.hardware_id))
    hw = hw_r.scalar_one_or_none()
    if not hw:
        raise HTTPException(404, "Hardware profile not found")

    fw_dir = os.path.join(project.path, "firmware", f"{exp.name}_{hw.name.lower().replace(' ', '_').replace('-', '_')}")
    
    if not os.path.exists(fw_dir):
        raise HTTPException(400, "Firmware files not generated yet. Call /firmware/generate first.")

    build_result = compile_firmware(firmware_dir=fw_dir)

    return {
        "project_id": req.project_id,
        "experiment_id": req.experiment_id,
        "hardware": hw.name,
        "firmware_path": fw_dir,
        "compilation_result": build_result,
    }


@router.get("/build-log")
async def get_build_log(firmware_path: str):
    """Retrieve build logs for a compiled firmware project."""
    log_path = os.path.join(firmware_path, "build.log")
    if not os.path.exists(log_path):
        raise HTTPException(404, "Build log file not found")

    with open(log_path, "r") as f:
        content = f.read()

    return {"firmware_path": firmware_path, "build_log": content}
