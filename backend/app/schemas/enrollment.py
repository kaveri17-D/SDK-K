from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class CreateInviteRequest(BaseModel):
    ttl_seconds: Optional[int] = Field(default=900, ge=60, le=86400, description="Ticket expiry in seconds (default 15 mins)")


class CreateInviteResponse(BaseModel):
    enrollment_token: str
    join_url: str
    expires_in_seconds: int


class ClaimInviteRequest(BaseModel):
    enrollment_token: str = Field(..., min_length=16, description="One-time enrollment ticket")
    platform: str = Field(..., min_length=1, max_length=32, examples=["android", "ios", "linux", "windows", "darwin"])
    sdk_version: str = Field(default="1.0.0", min_length=1, max_length=32)
    device_name: Optional[str] = Field(default=None, max_length=128)
    capabilities: Dict[str, Any] = Field(
        default_factory=lambda: {"network": True, "bandwidth_test": True, "heartbeat": True}
    )


class ClaimInviteResponse(BaseModel):
    node_id: str
    token: str
    status: str
    platform: str
    sdk_version: str
