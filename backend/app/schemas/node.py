from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CapabilitiesSchema(BaseModel):
    network: bool = True
    bandwidth_test: bool = True
    heartbeat: bool = True

    model_config = ConfigDict(extra="allow")


class NodeRegisterRequest(BaseModel):
    platform: str = Field(..., min_length=1, max_length=32, examples=["linux", "windows", "darwin"])
    sdk_version: str = Field(..., min_length=1, max_length=32, examples=["1.0.0"])
    device_name: Optional[str] = Field(default=None, max_length=128, examples=["demo-laptop"])
    capabilities: Dict[str, Any] = Field(
        default_factory=lambda: {"network": True, "bandwidth_test": True, "heartbeat": True}
    )
    owner_id: Optional[str] = Field(default=None, max_length=64)


class NodeRegisterResponse(BaseModel):
    node_id: str
    token: str
    status: str
    platform: str
    sdk_version: str


class HeartbeatRequest(BaseModel):
    sdk_version: str = Field(..., min_length=1, max_length=32)
    timestamp: Optional[str] = None
    health: Optional[Dict[str, Any]] = None


class HeartbeatResponse(BaseModel):
    status: str
    acknowledged_at: str
    node_id: str


class NetworkInfoUpdateRequest(BaseModel):
    observed_public_ip: Optional[str] = Field(default=None, max_length=64)
    download_mbps: Optional[float] = Field(default=None, ge=0)
    upload_mbps: Optional[float] = Field(default=None, ge=0)


class NodeResponse(BaseModel):
    id: str
    node_id: str
    owner_id: Optional[str] = None
    platform: str
    sdk_version: str
    device_name: Optional[str] = None
    status: str
    health_status: str
    capabilities: Dict[str, Any]
    observed_public_ip: Optional[str] = None
    download_mbps: Optional[float] = None
    upload_mbps: Optional[float] = None
    last_heartbeat_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NodeListResponse(BaseModel):
    items: List[NodeResponse]
    total: int


class PublicIPResponse(BaseModel):
    ip: str
    observed_at: str


class UploadSpeedTestResponse(BaseModel):
    bytes_received: int
    duration_ms: float
    upload_mbps: float
    message: str = "Observed bandwidth to Clipper-X test server"
