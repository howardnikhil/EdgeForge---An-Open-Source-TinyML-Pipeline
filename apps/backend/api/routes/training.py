"""ML Training API with real scikit-learn training."""
import os
import time
import json
import pickle
import traceback
import uuid
import asyncio
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import numpy as np
import pandas as pd

from core.database import get_session
from models.db_models import Project, Dataset, Experiment, Model, Job

router = APIRouter()

_executor = ProcessPoolExecutor(max_workers=2)


class TrainRequest(BaseModel):
    project_id: str
    dataset_id: str
    algorithm: str  # decision_tree, random_forest, svm, knn, gradient_boosting, logistic_regression, mlp
    task_type: str = "classification"  # classification, regression
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
    """Synchronous training function — runs in a separate process."""
    import sklearn
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (
        accuracy_score, f1_score, precision_score, recall_score,
        mean_squared_error, r2_score, confusion_matrix,
    )
    from sklearn.preprocessing import LabelEncoder

    start_time = time.time()

    # Load data
    df = pd.read_csv(dataset_path)

    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found. Available: {list(df.columns)}"}

    # Separate features and target
    X = df.drop(columns=[target_column])
    y = df[target_column]

    # Handle non-numeric features
    for col in X.columns:
        if X[col].dtype == object:
            X[col] = pd.Categorical(X[col]).codes

    # Handle NaN
    X = X.fillna(0)

    # Encode labels for classification
    le = None
    if task_type == "classification" and y.dtype == object:
        le = LabelEncoder()
        y = pd.Series(le.fit_transform(y))

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y if task_type == "classification" else None
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

    # Train
    model = ModelClass(**model_config)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    metrics = {}

    if task_type == "classification":
        metrics["accuracy"] = float(accuracy_score(y_test, y_pred))
        metrics["f1_score"] = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
        metrics["precision"] = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
        metrics["recall"] = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))

        cm = confusion_matrix(y_test, y_pred)
        metrics["confusion_matrix"] = cm.tolist()

        if le:
            metrics["class_names"] = le.classes_.tolist()
    else:
        metrics["mse"] = float(mean_squared_error(y_test, y_pred))
        metrics["rmse"] = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        metrics["r2"] = float(r2_score(y_test, y_pred))

    # Save model
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    with open(model_save_path, "wb") as f:
        pickle.dump({"model": model, "label_encoder": le, "feature_names": list(X.columns)}, f)

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

    # Validate algorithm
    if req.algorithm not in ALGORITHM_MAP:
        raise HTTPException(400, f"Unknown algorithm: {req.algorithm}. Available: {list(ALGORITHM_MAP.keys())}")

    if not ALGORITHM_MAP[req.algorithm].get(req.task_type):
        raise HTTPException(400, f"Algorithm '{req.algorithm}' does not support task '{req.task_type}'")

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
            req.config, req.seed, req.test_size, model_save_path,
        )
    except Exception as e:
        experiment.status = "failed"
        experiment.error_message = traceback.format_exc()
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
        raise HTTPException(500, f"Training failed: {str(e)}")

    if "error" in result:
        experiment.status = "failed"
        experiment.error_message = result["error"]
        job.status = "failed"
        job.error_message = result["error"]
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
        raise HTTPException(400, result["error"])

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

    # Analyze dataset
    df = pd.read_csv(dataset.path)
    if req.target_column not in df.columns:
        raise HTTPException(400, f"Target column '{req.target_column}' not found")

    n_samples = len(df)
    n_features = len(df.columns) - 1
    n_classes = df[req.target_column].nunique()

    # Intelligent algorithm selection based on dataset characteristics
    candidates = []

    if req.task_type == "classification":
        # Always include these lightweight models
        candidates.append({"algorithm": "decision_tree", "config": {"max_depth": 10}})
        candidates.append({"algorithm": "random_forest", "config": {"n_estimators": 100, "max_depth": 15}})
        candidates.append({"algorithm": "knn", "config": {"n_neighbors": min(5, n_samples - 1)}})

        if n_samples > 50:
            candidates.append({"algorithm": "svm", "config": {"kernel": "rbf", "C": 1.0}})
            candidates.append({"algorithm": "logistic_regression", "config": {"max_iter": 1000}})

        if n_samples > 100:
            candidates.append({"algorithm": "gradient_boosting", "config": {"n_estimators": 100, "max_depth": 5}})

        if n_samples > 200 and n_features > 3:
            candidates.append({"algorithm": "mlp", "config": {"hidden_layer_sizes": (64, 32), "max_iter": 500}})
            candidates.append({"algorithm": "random_forest", "config": {"n_estimators": 200, "max_depth": 20, "min_samples_leaf": 2}})
    else:
        candidates.append({"algorithm": "linear_regression", "config": {}})
        candidates.append({"algorithm": "decision_tree", "config": {"max_depth": 10}})
        candidates.append({"algorithm": "random_forest", "config": {"n_estimators": 100}})
        candidates.append({"algorithm": "knn", "config": {"n_neighbors": min(5, n_samples - 1)}})
        if n_samples > 50:
            candidates.append({"algorithm": "gradient_boosting", "config": {"n_estimators": 100}})
        if n_samples > 200:
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
                dataset.path, candidate["algorithm"], req.task_type,
                candidate["config"], req.seed, req.test_size,
                model_save_path, req.target_column,
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
    if req.task_type == "classification":
        completed.sort(key=lambda x: x["metrics"].get("accuracy", 0), reverse=True)
    else:
        completed.sort(key=lambda x: x["metrics"].get("r2", 0), reverse=True)

    # Summary
    summary = {
        "total_models": len(candidates),
        "completed": len(completed),
        "failed": len(results) - len(completed),
        "dataset_analysis": {
            "samples": n_samples,
            "features": n_features,
            "classes": n_classes if req.task_type == "classification" else None,
        },
    }

    if completed:
        best = completed[0]
        summary["best_accuracy" if req.task_type == "classification" else "best_r2"] = best
        summary["smallest_model"] = min(completed, key=lambda x: x["model_size_bytes"])

    return {"summary": summary, "results": results}
