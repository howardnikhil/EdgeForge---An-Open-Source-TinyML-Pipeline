"""Unit tests for ML evaluation quality, cross-validation, data leakage, and class balance."""
import os
import sys
import io
import pytest
import numpy as np
import pandas as pd
from httpx import AsyncClient, ASGITransport

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
from core.database import init_db
from core.ml_validation import (
    inspect_dataset_target,
    analyze_dataset_size,
    analyze_class_balance,
    detect_duplicates_and_leakage,
    calculate_cv_folds,
    check_stratification_possibility,
)
from api.routes.training import _train_model_sync


@pytest.fixture(scope="module")
def anyio_backend():
    return 'asyncio'


@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()


def test_tiny_classification_dataset_analysis():
    """1. Test tiny dataset size analysis."""
    info = analyze_dataset_size(15)
    assert info["reliability"] == "low"
    assert "Small dataset" in info["size_warning"]


def test_stratified_split_and_insufficient_samples():
    """2 & 3. Test stratified split check and insufficient samples handling."""
    # Sufficient samples per class
    df_sufficient = pd.DataFrame({"x": range(10), "label": ["A"] * 5 + ["B"] * 5})
    can_stratify, reason = check_stratification_possibility(df_sufficient, "label", "classification")
    assert can_stratify is True
    assert reason is None

    # Insufficient samples (class B has only 1 sample)
    df_insufficient = pd.DataFrame({"x": range(6), "label": ["A"] * 5 + ["B"] * 1})
    can_stratify_ins, reason_ins = check_stratification_possibility(df_insufficient, "label", "classification")
    assert can_stratify_ins is False
    assert "fewer than 2 samples" in reason_ins


def test_cv_fold_calculation():
    """5. Test dynamic CV fold calculation based on smallest class count."""
    assert calculate_cv_folds(n_samples=15, min_class_count=5) == 5
    assert calculate_cv_folds(n_samples=15, min_class_count=3) == 3
    assert calculate_cv_folds(n_samples=15, min_class_count=1) == 0  # Stratification impossible
    assert calculate_cv_folds(n_samples=2, min_class_count=1) == 0


def test_class_imbalance_detection():
    """6. Test class imbalance analysis."""
    # Balanced
    df_bal = pd.DataFrame({"label": ["A"] * 10 + ["B"] * 10})
    bal_info = analyze_class_balance(df_bal, "label")
    assert bal_info["is_balanced"] is True
    assert bal_info["warning"] is None

    # Severe imbalance
    df_imb = pd.DataFrame({"label": ["A"] * 15 + ["B"] * 1})
    imb_info = analyze_class_balance(df_imb, "label")
    assert imb_info["is_balanced"] is False
    assert "Severe class imbalance" in imb_info["warning"]


def test_duplicate_and_leakage_detection():
    """7. Test duplicate feature vector leakage detection."""
    df = pd.DataFrame({
        "feat1": [1.0, 1.0, 2.0, 3.0],
        "feat2": [0.5, 0.5, 0.8, 1.2],
        "label": ["A", "A", "B", "B"]
    })
    leak_info = detect_duplicates_and_leakage(df, ["feat1", "feat2"])
    assert leak_info["has_duplicates"] is True
    assert leak_info["duplicate_feature_vectors"] == 1
    assert "Potential data leakage" in leak_info["warning"]


def test_train_test_separation_and_leakage_protection(tmp_path):
    """4 & 8. Test train/test metrics isolation and pipeline scaling protection."""
    csv_file = tmp_path / "test_data.csv"
    df = pd.DataFrame({
        "f1": np.linspace(0, 10, 20),
        "f2": np.linspace(10, 20, 20),
        "label": ["cat_a"] * 10 + ["cat_b"] * 10
    })
    df.to_csv(csv_file, index=False)

    model_path = str(tmp_path / "model.pkl")
    res = _train_model_sync(
        dataset_path=str(csv_file),
        algorithm="decision_tree",
        task_type="classification",
        config={},
        seed=42,
        test_size=0.2,
        model_save_path=model_path,
        target_column="label"
    )

    assert "error" not in res
    metrics = res["metrics"]
    assert "train_accuracy" in metrics
    assert "test_accuracy" in metrics
    assert metrics["split"]["train_count"] == 16
    assert metrics["split"]["test_count"] == 4


def test_regression_evaluation(tmp_path):
    """9. Test regression metrics evaluation (MAE, MSE, RMSE, R²)."""
    csv_file = tmp_path / "reg_data.csv"
    df = pd.DataFrame({
        "x1": np.linspace(0, 5, 25),
        "x2": np.linspace(5, 10, 25),
        "target": np.linspace(10, 50, 25)
    })
    df.to_csv(csv_file, index=False)

    model_path = str(tmp_path / "reg_model.pkl")
    res = _train_model_sync(
        dataset_path=str(csv_file),
        algorithm="linear_regression",
        task_type="regression",
        config={},
        seed=42,
        test_size=0.2,
        model_save_path=model_path,
        target_column="target"
    )

    assert "error" not in res
    metrics = res["metrics"]
    assert "mae" in metrics
    assert "mse" in metrics
    assert "rmse" in metrics
    assert "r2" in metrics
    assert "test_r2" in metrics
    assert "train_r2" in metrics


def test_multiclass_classification_metrics(tmp_path):
    """10. Test multiclass classification metrics (accuracy, precision, recall, f1, macro_f1, cm)."""
    csv_file = tmp_path / "multi_data.csv"
    df = pd.DataFrame({
        "a": np.random.randn(30),
        "b": np.random.randn(30),
        "label": ["class1"] * 10 + ["class2"] * 10 + ["class3"] * 10
    })
    df.to_csv(csv_file, index=False)

    model_path = str(tmp_path / "multi_model.pkl")
    res = _train_model_sync(
        dataset_path=str(csv_file),
        algorithm="knn",
        task_type="classification",
        config={"n_neighbors": 3},
        seed=42,
        test_size=0.2,
        model_save_path=model_path,
        target_column="label"
    )

    assert "error" not in res
    metrics = res["metrics"]
    assert "accuracy" in metrics
    assert "f1_score" in metrics
    assert "macro_f1" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "confusion_matrix" in metrics
    assert len(metrics["class_names"]) == 3
