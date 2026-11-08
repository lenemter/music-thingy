from __future__ import annotations

from pydantic import BaseModel


class ServiceItem(BaseModel):
    code: str
    name: str
    shortName: str
    service: str
    online: bool


class ServicePreferenceUpdate(BaseModel):
    enabled_services: list[str]  # e.g. ["ЯМ", "SP", "SC", "YT"] or service names
