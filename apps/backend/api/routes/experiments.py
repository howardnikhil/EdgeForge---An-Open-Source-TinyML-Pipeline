"""Experiment tracking API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session
from models.db_models import Experiment

router = APIRouter()


@router.get("")
async def list_experiments(project_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Experiment)
        .where(Experiment.project_id == project_id)
        .order_by(Experiment.created_at.desc())
    )
    experiments = result.scalars().all()
    return [
        {
            "id": e.id, "name": e.name, "algorithm": e.algorithm,
            "framework": e.framework, "status": e.status,
            "metrics": e.metrics, "config": e.config,
            "model_size_bytes": e.model_size_bytes,
            "duration_seconds": e.duration_seconds,
            "quantization": e.quantization,
            "seed": e.seed, "created_at": e.created_at.isoformat(),
            "error_message": e.error_message,
        }
        for e in experiments
    ]


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Experiment).where(Experiment.id == experiment_id))
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(404, "Experiment not found")

    return {
        "id": exp.id, "name": exp.name, "algorithm": exp.algorithm,
        "framework": exp.framework, "framework_version": exp.framework_version,
        "status": exp.status, "metrics": exp.metrics, "config": exp.config,
        "model_path": exp.model_path, "model_size_bytes": exp.model_size_bytes,
        "duration_seconds": exp.duration_seconds, "quantization": exp.quantization,
        "input_shape": exp.input_shape, "output_shape": exp.output_shape,
        "seed": exp.seed, "reproducibility": exp.reproducibility,
        "error_message": exp.error_message, "created_at": exp.created_at.isoformat(),
    }


@router.post("/compare")
async def compare_experiments(experiment_ids: list[str], session: AsyncSession = Depends(get_session)):
    """Compare multiple experiments side-by-side."""
    result = await session.execute(
        select(Experiment).where(Experiment.id.in_(experiment_ids))
    )
    experiments = result.scalars().all()

    comparison = []
    for exp in experiments:
        comparison.append({
            "id": exp.id, "name": exp.name, "algorithm": exp.algorithm,
            "metrics": exp.metrics, "model_size_bytes": exp.model_size_bytes,
            "duration_seconds": exp.duration_seconds, "quantization": exp.quantization,
        })

    return {"experiments": comparison}


@router.delete("/{experiment_id}")
async def delete_experiment(experiment_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Experiment).where(Experiment.id == experiment_id))
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(404, "Experiment not found")

    import os
    if exp.model_path and os.path.exists(exp.model_path):
        os.remove(exp.model_path)

    await session.delete(exp)
    await session.commit()
    return {"deleted": True}
