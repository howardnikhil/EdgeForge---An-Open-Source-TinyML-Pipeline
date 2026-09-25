"""Automated Integration Test Suite for Real Embedded Validation Pipeline.

Verifies:
1. Real C/C++ inference code generation for MCU targets.
2. Real firmware compilation (PlatformIO / GCC toolchain).
3. MCU firmware emulation & sensor dataset replay.
4. Telemetry parsing & UART prediction capture.
5. Desktop Python vs Emulated MCU C inference accuracy validation.
6. Detailed Flash & RAM hardware memory breakdown.
"""
import os
import sys
import io
import uuid
import pytest
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from httpx import AsyncClient, ASGITransport

# Add apps/backend & root to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

for p in (backend_dir, root_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from main import app
from core.database import init_db
from core.firmware.c_generator import generate_embedded_firmware_project
from core.firmware.compiler import compile_firmware
from core.emulation.emulator import MCUEmulator
from core.validation.validator import validate_desktop_vs_mcu
from core.hardware.compatibility import analyze_hardware_compatibility


@pytest.fixture(scope="module")
def anyio_backend():
    return 'asyncio'


@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()


@pytest.mark.anyio
async def test_c_code_generation():
    """Verify C inference engine generation for Random Forest."""
    X = np.array([[0.1, 0.2], [0.3, 0.4], [1.5, 2.5], [2.1, 3.2]])
    y = np.array([0, 0, 1, 1])
    
    rf = RandomForestClassifier(n_estimators=3, max_depth=2, random_state=42)
    rf.fit(X, y)
    
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scratch", "c_gen_test"))
    res = generate_embedded_firmware_project(
        output_dir=out_dir,
        model=rf,
        algorithm="random_forest",
        n_features=2,
        class_labels=["class_0", "class_1"],
        target_board="native"
    )
    
    assert res["status"] == "success"
    assert os.path.exists(os.path.join(out_dir, "include", "model_data.h"))
    assert os.path.exists(os.path.join(out_dir, "src", "main.cpp"))
    
    with open(os.path.join(out_dir, "include", "model_data.h"), "r") as f:
        code = f.read()
        assert "predict_sample" in code
        assert "NUM_FEATURES 2" in code


@pytest.mark.anyio
async def test_compilation_and_emulation_pipeline():
    """Verify real firmware compilation, MCU execution, and sensor replay."""
    X = np.array([[0.1, 0.2], [0.2, 0.3], [1.5, 2.5], [2.1, 3.2]])
    y = np.array([0, 0, 1, 1])
    
    rf = RandomForestClassifier(n_estimators=3, max_depth=2, random_state=42)
    rf.fit(X, y)
    
    fw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scratch", "emu_test"))
    generate_embedded_firmware_project(
        output_dir=fw_dir,
        model=rf,
        algorithm="random_forest",
        n_features=2,
        class_labels=["class_0", "class_1"],
        target_board="native"
    )
    
    # 1. Compile firmware binary
    build_res = compile_firmware(firmware_dir=fw_dir)
    assert build_res["success"] is True, f"Compilation failed: {build_res.get('compiler_output')}"
    assert os.path.exists(build_res["elf_path"])
    
    # 2. Run MCU emulation and sensor replay
    emulator = MCUEmulator(binary_path=build_res["elf_path"], emulator_type="native")
    emu_res = emulator.run_sensor_replay(X.tolist())
    
    assert emu_res["success"] is True
    assert len(emu_res["telemetry"]) == 4
    assert emu_res["telemetry"][0]["prediction"] in (0, 1)
    
    # 3. Validate Desktop vs MCU
    val_res = validate_desktop_vs_mcu(
        desktop_model=rf,
        X_test=X,
        y_test=y,
        mcu_telemetry=emu_res["telemetry"],
        class_labels=["class_0", "class_1"]
    )
    
    assert val_res["agreement_rate"] == 100.0
    assert val_res["desktop_accuracy"] == 100.0
    assert val_res["mcu_accuracy"] == 100.0


@pytest.mark.anyio
async def test_hardware_compatibility_breakdown():
    """Verify detailed Flash/RAM memory breakdown."""
    hw_profile = {
        "name": "ESP32",
        "flash_bytes": 4 * 1024 * 1024,
        "ram_bytes": 520 * 1024
    }
    
    report = analyze_hardware_compatibility(
        model_size_bytes=12000,
        n_features=6,
        n_classes=3,
        algorithm="random_forest",
        hardware_profile=hw_profile
    )
    
    assert report["compatible"] is True
    assert "flash" in report["breakdown"]
    assert "ram" in report["breakdown"]
    assert report["breakdown"]["flash"]["sdk_base_bytes"] > 0


@pytest.mark.anyio
async def test_end_to_end_validation_api():
    """Verify API endpoints for compilation, emulation, and validation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        uid = uuid.uuid4().hex[:8]
        proj_name = f"Validation API Test {uid}"
        
        # 1. Create project
        proj_res = await client.post("/api/v1/projects", json={"name": proj_name, "project_type": "sensor"})
        proj_id = proj_res.json()["id"]

        # 2. Import CSV Dataset
        csv_data = "acc_x,acc_y,label\n" + ("0.1,0.2,idle\n" * 10) + ("1.8,2.4,motion\n" * 10)
        files = {"file": ("sensor.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
        data_form = {"project_id": proj_id, "name": "Sensor Dataset", "dataset_type": "timeseries"}

        ds_res = await client.post("/api/v1/datasets/import-csv", data=data_form, files=files)
        dataset_id = ds_res.json()["id"]

        # 3. Train Model
        train_res = await client.post("/api/v1/training/train", json={
            "project_id": proj_id,
            "dataset_id": dataset_id,
            "algorithm": "random_forest",
            "config": {"n_estimators": 3, "max_depth": 2},
            "task_type": "classification"
        })
        exp_id = train_res.json()["experiment_id"]

        # 4. Get Hardware Profile ID
        hw_res = await client.get("/api/v1/hardware/profiles")
        profiles = hw_res.json()
        native_profile = next((p for p in profiles if "native" in p["name"].lower()), profiles[0])
        hw_id = native_profile["id"]

        # 5. Generate Firmware Code
        gen_res = await client.post("/api/v1/firmware/generate", json={
            "project_id": proj_id,
            "experiment_id": exp_id,
            "hardware_id": hw_id,
        })
        assert gen_res.status_code == 200

        # 6. Real Compilation Endpoint
        comp_res = await client.post("/api/v1/firmware/compile", json={
            "project_id": proj_id,
            "experiment_id": exp_id,
            "hardware_id": hw_id,
        })
        assert comp_res.status_code == 200
        assert comp_res.json()["compilation_result"]["success"] is True

        # 7. Run Emulation & Sensor Replay Endpoint
        emu_res = await client.post("/api/v1/emulation/run", json={
            "project_id": proj_id,
            "experiment_id": exp_id,
            "dataset_id": dataset_id,
            "hardware_id": hw_id,
            "emulator_type": "native"
        })
        assert emu_res.status_code == 200
        assert emu_res.json()["emulation_result"]["success"] is True

        # 8. Run Desktop vs MCU Validation Endpoint
        val_res = await client.post("/api/v1/validation/run", json={
            "project_id": proj_id,
            "experiment_id": exp_id,
            "dataset_id": dataset_id,
            "hardware_id": hw_id,
        })
        assert val_res.status_code == 200
        report = val_res.json()["validation_report"]
        assert report["agreement_rate"] == 100.0

        # Clean up
        await client.delete(f"/api/v1/projects/{proj_id}?delete_files=true")
