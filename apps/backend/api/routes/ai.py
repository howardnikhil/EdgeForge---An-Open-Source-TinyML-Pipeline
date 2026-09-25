"""AI Assistant API — multi-provider chat with project context."""
import os
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session
from models.db_models import Project, Dataset, Experiment, Setting

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # user, assistant, system
    content: str


class ChatRequest(BaseModel):
    project_id: str | None = None
    messages: list[ChatMessage]
    provider: str = "openai"  # openai, anthropic, gemini, openrouter, ollama


class ProviderConfig(BaseModel):
    provider: str
    api_key: str
    base_url: str | None = None
    model: str | None = None


@router.get("/providers")
async def list_providers(session: AsyncSession = Depends(get_session)):
    """List configured AI providers."""
    providers = [
        {"id": "openai", "name": "OpenAI", "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]},
        {"id": "anthropic", "name": "Anthropic", "models": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"]},
        {"id": "gemini", "name": "Google Gemini", "models": ["gemini-2.5-pro", "gemini-2.0-flash"]},
        {"id": "openrouter", "name": "OpenRouter", "models": ["auto"]},
        {"id": "ollama", "name": "Ollama (Local)", "models": ["llama3", "mistral", "codellama"]},
    ]

    # Check which have API keys configured
    for p in providers:
        key_result = await session.execute(
            select(Setting).where(Setting.key == f"ai_api_key_{p['id']}")
        )
        setting = key_result.scalar_one_or_none()
        p["configured"] = bool(setting and setting.value)

    return providers


@router.post("/chat")
async def chat(req: ChatRequest, session: AsyncSession = Depends(get_session)):
    """Send a message to the AI assistant with project context."""
    # Get API key
    key_result = await session.execute(
        select(Setting).where(Setting.key == f"ai_api_key_{req.provider}")
    )
    key_setting = key_result.scalar_one_or_none()

    # Get model setting
    model_result = await session.execute(
        select(Setting).where(Setting.key == f"ai_model_{req.provider}")
    )
    model_setting = model_result.scalar_one_or_none()

    if req.provider == "ollama":
        api_key = "ollama"
        base_url = "http://localhost:11434/v1"
    elif not key_setting or not key_setting.value:
        raise HTTPException(400, f"No API key configured for {req.provider}. Go to Settings → AI Providers to configure.")
    else:
        api_key = key_setting.value
        base_url = None

    # Build project context
    system_prompt = _build_system_prompt()
    if req.project_id:
        project_context = await _get_project_context(req.project_id, session)
        system_prompt += f"\n\n## Current Project Context\n{project_context}"

    # Prepare messages
    messages = [{"role": "system", "content": system_prompt}]
    for msg in req.messages:
        messages.append({"role": msg.role, "content": msg.content})

    # Call provider
    try:
        import httpx

        if req.provider in ("openai", "openrouter"):
            url = base_url or ("https://openrouter.ai/api/v1" if req.provider == "openrouter" else "https://api.openai.com/v1")
            model = model_setting.value if model_setting and model_setting.value else ("gpt-4o-mini" if req.provider == "openai" else "auto")
            response = await _call_openai_compatible(url, api_key, model, messages)

        elif req.provider == "anthropic":
            model = model_setting.value if model_setting and model_setting.value else "claude-3-5-haiku-20241022"
            response = await _call_anthropic(api_key, model, messages)

        elif req.provider == "gemini":
            model = model_setting.value if model_setting and model_setting.value else "gemini-2.0-flash"
            response = await _call_openai_compatible(
                "https://generativelanguage.googleapis.com/v1beta/openai", api_key, model, messages
            )

        elif req.provider == "ollama":
            model = model_setting.value if model_setting and model_setting.value else "llama3"
            response = await _call_openai_compatible(base_url, api_key, model, messages)

        else:
            raise HTTPException(400, f"Unknown provider: {req.provider}")

        return {"response": response, "provider": req.provider}

    except httpx.ConnectError:
        if req.provider == "ollama":
            raise HTTPException(503, "Cannot connect to Ollama. Is it running? Start with: ollama serve")
        raise HTTPException(503, f"Cannot connect to {req.provider} API")
    except Exception as e:
        raise HTTPException(500, f"AI request failed: {str(e)}")


async def _call_openai_compatible(base_url: str, api_key: str, model: str, messages: list) -> str:
    import httpx
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 2048},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_anthropic(api_key: str, model: str, messages: list) -> str:
    import httpx
    # Extract system message
    system_msg = ""
    chat_messages = []
    for m in messages:
        if m["role"] == "system":
            system_msg = m["content"]
        else:
            chat_messages.append(m)

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": model,
                "system": system_msg,
                "messages": chat_messages,
                "max_tokens": 2048,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


def _build_system_prompt() -> str:
    return """You are the EdgeForge AI Assistant — an expert in TinyML, embedded systems, and Edge AI.

You help users with:
- Dataset analysis and preprocessing
- Model selection and training
- Hardware compatibility
- Firmware generation and optimization
- Debugging compilation and emulation issues
- Explaining ML concepts for embedded systems

You have access to the user's current project context. Be specific and technical.
When suggesting models, consider the target hardware constraints.
Always provide actionable, concrete advice."""


async def _get_project_context(project_id: str, session: AsyncSession) -> str:
    """Build a context string from the current project state."""
    proj_r = await session.execute(select(Project).where(Project.id == project_id))
    project = proj_r.scalar_one_or_none()
    if not project:
        return "No project loaded."

    context_parts = [f"Project: {project.name} (Type: {project.project_type})"]

    # Datasets
    ds_r = await session.execute(select(Dataset).where(Dataset.project_id == project_id))
    datasets = ds_r.scalars().all()
    if datasets:
        context_parts.append(f"\nDatasets ({len(datasets)}):")
        for d in datasets:
            context_parts.append(f"  - {d.name}: {d.num_samples} samples, {d.num_classes} classes, type={d.dataset_type}")
            if d.class_labels:
                context_parts.append(f"    Classes: {d.class_labels}")

    # Experiments
    exp_r = await session.execute(
        select(Experiment).where(Experiment.project_id == project_id).order_by(Experiment.created_at.desc()).limit(10)
    )
    experiments = exp_r.scalars().all()
    if experiments:
        context_parts.append(f"\nRecent Experiments ({len(experiments)}):")
        for e in experiments:
            metrics_str = ""
            if e.metrics:
                if "accuracy" in e.metrics:
                    metrics_str = f"accuracy={e.metrics['accuracy']:.4f}"
                elif "r2" in e.metrics:
                    metrics_str = f"r2={e.metrics['r2']:.4f}"
            context_parts.append(
                f"  - {e.name}: {e.algorithm} [{e.status}] {metrics_str} "
                f"size={e.model_size_bytes}B"
            )

    return "\n".join(context_parts)
