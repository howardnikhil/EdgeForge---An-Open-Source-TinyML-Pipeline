"""Settings API."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session
from models.db_models import Setting

router = APIRouter()


class SettingUpdate(BaseModel):
    key: str
    value: str
    category: str = "general"


@router.get("")
async def list_settings(category: str | None = None, session: AsyncSession = Depends(get_session)):
    query = select(Setting)
    if category:
        query = query.where(Setting.category == category)
    result = await session.execute(query)
    settings = result.scalars().all()

    # Mask API keys
    return [
        {
            "key": s.key,
            "value": _mask_if_key(s.key, s.value),
            "category": s.category,
            "has_value": bool(s.value),
        }
        for s in settings
    ]


@router.put("")
async def update_setting(data: SettingUpdate, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Setting).where(Setting.key == data.key))
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = data.value
        setting.category = data.category
    else:
        setting = Setting(key=data.key, value=data.value, category=data.category)
        session.add(setting)

    await session.commit()
    return {"key": data.key, "updated": True}


@router.get("/{key}")
async def get_setting(key: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(404, "Setting not found")
    return {
        "key": setting.key,
        "value": _mask_if_key(setting.key, setting.value),
        "category": setting.category,
        "has_value": bool(setting.value),
    }


@router.delete("/{key}")
async def delete_setting(key: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(404, "Setting not found")
    await session.delete(setting)
    await session.commit()
    return {"deleted": True}


def _mask_if_key(key: str, value: str) -> str:
    """Mask API keys in responses."""
    if "api_key" in key and value:
        if len(value) > 8:
            return value[:4] + "****" + value[-4:]
        return "****"
    return value
