"""Desktop vs MCU Validation API for EdgeForge."""
import os
import pickle
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from models.db_models import Project, Experiment, HardwareProfile, Dataset
from core.emulation.emulator import MCUEmulator
from core.validation.validator import validate_desktop_vs_mcu

router = APIRouter()


class ValidateRequest(BaseModel):
    project_id: str
    experiment_id: str
    dataset_id: str
    hardware_id: str
    max_samples: int = 100


@router.post("/run")
async def run_validation(req: ValidateRequest, session: AsyncSession = Depends(get_session)):
    """Run full Desktop vs Emulated MCU validation pipeline."""
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

    # 2. Load Python model
    if not exp.model_path or not os.path.exists(exp.model_path):
        raise HTTPException(404, "Desktop python model file not found")

    with open(exp.model_path, "rb") as f:
        model_payload = pickle.load(f)
    desktop_model = model_payload["model"]

    # 3. Load Dataset
    if not os.path.exists(dataset.path):
        raise HTTPException(404, "Dataset CSV file not found")

    df = pd.read_csv(dataset.path)
    label_col = next((c for c in df.columns if c.lower() in ("label", "target", "class")), None)
    feature_cols = [c for c in df.columns if c != label_col]

    X_test = df[feature_cols].values[:req.max_samples]
    
    if label_col:
        # Encode labels
        raw_y = df[label_col].values[:req.max_samples]
        classes = dataset.class_labels or list(np.unique(raw_y))
        class_map = {lbl: i for i, lbl in enumerate(classes)}
        y_test = np.array([class_map.get(v, 0) for v in raw_y])
    else:
        y_test = np.zeros(len(X_test), dtype=int)
        classes = ["class_0", "class_1"]

    # 4. Find compiled MCU ELF binary
    fw_dir = os.path.join(project.path, "firmware", f"{exp.name}_{hw.name.lower().replace(' ', '_').replace('-', '_')}")
    elf_path = os.path.join(fw_dir, "firmware.elf")
    
    if not os.path.exists(elf_path):
        for root, _, files in os.walk(os.path.join(fw_dir, ".pio", "build")):
            for f in files:
                if f.endswith(".elf") or f == "program":
                    elf_path = os.path.join(root, f)
                    break

    if not os.path.exists(elf_path):
        raise HTTPException(400, "Firmware binary not found. Compile firmware first.")

    # 5. Execute MCU Sensor Replay Emulation
    emulator = MCUEmulator(binary_path=elf_path, emulator_type="native")
    emulation_res = emulator.run_sensor_replay(X_test.tolist())

    if not emulation_res["success"] and not emulation_res["telemetry"]:
        raise HTTPException(500, f"MCU Emulation failed: {emulation_res.get('error', 'No telemetry captured')}")

    # 6. Compare Desktop vs MCU
    validation_report = validate_desktop_vs_mcu(
        desktop_model=desktop_model,
        X_test=X_test,
        y_test=y_test,
        mcu_telemetry=emulation_res["telemetry"],
        class_labels=classes
    )

    return {
        "project_id": req.project_id,
        "experiment_id": req.experiment_id,
        "hardware_id": req.hardware_id,
        "validation_report": validation_report,
        "emulation_summary": {
            "samples_processed": emulation_res["samples_processed"],
            "avg_latency_us": emulation_res["avg_latency_us"],
            "duration_s": emulation_res["duration_s"]
        }
    }
