"""SQLAlchemy ORM Models for EdgeForge."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    project_type: Mapped[str] = mapped_column(String(50), default="generic")  # sensor, audio, vision, generic
    path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    sensors: Mapped[list["Sensor"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    pipelines: Mapped[list["Pipeline"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    experiments: Mapped[list["Experiment"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    dataset_type: Mapped[str] = mapped_column(String(50), default="timeseries")  # timeseries, audio, image, tabular
    path: Mapped[str] = mapped_column(Text, nullable=False)
    num_samples: Mapped[int] = mapped_column(Integer, default=0)
    num_classes: Mapped[int] = mapped_column(Integer, default=0)
    class_labels: Mapped[dict] = mapped_column(JSON, default=dict)
    split_config: Mapped[dict] = mapped_column(JSON, default=dict)
    statistics: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_extra: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    project: Mapped["Project"] = relationship(back_populates="datasets")
    experiments: Mapped[list["Experiment"]] = relationship(back_populates="dataset")


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sensor_type: Mapped[str] = mapped_column(String(50), default="custom")  # imu, temperature, audio, etc.
    interface: Mapped[str] = mapped_column(String(50), default="serial")
    fields: Mapped[list] = mapped_column(JSON, default=list)  # [{name, type, unit}]
    sample_rate: Mapped[float] = mapped_column(Float, default=100.0)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="sensors")


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    nodes: Mapped[list] = mapped_column(JSON, default=list)
    edges: Mapped[list] = mapped_column(JSON, default=list)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    project: Mapped["Project"] = relationship(back_populates="pipelines")


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(100), nullable=False)
    framework: Mapped[str] = mapped_column(String(50), default="scikit-learn")
    framework_version: Mapped[str] = mapped_column(String(50), default="")
    config: Mapped[dict] = mapped_column(JSON, default=dict)  # hyperparameters, preprocessing
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)  # accuracy, f1, etc.
    model_path: Mapped[str] = mapped_column(Text, default="")
    model_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    quantization: Mapped[str] = mapped_column(String(20), default="fp32")
    input_shape: Mapped[list] = mapped_column(JSON, default=list)
    output_shape: Mapped[list] = mapped_column(JSON, default=list)
    seed: Mapped[int] = mapped_column(Integer, default=42)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    reproducibility: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="experiments")
    dataset: Mapped["Dataset"] = relationship(back_populates="experiments")
    models: Mapped[list["Model"]] = relationship(back_populates="experiment", cascade="all, delete-orphan")


class Model(Base):
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(String(50), default="pickle")  # pickle, onnx, tflite, c_array
    path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    input_shape: Mapped[list] = mapped_column(JSON, default=list)
    output_shape: Mapped[list] = mapped_column(JSON, default=list)
    quantization: Mapped[str] = mapped_column(String(20), default="fp32")
    metadata_extra: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    experiment: Mapped["Experiment"] = relationship(back_populates="models")


class HardwareProfile(Base):
    __tablename__ = "hardware_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    architecture: Mapped[str] = mapped_column(String(50), nullable=False)
    flash_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    ram_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    cpu_freq_mhz: Mapped[int] = mapped_column(Integer, default=0)
    toolchain: Mapped[str] = mapped_column(String(100), default="")
    runtime: Mapped[str] = mapped_column(String(100), default="")
    emulator: Mapped[str] = mapped_column(String(100), default="")
    deployment_formats: Mapped[list] = mapped_column(JSON, default=list)
    supported_operators: Mapped[list] = mapped_column(JSON, default=list)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)  # training, preprocessing, firmware, emulation
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued, running, completed, failed, cancelled
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    logs: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="jobs")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), default="general")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
