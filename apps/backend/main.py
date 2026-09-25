"""HowNik's EdgeForge Backend - Main Application Entry Point"""
import os
import sys

# Add workspace root and backend directories to path for imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(backend_dir))
for p in (root_dir, backend_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.database import init_db, get_engine
from api.routes import projects, datasets, serial, training, experiments, models as models_routes
from api.routes import hardware, firmware, pipelines, jobs, ai, settings, system, emulation, validation


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and services on startup."""
    await init_db()
    print("\n  ╔══════════════════════════════════════╗")
    print("  ║   HowNik's EdgeForge Backend v0.1.0  ║")
    print("  ║   http://127.0.0.1:8000              ║")
    print("  ╚══════════════════════════════════════╝\n")
    yield
    # Cleanup
    engine = get_engine()
    if engine:
        await engine.dispose()


app = FastAPI(
    title="HowNik's EdgeForge",
    description="TinyML / Edge-AI Engineering IDE",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["datasets"])
app.include_router(serial.router, prefix="/api/v1/serial", tags=["serial"])
app.include_router(pipelines.router, prefix="/api/v1/pipelines", tags=["pipelines"])
app.include_router(training.router, prefix="/api/v1/training", tags=["training"])
app.include_router(experiments.router, prefix="/api/v1/experiments", tags=["experiments"])
app.include_router(models_routes.router, prefix="/api/v1/models", tags=["models"])
app.include_router(hardware.router, prefix="/api/v1/hardware", tags=["hardware"])
app.include_router(firmware.router, prefix="/api/v1/firmware", tags=["firmware"])
app.include_router(emulation.router, prefix="/api/v1/emulation", tags=["emulation"])
app.include_router(validation.router, prefix="/api/v1/validation", tags=["validation"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])


@app.get("/")
async def root():
    return {"name": "HowNik's EdgeForge", "version": "0.1.0", "status": "running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
