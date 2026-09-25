"""Emulation and Sensor Replay API for EdgeForge."""
import os
import pickle
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from models.db_models import Project, Experiment, HardwareProfile, Dataset, Job
from core.emulation.emulator import MCUEmulator

router = APIRouter()


class RunEmulationRequest(BaseModel):
    project_id: str
    experiment_id: str
    dataset_id: str
    hardware_id: str
    emulator_type: str = "native"  # native, renode, qemu
    max_samples: int = 100


@router.post("/run")
async def run_emulation(req: RunEmulationRequest, session: AsyncSession = Depends(get_session)):
    """Run real MCU firmware emulation and replay sensor dataset samples."""
    # 1. Load entities
    exp_res = await session.execute(select(Experiment).where(Experiment.id == req.experiment_id))
    exp = exp_res.scalar_one_or_none()
    if not exp:
        raise HTTPException(404, "Experiment not found")

    proj_res = await session.execute(select(Project).where(Project.id == req.project_id))
    project = proj_res.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    ds_res = await session.execute(select(Dataset).where(Dataset.id == req.dataset_id))
    dataset = ds_res.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    hw_res = await session.execute(select(HardwareProfile).where(HardwareProfile.id == req.hardware_id))
    hw = hw_res.scalar_one_or_none()
    if not hw:
        raise HTTPException(404, "Hardware profile not found")

    # 2. Check firmware ELF binary
    fw_dir = os.path.join(project.path, "firmware", f"{exp.name}_{hw.name.lower().replace(' ', '_').replace('-', '_')}")
    elf_path = os.path.join(fw_dir, "firmware.elf")
    
    if not os.path.exists(elf_path):
        # Look in PlatformIO build folder
        pio_elf = None
        for root, _, files in os.walk(os.path.join(fw_dir, ".pio", "build")):
            for f in files:
                if f.endswith(".elf") or f == "program":
                    pio_elf = os.path.join(root, f)
                    break
        if pio_elf and os.path.exists(pio_elf):
            elf_path = pio_elf

    if not os.path.exists(elf_path):
        raise HTTPException(400, "Firmware binary not found. Compile firmware first using /firmware/compile endpoint.")

    # 3. Load dataset CSV
    if not os.path.exists(dataset.path):
        raise HTTPException(404, "Dataset CSV file not found")

    df = pd.read_csv(dataset.path)
    # Remove label column if present
    feature_cols = [c for c in df.columns if c.lower() not in ("label", "target", "class")]
    X_samples = df[feature_cols].values[:req.max_samples].tolist()

    # 4. Execute MCU Emulation with Sensor Replay
    emulator = MCUEmulator(binary_path=elf_path, emulator_type=req.emulator_type)
    result = emulator.run_sensor_replay(X_samples)

    return {
        "project_id": req.project_id,
        "experiment_id": req.experiment_id,
        "hardware_id": req.hardware_id,
        "emulation_result": result,
    }
