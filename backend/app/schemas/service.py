from pydantic import BaseModel


class ServiceStatusRead(BaseModel):
    code: str
    name: str
    shortName: str
    service: str
    online: bool
