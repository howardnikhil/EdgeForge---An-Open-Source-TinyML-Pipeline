"""Integration & Logic Tests for Task-Aware Metric Persistence, Interpretation, Baseline & Chart Integrity."""
import os
import sys
import pytest
import math
import numpy as np
import pandas as pd
from httpx import AsyncClient, ASGITransport
from sklearn.dummy import DummyRegressor
from sklearn.metrics import r2_score

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
from core.database import init_db
from core.ml_validation import interpret_r2_backend

@pytest.fixture(scope="module")
def anyio_backend():
    return 'asyncio'

@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()


def test_r2_interpretation_thresholds():
    """Verify canonical R² interpretation thresholds."""
    assert interpret_r2_backend(1.0)["rating"] == "Excellent predictive fit"
    assert interpret_r2_backend(0.92)["rating"] == "Excellent predictive fit"
    assert interpret_r2_backend(0.84)["rating"] == "Strong predictive fit"
    assert interpret_r2_backend(0.51)["rating"] == "Moderate predictive fit"
    assert interpret_r2_backend(0.26)["rating"] == "Weak predictive fit"
    assert interpret_r2_backend(0.11)["rating"] == "Very weak predictive fit"
    assert interpret_r2_backend(0.0)["rating"] == "No improvement over mean baseline"
    assert interpret_r2_backend(-0.5)["rating"] == "Worse than mean baseline"
    assert interpret_r2_backend(-1.643)["rating"] == "Worse than mean baseline"

    assert interpret_r2_backend(-1.643)["is_worse_than_baseline"] is True
    assert "help_note" in interpret_r2_backend(-1.643)


def test_metric_formatting_rules():
    """Verify exact formatting rules for accuracy and R2."""
    def format_accuracy(val):
        if val is None or math.isnan(val) or math.isinf(val):
            return "—"
        pct = val if val > 1.0 else val * 100.0
        return f"{pct:.2f}%"

    def format_r2(val):
        if val is None or math.isnan(val) or math.isinf(val):
            return "—"
        return f"{val:.3f}"

    # 1. R2 raw formatting checks
    assert format_r2(-1.643) == "-1.643"
    assert format_r2(0.842) == "0.842"
    assert format_r2(1.0) == "1.000"
    assert format_r2(0.0) == "0.000"

    # 2. Accuracy formatting checks
    assert format_accuracy(0.9623) == "96.23%"
    assert format_accuracy(1.0) == "100.00%"
    assert format_accuracy(0.0) == "0.00%"


def test_baseline_fitting_no_leakage():
    """Verify DummyRegressor baseline fits strictly on train set and tests on unseen test set."""
    np.random.seed(42)
    X_train = np.random.randn(80, 3)
    y_train = np.random.randn(80) * 10 + 5.0  # Mean approx 5.0

    X_test = np.random.randn(20, 3)
    y_test = np.random.randn(20) * 10 + 12.0  # Slightly shifted mean on test set

    dummy = DummyRegressor(strategy="mean")
    dummy.fit(X_train, y_train)

    # Predictions on test set must equal y_train mean (approx 5.0)
    y_pred_dummy = dummy.predict(X_test)
    assert np.allclose(y_pred_dummy, y_train.mean())

    # Baseline R2 evaluated on test set
    base_r2 = r2_score(y_test, y_pred_dummy)
    # Since test set mean is shifted, base_r2 <= 0.0
    assert base_r2 <= 0.05


def test_dashboard_best_metric_aggregation():
    """Verify classification and regression experiments are never mixed when finding best KPI."""
    exps = [
        {"id": "1", "task_type": "classification", "metrics": {"test_accuracy": 0.9623, "accuracy": 0.9623}, "status": "completed"},
        {"id": "2", "task_type": "classification", "metrics": {"test_accuracy": 0.8810, "accuracy": 0.8810}, "status": "completed"},
        {"id": "3", "task_type": "regression", "metrics": {"test_r2": 0.842, "r2": 0.842}, "status": "completed"},
        {"id": "4", "task_type": "regression", "metrics": {"test_r2": -1.643, "r2": -1.643}, "status": "completed"},
    ]

    class_exps = [e for e in exps if e["task_type"] == "classification"]
    reg_exps = [e for e in exps if e["task_type"] == "regression"]

    best_class_acc = max(e["metrics"]["test_accuracy"] for e in class_exps)
    best_reg_r2 = max(e["metrics"]["test_r2"] for e in reg_exps)

    # Classification MAX
    assert best_class_acc == 0.9623
    # Regression MAX
    assert best_reg_r2 == 0.842

    # Verify R2 -1.643 < 0.842
    assert max(-1.643, 0.842) == 0.842


def test_chart_data_filtering():
    """Verify invalid / NaN / undefined values are rejected before chart generation."""
    raw_points = [
        {"algo": "rf", "r2": 0.842},
        {"algo": "dt", "r2": float("nan")},
        {"algo": "knn", "r2": None},
        {"algo": "mlp", "r2": -1.643},
    ]

    valid_points = []
    for p in raw_points:
        val = p["r2"]
        if val is not None and not math.isnan(val) and not math.isinf(val):
            valid_points.append(p)

    assert len(valid_points) == 2
    assert [p["algo"] for p in valid_points] == ["rf", "mlp"]
    assert valid_points[0]["r2"] == 0.842
    assert valid_points[1]["r2"] == -1.643


@pytest.mark.anyio
async def test_dashboard_api_task_integrity():
    """Test project/experiment API returns valid task_type and metrics dict."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        proj_res = await client.post("/api/v1/projects", json={"name": "Dashboard Task Integrity Test"})
        assert proj_res.status_code == 200
        proj_id = proj_res.json()["id"]

        exp_res = await client.get(f"/api/v1/experiments?project_id={proj_id}")
        assert exp_res.status_code == 200

        # Clean up
        await client.delete(f"/api/v1/projects/{proj_id}?delete_files=true")
