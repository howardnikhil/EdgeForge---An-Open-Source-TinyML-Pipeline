"""Dataset management API."""
import os
import csv
import json
import shutil
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from models.db_models import Dataset, Project

from core.ml_validation import inspect_dataset_target

router = APIRouter()


class DatasetCreate(BaseModel):
    project_id: str
    name: str
    dataset_type: str = "timeseries"


class DatasetSplit(BaseModel):
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    seed: int = 42
    stratify: bool = True


class LabelUpdate(BaseModel):
    sample_indices: list[int]
    label: str


@router.get("")
async def list_datasets(project_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dataset).where(Dataset.project_id == project_id))
    datasets = result.scalars().all()
    res = []
    for d in datasets:
        target_info = {}
        if os.path.exists(d.path):
            try:
                df = pd.read_csv(d.path, nrows=100)
                target_info = inspect_dataset_target(df)
            except Exception:
                pass
        res.append({
            "id": d.id, "name": d.name, "version": d.version,
            "dataset_type": d.dataset_type, "num_samples": d.num_samples,
            "num_classes": d.num_classes, "class_labels": d.class_labels,
            "statistics": d.statistics, "created_at": d.created_at.isoformat(),
            "target_info": target_info,
        })
    return res


@router.post("/import-csv")
async def import_csv(
    project_id: str = Form(...),
    name: str = Form(...),
    dataset_type: str = Form("timeseries"),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """Import a CSV file as a dataset."""
    # Verify project exists
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    # Read CSV content
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be UTF-8 encoded CSV")

    # Parse CSV
    try:
        df = pd.read_csv(pd.io.common.StringIO(text))
    except Exception as e:
        raise HTTPException(400, f"CSV parsing error: {str(e)}")

    if df.empty:
        raise HTTPException(400, "CSV file is empty")

    # Save raw data
    raw_dir = os.path.join(project.path, "dataset", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, f"{name}.csv")
    df.to_csv(raw_path, index=False)

    # Compute statistics & target info
    stats = _compute_statistics(df)
    target_info = inspect_dataset_target(df)

    # Detect classes if 'label' column exists
    class_labels = {}
    num_classes = 0
    if "label" in df.columns:
        class_labels = {str(k): int(v) for k, v in df["label"].value_counts().to_dict().items()}
        num_classes = len(class_labels)

    dataset = Dataset(
        project_id=project_id,
        name=name,
        dataset_type=dataset_type,
        path=raw_path,
        num_samples=len(df),
        num_classes=num_classes,
        class_labels=class_labels,
        statistics=stats,
    )
    session.add(dataset)
    await session.commit()
    await session.refresh(dataset)

    return {
        "id": dataset.id, "name": dataset.name, "num_samples": dataset.num_samples,
        "num_classes": num_classes, "class_labels": class_labels,
        "statistics": stats, "columns": list(df.columns),
        "target_info": target_info,
    }


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    # Load preview data & target info
    preview = []
    target_info = {}
    cols = []
    if os.path.exists(dataset.path):
        df_full = pd.read_csv(dataset.path)
        preview = df_full.head(100).to_dict(orient="records")
        target_info = inspect_dataset_target(df_full)
        cols = list(df_full.columns)

    return {
        "id": dataset.id, "name": dataset.name, "version": dataset.version,
        "dataset_type": dataset.dataset_type, "num_samples": dataset.num_samples,
        "num_classes": dataset.num_classes, "class_labels": dataset.class_labels,
        "statistics": dataset.statistics, "preview": preview,
        "columns": cols,
        "target_info": target_info,
    }


@router.get("/{dataset_id}/statistics")
async def get_statistics(dataset_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    if not os.path.exists(dataset.path):
        raise HTTPException(404, "Dataset file not found on disk")

    df = pd.read_csv(dataset.path)
    stats = _compute_statistics(df)

    # Update stored stats
    dataset.statistics = stats
    await session.commit()

    return stats


@router.post("/{dataset_id}/split")
async def split_dataset(dataset_id: str, config: DatasetSplit, session: AsyncSession = Depends(get_session)):
    """Split dataset into train/validation/test sets."""
    result = await session.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    if abs(config.train_ratio + config.val_ratio + config.test_ratio - 1.0) > 0.01:
        raise HTTPException(400, "Split ratios must sum to 1.0")

    df = pd.read_csv(dataset.path)
    n = len(df)

    # Shuffle with seed
    rng = np.random.RandomState(config.seed)
    indices = rng.permutation(n)

    train_end = int(n * config.train_ratio)
    val_end = train_end + int(n * config.val_ratio)

    train_idx = indices[:train_end]
    val_idx = indices[train_end:val_end]
    test_idx = indices[val_end:]

    # Get project path from dataset path
    project_path = os.path.dirname(os.path.dirname(os.path.dirname(dataset.path)))
    splits_dir = os.path.join(project_path, "dataset", "splits")
    os.makedirs(splits_dir, exist_ok=True)

    # Save splits
    df.iloc[train_idx].to_csv(os.path.join(splits_dir, f"{dataset.name}_train.csv"), index=False)
    df.iloc[val_idx].to_csv(os.path.join(splits_dir, f"{dataset.name}_val.csv"), index=False)
    df.iloc[test_idx].to_csv(os.path.join(splits_dir, f"{dataset.name}_test.csv"), index=False)

    split_info = {
        "train": {"count": len(train_idx), "ratio": config.train_ratio},
        "validation": {"count": len(val_idx), "ratio": config.val_ratio},
        "test": {"count": len(test_idx), "ratio": config.test_ratio},
        "seed": config.seed,
        "stratified": config.stratify,
    }

    dataset.split_config = split_info
    await session.commit()

    return split_info


@router.post("/{dataset_id}/label")
async def update_labels(dataset_id: str, data: LabelUpdate, session: AsyncSession = Depends(get_session)):
    """Update labels for specific samples."""
    result = await session.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    df = pd.read_csv(dataset.path)

    if "label" not in df.columns:
        df["label"] = ""

    valid_indices = [i for i in data.sample_indices if 0 <= i < len(df)]
    if not valid_indices:
        raise HTTPException(400, "No valid sample indices provided")

    df.loc[valid_indices, "label"] = data.label
    df.to_csv(dataset.path, index=False)

    # Update version
    dataset.version += 1
    dataset.class_labels = {str(k): int(v) for k, v in df["label"].value_counts().to_dict().items()}
    dataset.num_classes = len(dataset.class_labels)
    dataset.updated_at = datetime.now(timezone.utc)
    await session.commit()

    return {"updated": len(valid_indices), "version": dataset.version, "class_labels": dataset.class_labels}


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    if os.path.exists(dataset.path):
        os.remove(dataset.path)

    await session.delete(dataset)
    await session.commit()
    return {"deleted": True}


def _compute_statistics(df: pd.DataFrame) -> dict:
    """Compute comprehensive dataset statistics."""
    stats = {
        "num_rows": len(df),
        "num_columns": len(df.columns),
        "columns": {},
        "missing_values": {},
        "duplicates": int(df.duplicated().sum()),
    }

    for col in df.columns:
        col_stats = {"dtype": str(df[col].dtype)}
        missing = int(df[col].isna().sum())
        stats["missing_values"][col] = missing

        if pd.api.types.is_numeric_dtype(df[col]):
            desc = df[col].describe()
            col_stats.update({
                "min": float(desc["min"]) if not pd.isna(desc["min"]) else None,
                "max": float(desc["max"]) if not pd.isna(desc["max"]) else None,
                "mean": float(desc["mean"]) if not pd.isna(desc["mean"]) else None,
                "std": float(desc["std"]) if not pd.isna(desc["std"]) else None,
                "median": float(df[col].median()) if not df[col].isna().all() else None,
            })
        elif pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
            col_stats["unique"] = int(df[col].nunique())
            if df[col].nunique() <= 50:
                col_stats["value_counts"] = {str(k): int(v) for k, v in df[col].value_counts().head(20).items()}

        stats["columns"][col] = col_stats

    return stats
