"""ML Training API with real scikit-learn training."""
import os
import time
import json
import pickle
import traceback
import uuid
import asyncio
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import numpy as np
import pandas as pd

from core.database import get_session
from models.db_models import Project, Dataset, Experiment, Model, Job

from core.ml_validation import (
    inspect_dataset_target, validate_task_compatibility,
    calculate_cv_folds, check_stratification_possibility,
    analyze_dataset_size, analyze_class_balance, detect_duplicates_and_leakage,
    analyze_regression_diagnostics, interpret_r2_backend,
)

router = APIRouter()

_executor = ThreadPoolExecutor(max_workers=4)

class TrainRequest(BaseModel):
    project_id: str
    dataset_id: str
    algorithm: str  # decision_tree, random_forest, svm, knn, gradient_boosting, logistic_regression, mlp
    task_type: str = "classification"  # classification, regression
    target_column: str = "label"
    config: dict = {}  # hyperparameters
    seed: int = 42
    test_size: float = 0.2


class AutoMLRequest(BaseModel):
    project_id: str
    dataset_id: str
    task_type: str = "classification"
    target_column: str = "label"
    max_models: int = 8
    seed: int = 42
    test_size: float = 0.2


ALGORITHM_MAP = {
    "decision_tree": {
        "classification": "sklearn.tree.DecisionTreeClassifier",
        "regression": "sklearn.tree.DecisionTreeRegressor",
    },
    "random_forest": {
        "classification": "sklearn.ensemble.RandomForestClassifier",
        "regression": "sklearn.ensemble.RandomForestRegressor",
    },
    "gradient_boosting": {
        "classification": "sklearn.ensemble.GradientBoostingClassifier",
        "regression": "sklearn.ensemble.GradientBoostingRegressor",
    },
    "svm": {
        "classification": "sklearn.svm.SVC",
        "regression": "sklearn.svm.SVR",
    },
    "knn": {
        "classification": "sklearn.neighbors.KNeighborsClassifier",
        "regression": "sklearn.neighbors.KNeighborsRegressor",
    },
    "logistic_regression": {
        "classification": "sklearn.linear_model.LogisticRegression",
        "regression": None,
    },
    "linear_regression": {
        "classification": None,
        "regression": "sklearn.linear_model.LinearRegression",
    },
    "mlp": {
        "classification": "sklearn.neural_network.MLPClassifier",
        "regression": "sklearn.neural_network.MLPRegressor",
    },
}


def _import_model_class(dotpath: str):
    """Dynamically import a scikit-learn model class."""
    parts = dotpath.rsplit(".", 1)
    mod = __import__(parts[0], fromlist=[parts[1]])
    return getattr(mod, parts[1])


def _train_model_sync(
    dataset_path: str, algorithm: str, task_type: str,
    config: dict, seed: int, test_size: float,
    model_save_path: str, target_column: str = "label",
) -> dict:
    """Synchronous training function with pipeline leakage protection & CV analysis."""
    import sklearn
    from sklearn.model_selection import train_test_split, StratifiedKFold, KFold, cross_val_score
    from sklearn.metrics import (
        accuracy_score, f1_score, precision_score, recall_score,
        mean_squared_error, mean_absolute_error, r2_score, confusion_matrix,
    )
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.pipeline import Pipeline

    start_time = time.time()

    # Load data
    df = pd.read_csv(dataset_path)

    if target_column not in df.columns:
        if "label" in df.columns:
            target_column = "label"
        elif "target" in df.columns:
            target_column = "target"
        elif "class" in df.columns:
            target_column = "class"
        else:
            target_column = df.columns[-1]

    # Separate features and target
    X = df.drop(columns=[target_column])
    y = df[target_column]

    # Safeguard validation: string target for regression
    if task_type == "regression" and (pd.api.types.is_string_dtype(y) or pd.api.types.is_object_dtype(y) or isinstance(y.dtype, pd.CategoricalDtype)):
        return {"error": f"Cannot run Regression task on string/categorical target column '{target_column}'."}

    # Handle non-numeric features
    for col in X.columns:
        if X[col].dtype == object or pd.api.types.is_string_dtype(X[col]) or isinstance(X[col].dtype, pd.CategoricalDtype):
            X[col] = pd.Categorical(X[col]).codes

    # Handle NaN
    X = X.fillna(0)

    # Detect duplicates & leakage
    leakage_info = detect_duplicates_and_leakage(df, list(X.columns))

    # Encode labels for classification
    le = None
    if task_type == "classification":
        if pd.api.types.is_string_dtype(y) or pd.api.types.is_object_dtype(y) or isinstance(y.dtype, pd.CategoricalDtype) or not pd.api.types.is_numeric_dtype(y):
            le = LabelEncoder()
            y = pd.Series(le.fit_transform(y.astype(str)))
        elif (y % 1 == 0).all():
            le = LabelEncoder()
            y = pd.Series(le.fit_transform(y))

    # Check stratification possibility
    can_stratify, stratify_reason = check_stratification_possibility(df, target_column, task_type)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y if (task_type == "classification" and can_stratify) else None
    )

    # Get model class
    dotpath = ALGORITHM_MAP.get(algorithm, {}).get(task_type)
    if not dotpath:
        return {"error": f"Algorithm '{algorithm}' not supported for task '{task_type}'"}

    ModelClass = _import_model_class(dotpath)

    # Build config with defaults
    model_config = {"random_state": seed}
    if algorithm == "svm" and task_type == "classification":
        model_config["probability"] = True
    model_config.update(config)

    # Filter valid params
    import inspect
    valid_params = set(inspect.signature(ModelClass.__init__).parameters.keys())
    model_config = {k: v for k, v in model_config.items() if k in valid_params}

    # Pipeline leakage protection: Fit scaler strictly on X_train
    model_instance = ModelClass(**model_config)
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", model_instance)
    ])

    pipeline.fit(X_train, y_train)

    # Evaluate on Train and Test sets separately
    y_train_pred = pipeline.predict(X_train)
    y_test_pred = pipeline.predict(X_test)

    # Perform Cross-Validation dynamically
    min_c = int(y.value_counts().min()) if task_type == "classification" else len(y)
    cv_folds = calculate_cv_folds(len(y), min_c if task_type == "classification" else None)

    cv_mean = None
    cv_std = None

    if cv_folds >= 2:
        try:
            cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed) if (task_type == "classification" and can_stratify) else KFold(n_splits=cv_folds, shuffle=True, random_state=seed)
            cv_scores = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy" if task_type == "classification" else "r2")
            cv_mean = float(cv_scores.mean())
            cv_std = float(cv_scores.std())
        except Exception:
            pass

    metrics = {}

    if task_type == "classification":
        metrics["accuracy"] = float(accuracy_score(y_test, y_test_pred))
        metrics["test_accuracy"] = float(accuracy_score(y_test, y_test_pred))
        metrics["train_accuracy"] = float(accuracy_score(y_train, y_train_pred))
        metrics["f1_score"] = float(f1_score(y_test, y_test_pred, average="weighted", zero_division=0))
        metrics["macro_f1"] = float(f1_score(y_test, y_test_pred, average="macro", zero_division=0))
        metrics["precision"] = float(precision_score(y_test, y_test_pred, average="weighted", zero_division=0))
        metrics["recall"] = float(recall_score(y_test, y_test_pred, average="weighted", zero_division=0))

        cm = confusion_matrix(y_test, y_test_pred)
        metrics["confusion_matrix"] = cm.tolist()

        if le:
            metrics["class_names"] = [str(c) for c in le.classes_.tolist()]
        else:
            metrics["class_names"] = [str(c) for c in np.unique(y).tolist()]

        if cv_mean is not None:
            metrics["cv_accuracy_mean"] = round(cv_mean, 4)
            metrics["cv_accuracy_std"] = round(cv_std, 4) if cv_std is not None else 0.0
            metrics["cv_folds"] = cv_folds
    else:
        from sklearn.dummy import DummyRegressor
        dummy = DummyRegressor(strategy="mean")
        dummy.fit(X_train, y_train)
        y_test_dummy = dummy.predict(X_test)

        b_r2 = float(r2_score(y_test, y_test_dummy))
        b_mae = float(mean_absolute_error(y_test, y_test_dummy))
        b_mse = float(mean_squared_error(y_test, y_test_dummy))
        b_rmse = float(np.sqrt(b_mse))

        metrics["mae"] = float(mean_absolute_error(y_test, y_test_pred))
        metrics["mse"] = float(mean_squared_error(y_test, y_test_pred))
        metrics["rmse"] = float(np.sqrt(metrics["mse"]))
        metrics["r2"] = float(r2_score(y_test, y_test_pred))
        metrics["test_r2"] = metrics["r2"]
        metrics["train_r2"] = float(r2_score(y_train, y_train_pred))

        metrics["baseline_r2"] = b_r2
        metrics["baseline_mae"] = b_mae
        metrics["baseline_rmse"] = b_rmse
        metrics["baseline"] = {
            "type": "mean",
            "test_r2": b_r2,
            "test_mae": b_mae,
            "test_rmse": b_rmse,
        }
        metrics["r2_interpretation"] = interpret_r2_backend(metrics["r2"])
        metrics["regression_diagnostics"] = analyze_regression_diagnostics(df, target_column, X, y)

        if cv_mean is not None:
            metrics["cv_r2_mean"] = round(cv_mean, 4)
            metrics["cv_r2_std"] = round(cv_std, 4) if cv_std is not None else 0.0
            metrics["cv_folds"] = cv_folds

    metrics["split"] = {
        "train_count": len(X_train),
        "val_count": 0,
        "test_count": len(X_test),
        "total_count": len(df),
        "stratification_applied": can_stratify,
        "stratification_reason": stratify_reason,
    }
    metrics["size_info"] = analyze_dataset_size(len(df))
    metrics["class_balance"] = analyze_class_balance(df, target_column) if task_type == "classification" else None
    metrics["leakage_info"] = leakage_info

    # Save model
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    with open(model_save_path, "wb") as f:
        pickle.dump({"model": pipeline, "label_encoder": le, "feature_names": list(X.columns)}, f)

    model_size = os.path.getsize(model_save_path)
    duration = time.time() - start_time

    return {
        "metrics": metrics,
        "model_size_bytes": model_size,
        "duration_seconds": round(duration, 3),
        "num_train_samples": len(X_train),
        "num_test_samples": len(X_test),
        "feature_names": list(X.columns),
        "input_shape": [X.shape[1]],
        "output_shape": [int(y.nunique())] if task_type == "classification" else [1],
        "framework_version": sklearn.__version__,
    }


@router.post("/train")
async def train_model(req: TrainRequest, session: AsyncSession = Depends(get_session)):
    """Train a single model."""
    # Validate project & dataset
    proj = await session.execute(select(Project).where(Project.id == req.project_id))
    project = proj.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    ds = await session.execute(select(Dataset).where(Dataset.id == req.dataset_id))
    dataset = ds.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    if not os.path.exists(dataset.path):
        raise HTTPException(404, "Dataset file not found on disk")

    # Inspect dataset target & validate task/algorithm compatibility
    try:
        df = pd.read_csv(dataset.path)
        target_info = inspect_dataset_target(df, req.target_column)
        validate_task_compatibility(target_info, req.task_type, req.algorithm, ALGORITHM_MAP)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, detail={
            "error": "DATASET_INSPECTION_ERROR",
            "message": f"Could not inspect dataset file: {str(exc)}",
        })

    # Create experiment record
    exp_name = f"{req.algorithm}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    model_save_path = os.path.join(project.path, "models", f"{exp_name}.pkl")

    experiment = Experiment(
        project_id=req.project_id,
        dataset_id=req.dataset_id,
        name=exp_name,
        algorithm=req.algorithm,
        framework="scikit-learn",
        config=req.config,
        seed=req.seed,
        status="running",
    )
    session.add(experiment)
    await session.commit()
    await session.refresh(experiment)

    # Create job
    job = Job(
        project_id=req.project_id,
        job_type="training",
        status="running",
        config={"experiment_id": experiment.id, "algorithm": req.algorithm},
        started_at=datetime.now(timezone.utc),
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Run training in process pool
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            _executor,
            _train_model_sync,
            dataset.path, req.algorithm, req.task_type,
            req.config, req.seed, req.test_size, model_save_path, req.target_column,
        )
    except Exception as e:
        experiment.status = "failed"
        experiment.error_message = traceback.format_exc()
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
        raise HTTPException(422, detail={
            "error": "TRAINING_EXECUTION_ERROR",
            "message": f"Training failed during execution: {str(e)}",
        })

    if "error" in result:
        experiment.status = "failed"
        experiment.error_message = result["error"]
        job.status = "failed"
        job.error_message = result["error"]
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
        raise HTTPException(422, detail={
            "error": "TRAINING_ERROR",
            "message": result["error"],
        })

    # Update experiment
    experiment.status = "completed"
    experiment.metrics = result["metrics"]
    experiment.model_path = model_save_path
    experiment.model_size_bytes = result["model_size_bytes"]
    experiment.duration_seconds = result["duration_seconds"]
    experiment.input_shape = result["input_shape"]
    experiment.output_shape = result["output_shape"]
    experiment.framework_version = result["framework_version"]
    experiment.reproducibility = {
        "seed": req.seed,
        "framework": "scikit-learn",
        "framework_version": result["framework_version"],
        "algorithm": req.algorithm,
        "config": req.config,
        "test_size": req.test_size,
        "dataset_version": dataset.version,
    }

    # Create model record
    model_record = Model(
        experiment_id=experiment.id,
        name=exp_name,
        format="pickle",
        path=model_save_path,
        size_bytes=result["model_size_bytes"],
        input_shape=result["input_shape"],
        output_shape=result["output_shape"],
    )
    session.add(model_record)

    job.status = "completed"
    job.progress = 100.0
    job.result = result
    job.completed_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(experiment)

    return {
        "experiment_id": experiment.id,
        "job_id": job.id,
        "algorithm": req.algorithm,
        "status": "completed",
        "metrics": result["metrics"],
        "model_size_bytes": result["model_size_bytes"],
        "duration_seconds": result["duration_seconds"],
        "input_shape": result["input_shape"],
        "output_shape": result["output_shape"],
    }


@router.post("/automl")
async def run_automl(req: AutoMLRequest, session: AsyncSession = Depends(get_session)):
    """Run AutoML — analyze dataset and train appropriate models."""
    # Validate
    proj = await session.execute(select(Project).where(Project.id == req.project_id))
    project = proj.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    ds = await session.execute(select(Dataset).where(Dataset.id == req.dataset_id))
    dataset = ds.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    if not os.path.exists(dataset.path):
        raise HTTPException(404, "Dataset file not found")

    # Analyze dataset & determine target characteristics
    df = pd.read_csv(dataset.path)
    target_info = inspect_dataset_target(df, req.target_column)

    # Automatically adapt task type based on target type
    active_task_type = req.task_type
    if target_info["target_type"] in ("categorical", "boolean", "numeric discrete/class-like"):
        active_task_type = "classification"
    elif target_info["target_type"] == "numeric continuous":
        active_task_type = "regression"
    elif active_task_type not in ("classification", "regression"):
        active_task_type = target_info["task_suggestion"]

    n_samples = len(df)
    n_features = len(df.columns) - 1
    n_classes = df[target_info["target_column"]].nunique()

    # Intelligent algorithm selection based on dataset characteristics
    candidates = []

    if active_task_type == "classification":
        # Always include these lightweight models
        candidates.append({"algorithm": "decision_tree", "config": {"max_depth": 10}})
        candidates.append({"algorithm": "random_forest", "config": {"n_estimators": 100, "max_depth": 15}})
        candidates.append({"algorithm": "knn", "config": {"n_neighbors": min(5, max(1, n_samples - 1))}})

        if n_samples >= 15:
            candidates.append({"algorithm": "svm", "config": {"kernel": "rbf", "C": 1.0}})
            candidates.append({"algorithm": "logistic_regression", "config": {"max_iter": 1000}})

        if n_samples > 50:
            candidates.append({"algorithm": "gradient_boosting", "config": {"n_estimators": 100, "max_depth": 5}})

        if n_samples > 100 and n_features > 3:
            candidates.append({"algorithm": "mlp", "config": {"hidden_layer_sizes": (64, 32), "max_iter": 500}})
    else:
        candidates.append({"algorithm": "linear_regression", "config": {}})
        candidates.append({"algorithm": "decision_tree", "config": {"max_depth": 10}})
        candidates.append({"algorithm": "random_forest", "config": {"n_estimators": 100}})
        candidates.append({"algorithm": "knn", "config": {"n_neighbors": min(5, max(1, n_samples - 1))}})
        if n_samples > 30:
            candidates.append({"algorithm": "gradient_boosting", "config": {"n_estimators": 100}})
        if n_samples > 100:
            candidates.append({"algorithm": "mlp", "config": {"hidden_layer_sizes": (64, 32), "max_iter": 500}})

    # Limit candidates
    candidates = candidates[:req.max_models]

    # Train all candidates
    results = []
    loop = asyncio.get_event_loop()

    for candidate in candidates:
        exp_name = f"automl_{candidate['algorithm']}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        model_save_path = os.path.join(project.path, "models", f"{exp_name}.pkl")

        experiment = Experiment(
            project_id=req.project_id,
            dataset_id=req.dataset_id,
            name=exp_name,
            algorithm=candidate["algorithm"],
            framework="scikit-learn",
            config=candidate["config"],
            seed=req.seed,
            status="running",
        )
        session.add(experiment)
        await session.commit()
        await session.refresh(experiment)

        try:
            result = await loop.run_in_executor(
                _executor,
                _train_model_sync,
                dataset.path, candidate["algorithm"], active_task_type,
                candidate["config"], req.seed, req.test_size,
                model_save_path, target_info["target_column"],
            )

            if "error" in result:
                experiment.status = "failed"
                experiment.error_message = result["error"]
                await session.commit()
                results.append({
                    "algorithm": candidate["algorithm"],
                    "status": "failed",
                    "error": result["error"],
                })
                continue

            experiment.status = "completed"
            experiment.metrics = result["metrics"]
            experiment.model_path = model_save_path
            experiment.model_size_bytes = result["model_size_bytes"]
            experiment.duration_seconds = result["duration_seconds"]
            experiment.input_shape = result["input_shape"]
            experiment.output_shape = result["output_shape"]
            experiment.framework_version = result["framework_version"]

            model_record = Model(
                experiment_id=experiment.id,
                name=exp_name,
                format="pickle",
                path=model_save_path,
                size_bytes=result["model_size_bytes"],
                input_shape=result["input_shape"],
                output_shape=result["output_shape"],
            )
            session.add(model_record)
            await session.commit()

            results.append({
                "experiment_id": experiment.id,
                "algorithm": candidate["algorithm"],
                "config": candidate["config"],
                "status": "completed",
                "metrics": result["metrics"],
                "model_size_bytes": result["model_size_bytes"],
                "duration_seconds": result["duration_seconds"],
            })

        except Exception as e:
            experiment.status = "failed"
            experiment.error_message = str(e)
            await session.commit()
            results.append({
                "algorithm": candidate["algorithm"],
                "status": "failed",
                "error": str(e),
            })

    # Sort by primary metric
    completed = [r for r in results if r["status"] == "completed"]
    if active_task_type == "classification":
        completed.sort(key=lambda x: x["metrics"].get("accuracy", 0), reverse=True)
    else:
        completed.sort(key=lambda x: x["metrics"].get("r2", 0), reverse=True)

    # Summary
    summary = {
        "total_models": len(candidates),
        "completed": len(completed),
        "failed": len(results) - len(completed),
        "dataset_analysis": {
            "target_column": target_info["target_column"],
            "target_type": target_info["target_type"],
            "detected_task": active_task_type,
            "samples": n_samples,
            "features": n_features,
            "classes": n_classes if active_task_type == "classification" else None,
        },
    }

    if completed:
        best = completed[0]
        summary["best_accuracy" if active_task_type == "classification" else "best_r2"] = best
        summary["smallest_model"] = min(completed, key=lambda x: x["model_size_bytes"])

        if active_task_type == "regression":
            best_r2 = best["metrics"].get("test_r2", best["metrics"].get("r2"))
            summary["baseline"] = best["metrics"].get("baseline", {"type": "mean", "test_r2": 0.0})
            if best_r2 is not None:
                if best_r2 < 0:
                    summary["model_quality_warning"] = "No candidate model outperformed the mean baseline on the held-out test set."
                elif best_r2 < 0.25:
                    summary["model_quality_warning"] = "Best model shows weak predictive performance on the held-out test set."
                elif best_r2 < 0.50:
                    summary["model_quality_warning"] = "Only marginal improvement over baseline."
                else:
                    summary["model_quality_warning"] = None

    return {"summary": summary, "results": results}
