from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_active_user, get_optional_current_user
from app.database import get_db
from app.models.preference import UserServicePreference
from app.models.user import User
from app.schemas.service import ServiceItem, ServicePreferenceUpdate
from services.music.aggregator import aggregator

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("", response_model=list[ServiceItem])
@router.get("/", response_model=list[ServiceItem], include_in_schema=False)
async def list_services(
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
) -> list[ServiceItem]:
    enabled_set: set[str] | None = None
    if current_user and current_user.id:
        stmt = select(UserServicePreference).where(UserServicePreference.user_id == current_user.id)
        result = await db.exec(stmt)
        prefs = result.all()
        if prefs:
            enabled_set = {p.service for p in prefs if p.is_enabled}

    raw_services = aggregator.get_services_status(enabled_services=enabled_set)
    return [ServiceItem(**s) for s in raw_services]


@router.put("/preferences", response_model=list[ServiceItem])
async def update_service_preferences(
    payload: ServicePreferenceUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> list[ServiceItem]:
    assert current_user.id is not None
    # Load existing preferences
    stmt = select(UserServicePreference).where(UserServicePreference.user_id == current_user.id)
    result = await db.exec(stmt)
    existing_map = {p.service.lower(): p for p in result.all()}

    all_supported = ["yandex", "spotify", "soundcloud", "youtube"]
    requested_set = {s.lower() for s in payload.enabled_services}

    for svc in all_supported:
        pref = existing_map.get(svc)
        is_on = (svc in requested_set or (svc == "yandex" and "ям" in requested_set)
                 or (svc == "spotify" and "sp" in requested_set)
                 or (svc == "soundcloud" and "sc" in requested_set)
                 or (svc == "youtube" and "yt" in requested_set))

        if pref:
            pref.is_enabled = is_on
            db.add(pref)
        else:
            new_pref = UserServicePreference(user_id=current_user.id, service=svc, is_enabled=is_on)
            db.add(new_pref)

    await db.commit()

    # Return updated status
    enabled_names = {svc for svc in all_supported if (
        svc in requested_set or (svc == "yandex" and "ям" in requested_set)
        or (svc == "spotify" and "sp" in requested_set)
        or (svc == "soundcloud" and "sc" in requested_set)
        or (svc == "youtube" and "yt" in requested_set)
    )}
    raw_services = aggregator.get_services_status(enabled_services=enabled_names)
    return [ServiceItem(**s) for s in raw_services]
