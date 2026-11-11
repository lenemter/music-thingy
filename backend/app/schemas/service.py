from pydantic import BaseModel


class ServiceStatusRead(BaseModel):
    code: str
    name: str
    shortName: str
    service: str
    online: bool


class ServiceConnectionStatus(BaseModel):
    service: str
    code: str
    name: str
    connected: bool
    is_active: bool
    account_name: str | None = None
    account_id: str | None = None


class ConnectServiceRequest(BaseModel):
    token: str | None = None
    refresh_token: str | None = None
    auth_json: str | None = None
    user_agent: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


class ToggleServiceRequest(BaseModel):
    is_active: bool


class YouTubeDeviceCodeResponse(BaseModel):
    device_code: str
    user_code: str
    verification_url: str
    expires_in: int
    interval: int


class YouTubePollTokenRequest(BaseModel):
    device_code: str
    client_id: str | None = None
    client_secret: str | None = None


class YandexPollTokenRequest(BaseModel):
    device_code: str


class VkLoginRequest(BaseModel):
    login: str
    password: str
    code: str | None = None
