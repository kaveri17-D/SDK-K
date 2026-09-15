import logging
from typing import Optional
from fastapi import APIRouter, Request, Query, status
from backend.app.schemas.node import PublicIPResponse, UploadSpeedTestResponse
from backend.app.services.ip_service import IPService
from backend.app.services.bandwidth_service import BandwidthService

logger = logging.getLogger("clipper-x.api.network")

router = APIRouter(prefix="/network", tags=["Network Telemetry"])


@router.get(
    "/ip",
    response_model=PublicIPResponse,
    summary="Get observed public egress IP",
)
async def get_observed_ip(request: Request):
    """
    Returns the public egress IP as observed by the Clipper-X backend.
    Enforces trusted reverse-proxy verification before accepting X-Forwarded-For.
    """
    data = IPService.get_ip_response(request)
    return PublicIPResponse(**data)


@router.get(
    "/speed-test",
    summary="Controlled bandwidth measurement download payload",
)
async def download_speed_test(
    size_mb: Optional[int] = Query(
        default=None,
        description="Payload size in MB (capped at configured maximum)",
    ),
):
    """
    Downloads a controlled payload stream of known size to measure download bandwidth.
    """
    return BandwidthService.create_download_response(requested_mb=size_mb)


@router.post(
    "/speed-test/upload",
    response_model=UploadSpeedTestResponse,
    summary="Controlled bandwidth measurement upload endpoint",
)
async def upload_speed_test(request: Request):
    """
    Measures upload bandwidth to Clipper-X test server by streaming payload.
    Enforces payload size limits.
    """
    result = await BandwidthService.process_upload_test(request)
    return UploadSpeedTestResponse(**result)
