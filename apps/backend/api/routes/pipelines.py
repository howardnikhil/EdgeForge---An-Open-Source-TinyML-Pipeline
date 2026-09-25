"""Pipeline management API."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session
from models.db_models import Pipeline

router = APIRouter()


class PipelineCreate(BaseModel):
    project_id: str
    name: str
    nodes: list = []
    edges: list = []
    config: dict = {}


class PipelineUpdate(BaseModel):
    name: str | None = None
    nodes: list | None = None
    edges: list | None = None
    config: dict | None = None


@router.get("")
async def list_pipelines(project_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Pipeline).where(Pipeline.project_id == project_id))
    pipelines = result.scalars().all()
    return [
        {"id": p.id, "name": p.name, "nodes": p.nodes, "edges": p.edges, "created_at": p.created_at.isoformat()}
        for p in pipelines
    ]


@router.post("")
async def create_pipeline(data: PipelineCreate, session: AsyncSession = Depends(get_session)):
    pipeline = Pipeline(
        project_id=data.project_id,
        name=data.name,
        nodes=data.nodes,
        edges=data.edges,
        config=data.config,
    )
    session.add(pipeline)
    await session.commit()
    await session.refresh(pipeline)
    return {"id": pipeline.id, "name": pipeline.name}


@router.get("/{pipeline_id}")
async def get_pipeline(pipeline_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Pipeline not found")
    return {"id": p.id, "name": p.name, "nodes": p.nodes, "edges": p.edges, "config": p.config}


@router.patch("/{pipeline_id}")
async def update_pipeline(pipeline_id: str, data: PipelineUpdate, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Pipeline not found")

    if data.name is not None:
        p.name = data.name
    if data.nodes is not None:
        p.nodes = data.nodes
    if data.edges is not None:
        p.edges = data.edges
    if data.config is not None:
        p.config = data.config

    await session.commit()
    return {"id": p.id, "name": p.name}


@router.delete("/{pipeline_id}")
async def delete_pipeline(pipeline_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Pipeline not found")
    await session.delete(p)
    await session.commit()
    return {"deleted": True}
