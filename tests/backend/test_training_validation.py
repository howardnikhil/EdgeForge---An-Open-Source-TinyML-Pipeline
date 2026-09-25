"""Tests for EdgeForge Training Validation Architecture & Target Type Detection."""
import os
import sys
import io
import uuid
import pytest
import pandas as pd
from httpx import AsyncClient, ASGITransport

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
from core.database import init_db
from core.ml_validation import inspect_dataset_target, validate_task_compatibility


@pytest.fixture(scope="module")
def anyio_backend():
    return 'asyncio'


@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()


@pytest.mark.anyio
async def test_dataset_target_detection_categorical():
    """Test 7: Dataset with classes idle, wave, shake -> classification detected correctly."""
    df = pd.DataFrame({
        "acc_x": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        "acc_y": [1.1, 1.2, 1.3, 1.4, 1.5, 1.6],
        "label": ["idle", "wave", "shake", "idle", "wave", "shake"]
    })
    info = inspect_dataset_target(df)
    assert info["target_column"] == "label"
    assert info["target_type"] == "categorical"
    assert info["task_suggestion"] == "classification"
    assert set(info["classes"]) == {"idle", "wave", "shake"}


@pytest.mark.anyio
async def test_dataset_target_detection_numeric_continuous():
    """Test target detection for continuous numeric values."""
    df = pd.DataFrame({
        "time": range(30),
        "temperature": [20.0 + i * 0.5 for i in range(30)]
    })
    info = inspect_dataset_target(df, target_column="temperature")
    assert info["target_type"] == "numeric continuous"
    assert info["task_suggestion"] == "regression"


@pytest.mark.anyio
async def test_categorical_target_classification_and_regression_api():
    """Tests 1, 2, 8:
    - Categorical target + Classification -> succeeds
    - Categorical target + Regression -> HTTP 422 (NEVER HTTP 500)
    - Random Forest classification on idle, wave, shake -> model training succeeds
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Create project
        proj_res = await client.post("/api/v1/projects", json={
            "name": f"Validation Test Proj {uuid.uuid4().hex[:6]}",
            "project_type": "sensor"
        })
        assert proj_res.status_code in (200, 201)
        project_id = proj_res.json()["id"]

        # Upload categorical CSV (idle, wave, shake)
        csv_content = (
            "acc_x,acc_y,acc_z,label\n"
            "0.1,0.2,0.3,idle\n"
            "0.2,0.1,0.4,idle\n"
            "0.3,0.3,0.2,idle\n"
            "1.1,1.2,1.3,wave\n"
            "1.2,1.1,1.4,wave\n"
            "1.3,1.3,1.2,wave\n"
            "2.1,2.2,2.3,shake\n"
            "2.2,2.1,2.4,shake\n"
            "2.3,2.3,2.2,shake\n"
            "0.15,0.25,0.35,idle\n"
            "1.15,1.25,1.35,wave\n"
            "2.15,2.25,2.35,shake\n"
            "0.18,0.28,0.38,idle\n"
            "1.18,1.28,1.38,wave\n"
            "2.18,2.28,2.38,shake\n"
        )
        files = {"file": ("gesture.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        data = {"project_id": project_id, "name": "gesture_dataset", "dataset_type": "timeseries"}
        import_res = await client.post("/api/v1/datasets/import-csv", data=data, files=files)
        assert import_res.status_code in (200, 201)
        dataset_id = import_res.json()["id"]

        # Test 2: Categorical target + Regression -> HTTP 422 (never HTTP 500)
        reg_res = await client.post("/api/v1/training/train", json={
            "project_id": project_id,
            "dataset_id": dataset_id,
            "algorithm": "random_forest",
            "task_type": "regression",
            "seed": 42
        })
        assert reg_res.status_code == 422
        err_data = reg_res.json()["detail"]
        assert err_data["error"] == "TASK_DATA_MISMATCH"
        assert "Regression" in err_data["message"]
        assert err_data["details"]["suggested_task"] == "classification"

        # Test 1 & 8: Categorical target + Classification (Random Forest) -> succeeds
        clf_res = await client.post("/api/v1/training/train", json={
            "project_id": project_id,
            "dataset_id": dataset_id,
            "algorithm": "random_forest",
            "task_type": "classification",
            "seed": 42
        })
        if clf_res.status_code != 200:
            print("CLF_RES ERROR:", clf_res.json())
        assert clf_res.status_code == 200
        clf_data = clf_res.json()
        assert clf_data["status"] == "completed"
        assert "accuracy" in clf_data["metrics"]
        assert clf_data["metrics"]["accuracy"] > 0


@pytest.mark.anyio
async def test_numeric_target_regression_and_classification_api():
    """Tests 3, 4:
    - Numeric continuous target + Regression -> succeeds
    - Numeric continuous target + Classification -> validation HTTP 422
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        proj_res = await client.post("/api/v1/projects", json={
            "name": f"Regression Test Proj {uuid.uuid4().hex[:6]}",
            "project_type": "sensor"
        })
        project_id = proj_res.json()["id"]

        # Create numeric dataset
        rows = ["feature1,feature2,target\n"]
        for i in range(30):
            rows.append(f"{i * 0.1},{i * 0.2},{10.0 + i * 1.5}\n")
        csv_content = "".join(rows)

        files = {"file": ("numeric.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        data = {"project_id": project_id, "name": "numeric_dataset", "dataset_type": "timeseries"}
        import_res = await client.post("/api/v1/datasets/import-csv", data=data, files=files)
        dataset_id = import_res.json()["id"]

        # Test 3: Numeric continuous target + Regression -> succeeds
        reg_res = await client.post("/api/v1/training/train", json={
            "project_id": project_id,
            "dataset_id": dataset_id,
            "algorithm": "linear_regression",
            "task_type": "regression",
            "seed": 42
        })
        assert reg_res.status_code == 200
        reg_data = reg_res.json()
        assert reg_data["status"] == "completed"
        assert "r2" in reg_data["metrics"]

        # Test 4: Numeric continuous target + Classification -> HTTP 422
        clf_res = await client.post("/api/v1/training/train", json={
            "project_id": project_id,
            "dataset_id": dataset_id,
            "algorithm": "random_forest",
            "task_type": "classification",
            "seed": 42
        })
        assert clf_res.status_code == 422
        assert clf_res.json()["detail"]["error"] == "TASK_DATA_MISMATCH"


@pytest.mark.anyio
async def test_automl_task_selection():
    """Tests 5, 6:
    - AutoML + categorical target -> classification algorithms selected & evaluated
    - AutoML + numeric continuous target -> regression algorithms selected & evaluated
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        proj_res = await client.post("/api/v1/projects", json={
            "name": f"AutoML Validation Proj {uuid.uuid4().hex[:6]}",
            "project_type": "sensor"
        })
        project_id = proj_res.json()["id"]

        # Categorical dataset
        cat_csv = (
            "x,y,label\n"
            "1,2,idle\n2,3,idle\n3,4,idle\n"
            "10,20,wave\n11,21,wave\n12,22,wave\n"
            "100,200,shake\n101,201,shake\n102,202,shake\n"
            "1,3,idle\n10,21,wave\n100,201,shake\n"
            "2,2,idle\n11,20,wave\n101,200,shake\n"
        )
        files = {"file": ("cat.csv", io.BytesIO(cat_csv.encode("utf-8")), "text/csv")}
        data = {"project_id": project_id, "name": "cat_dataset"}
        imp1 = await client.post("/api/v1/datasets/import-csv", data=data, files=files)
        cat_ds_id = imp1.json()["id"]

        # Test 5: AutoML on categorical dataset (even if task_type='regression' is sent in request)
        automl_cat = await client.post("/api/v1/training/automl", json={
            "project_id": project_id,
            "dataset_id": cat_ds_id,
            "task_type": "regression",  # Requested regression on categorical data
            "target_column": "label",
            "max_models": 4
        })
        assert automl_cat.status_code == 200
        cat_data = automl_cat.json()
        assert cat_data["summary"]["dataset_analysis"]["detected_task"] == "classification"
        assert cat_data["summary"]["completed"] > 0
        assert "best_accuracy" in cat_data["summary"]

        # Numeric dataset
        num_csv = "x,y,target\n" + "".join([f"{i},{i*2},{10.0 + i*0.5}\n" for i in range(25)])
        files2 = {"file": ("num.csv", io.BytesIO(num_csv.encode("utf-8")), "text/csv")}
        data2 = {"project_id": project_id, "name": "num_dataset"}
        imp2 = await client.post("/api/v1/datasets/import-csv", data=data2, files=files2)
        num_ds_id = imp2.json()["id"]

        # Test 6: AutoML on numeric continuous dataset
        automl_num = await client.post("/api/v1/training/automl", json={
            "project_id": project_id,
            "dataset_id": num_ds_id,
            "task_type": "regression",
            "target_column": "target",
            "max_models": 4
        })
        assert automl_num.status_code == 200
        num_data = automl_num.json()
        assert num_data["summary"]["dataset_analysis"]["detected_task"] == "regression"
        assert num_data["summary"]["completed"] > 0
        assert "best_r2" in num_data["summary"]
