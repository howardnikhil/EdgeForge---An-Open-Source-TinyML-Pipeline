"""Comprehensive integration tests for EdgeForge FastAPI backend."""
import os
import sys
import io
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

# Add apps/backend to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
from core.database import init_db

@pytest.fixture(scope="module")
def anyio_backend():
    return 'asyncio'

@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()


@pytest.mark.anyio
async def test_system_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/system/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["name"] == "HowNik's EdgeForge"


@pytest.mark.anyio
async def test_system_environment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/system/environment")
        assert response.status_code == 200
        data = response.json()
        assert "os" in data
        assert "python" in data
        assert "ml_frameworks" in data


@pytest.mark.anyio
async def test_system_capabilities():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/system/capabilities")
        assert response.status_code == 200
        data = response.json()
        assert data["serial_collection"] is True
        assert data["dataset_management"] is True


@pytest.mark.anyio
async def test_project_crud():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        uid = uuid.uuid4().hex[:8]
        proj_name = f"Test Edge Project {uid}"
        # Create project
        create_res = await client.post("/api/v1/projects", json={
            "name": proj_name,
            "description": "A project for automated testing",
            "project_type": "sensor"
        })
        assert create_res.status_code in (200, 201)
        project = create_res.json()
        project_id = project["id"]
        assert project["name"] == proj_name
        assert os.path.exists(project["path"])

        # List projects
        list_res = await client.get("/api/v1/projects")
        assert list_res.status_code == 200
        projects = list_res.json()
        assert any(p["id"] == project_id for p in projects)

        # Get project
        get_res = await client.get(f"/api/v1/projects/{project_id}")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["id"] == project_id
        assert "files" in get_data

        # Update project
        patch_res = await client.patch(f"/api/v1/projects/{project_id}", json={
            "description": "Updated description"
        })
        assert patch_res.status_code == 200
        assert patch_res.json()["description"] == "Updated description"

        # Delete project
        del_res = await client.delete(f"/api/v1/projects/{project_id}?delete_files=true")
        assert del_res.status_code == 200
        assert del_res.json()["deleted"] is True


@pytest.mark.anyio
async def test_hardware_profiles():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/api/v1/hardware/profiles")
        assert res.status_code == 200
        profiles = res.json()
        assert len(profiles) > 0
        esp32 = next((p for p in profiles if "ESP32" in p["name"]), None)
        assert esp32 is not None


@pytest.mark.anyio
async def test_end_to_end_ml_and_firmware_pipeline():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        uid = uuid.uuid4().hex[:8]
        proj_name = f"Pipeline Test {uid}"
        # 1. Create project
        proj_res = await client.post("/api/v1/projects", json={
            "name": proj_name,
            "project_type": "sensor"
        })
        assert proj_res.status_code in (200, 201)
        proj_id = proj_res.json()["id"]

        # 2. Import CSV Dataset
        csv_data = "acc_x,acc_y,acc_z,label\n"
        for i in range(30):
            csv_data += f"{0.1*i},{0.2*i},{0.3*i},idle\n"
        for i in range(30):
            csv_data += f"{1.0+0.5*i},{2.0+0.5*i},{3.0+0.5*i},motion\n"

        files = {"file": ("sensor.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
        data_form = {"project_id": proj_id, "name": "Sensor Dataset", "dataset_type": "timeseries"}

        ds_res = await client.post("/api/v1/datasets/import-csv", data=data_form, files=files)
        assert ds_res.status_code == 200
        ds_data = ds_res.json()
        dataset_id = ds_data["id"]
        assert ds_data["num_samples"] == 60
        assert ds_data["num_classes"] == 2

        # 3. Train Model
        train_res = await client.post("/api/v1/training/train", json={
            "project_id": proj_id,
            "dataset_id": dataset_id,
            "algorithm": "random_forest",
            "config": {"n_estimators": 5, "max_depth": 3},
            "task_type": "classification"
        })
        assert train_res.status_code == 200
        train_data = train_res.json()
        exp_id = train_data["experiment_id"]
        assert train_data["status"] == "completed"
        assert train_data["metrics"]["accuracy"] > 0.8

        # 4. Export ONNX
        onnx_res = await client.post(f"/api/v1/models/export-onnx?experiment_id={exp_id}")
        assert onnx_res.status_code == 200
        assert "size_bytes" in onnx_res.json()

        # 5. Export C Array
        c_res = await client.post(f"/api/v1/models/export-c-array?experiment_id={exp_id}")
        assert c_res.status_code == 200
        assert "size_bytes" in c_res.json()

        # 6. Check Hardware Compatibility
        hw_res = await client.get("/api/v1/hardware/profiles")
        profiles = hw_res.json()
        hw_id = profiles[0]["id"]

        compat_res = await client.post(f"/api/v1/hardware/compatibility?experiment_id={exp_id}&hardware_id={hw_id}")
        assert compat_res.status_code == 200
        assert compat_res.json()["compatible"] is True

        # 7. Generate Firmware Code
        gen_res = await client.post("/api/v1/firmware/generate", json={
            "project_id": proj_id,
            "experiment_id": exp_id,
            "hardware_id": hw_id,
            "deployment_format": "platformio"
        })
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assert "src/main.cpp" in gen_data["files"]
        assert "platformio.ini" in gen_data["files"]
        main_cpp_path = os.path.join(gen_data["firmware_path"], "src", "main.cpp")
        assert os.path.exists(main_cpp_path)

        with open(main_cpp_path, "r") as f:
            content = f.read()
            assert "void setup()" in content

        # 8. Clean up
        await client.delete(f"/api/v1/projects/{proj_id}?delete_files=true")


@pytest.mark.anyio
async def test_settings_api():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Update setting
        put_res = await client.put("/api/v1/settings", json={
            "key": "test_key",
            "value": "test_val",
            "category": "general"
        })
        assert put_res.status_code == 200

        # List settings
        get_res = await client.get("/api/v1/settings")
        assert get_res.status_code == 200
        settings = get_res.json()
        assert any(s["key"] == "test_key" for s in settings)
