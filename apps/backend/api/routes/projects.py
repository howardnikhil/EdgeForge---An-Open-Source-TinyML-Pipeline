"""Project management API."""
import os
import shutil
import yaml
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from models.db_models import Project

router = APIRouter()

# Default workspace for projects
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "..", "projects")
os.makedirs(WORKSPACE_DIR, exist_ok=True)


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    project_type: str = "generic"  # sensor, audio, vision, generic


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


PROJECT_DIRS = [
    "dataset/raw", "dataset/processed", "dataset/metadata", "dataset/splits",
    "sensors", "pipelines", "experiments", "models",
    "hardware", "firmware", "emulation", "deployment", "reports"
]


def _create_project_dirs(project_path: str):
    """Create the standard project directory structure."""
    for d in PROJECT_DIRS:
        os.makedirs(os.path.join(project_path, d), exist_ok=True)


def _write_project_yaml(project_path: str, name: str, description: str, project_type: str):
    """Write project.yaml config file."""
    config = {
        "name": name,
        "description": description,
        "type": project_type,
        "version": "0.1.0",
        "created": datetime.now(timezone.utc).isoformat(),
        "edgeforge_version": "0.1.0",
    }
    with open(os.path.join(project_path, "project.yaml"), "w") as f:
        yaml.dump(config, f, default_flow_style=False)


@router.get("")
async def list_projects(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project).order_by(Project.updated_at.desc()))
    projects = result.scalars().all()
    return [
        {
            "id": p.id, "name": p.name, "description": p.description,
            "project_type": p.project_type, "path": p.path,
            "created_at": p.created_at.isoformat(), "updated_at": p.updated_at.isoformat(),
        }
        for p in projects
    ]


@router.post("")
async def create_project(data: ProjectCreate, session: AsyncSession = Depends(get_session)):
    # Sanitize name for directory
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in data.name).strip()
    if not safe_name:
        raise HTTPException(400, "Invalid project name")

    project_path = os.path.abspath(os.path.join(WORKSPACE_DIR, safe_name.replace(" ", "-").lower()))

    # Prevent path traversal
    if not project_path.startswith(os.path.abspath(WORKSPACE_DIR)):
        raise HTTPException(400, "Invalid project path")

    if os.path.exists(project_path):
        raise HTTPException(409, f"Project directory already exists: {safe_name}")

    # Create directories and config
    _create_project_dirs(project_path)
    _write_project_yaml(project_path, data.name, data.description, data.project_type)

    project = Project(
        name=data.name,
        description=data.description,
        project_type=data.project_type,
        path=project_path,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)

    return {
        "id": project.id, "name": project.name, "description": project.description,
        "project_type": project.project_type, "path": project.path,
        "created_at": project.created_at.isoformat(), "updated_at": project.updated_at.isoformat(),
    }


@router.get("/{project_id}")
async def get_project(project_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    # Build file tree
    file_tree = []
    if os.path.exists(project.path):
        for root, dirs, files in os.walk(project.path):
            rel = os.path.relpath(root, project.path)
            for f in files:
                file_tree.append(os.path.join(rel, f) if rel != "." else f)

    return {
        "id": project.id, "name": project.name, "description": project.description,
        "project_type": project.project_type, "path": project.path,
        "created_at": project.created_at.isoformat(), "updated_at": project.updated_at.isoformat(),
        "files": file_tree,
    }


@router.patch("/{project_id}")
async def update_project(project_id: str, data: ProjectUpdate, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description

    project.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(project)

    return {"id": project.id, "name": project.name, "description": project.description}


@router.delete("/{project_id}")
async def delete_project(project_id: str, delete_files: bool = False, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    if delete_files and os.path.exists(project.path):
        shutil.rmtree(project.path)

    await session.delete(project)
    await session.commit()

    return {"deleted": True, "id": project_id}
