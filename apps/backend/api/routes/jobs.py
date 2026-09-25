"""Job management API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session
from models.db_models import Job

router = APIRouter()


@router.get("")
async def list_jobs(project_id: str | None = None, session: AsyncSession = Depends(get_session)):
    query = select(Job).order_by(Job.created_at.desc())
    if project_id:
        query = query.where(Job.project_id == project_id)
    result = await session.execute(query)
    jobs = result.scalars().all()
    return [
        {
            "id": j.id, "job_type": j.job_type, "status": j.status,
            "progress": j.progress, "created_at": j.created_at.isoformat(),
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            "error_message": j.error_message,
        }
        for j in jobs
    ]


@router.get("/{job_id}")
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "id": job.id, "job_type": job.job_type, "status": job.status,
        "progress": job.progress, "config": job.config, "result": job.result,
        "logs": job.logs, "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status in ("completed", "failed", "cancelled"):
        raise HTTPException(400, f"Job already {job.status}")
    job.status = "cancelled"
    await session.commit()
    return {"cancelled": True}
