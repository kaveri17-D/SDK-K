import logging
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from backend.app.db.session import get_db, get_redis
from backend.app.schemas.enrollment import (
    CreateInviteRequest,
    CreateInviteResponse,
    ClaimInviteRequest,
    ClaimInviteResponse,
)
from backend.app.services.enrollment_service import EnrollmentService

logger = logging.getLogger("clipper-x.api.enrollment")

router = APIRouter(prefix="/enrollment", tags=["Enrollment"])


@router.post(
    "/invite",
    response_model=CreateInviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create short-lived one-time enrollment ticket & join URL",
)
async def create_invite(
    request: Request,
    payload: CreateInviteRequest = CreateInviteRequest(),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """
    Generates a secure one-time enrollment ticket for frictionless onboarding.
    Never exposes permanent node secrets in URLs.
    """
    token = await EnrollmentService.create_ticket(
        redis_client=redis_client,
        ttl_seconds=payload.ttl_seconds,
    )

    base_url = str(request.base_url).rstrip("/")
    join_url = f"{base_url}/join?token={token}"

    return CreateInviteResponse(
        enrollment_token=token,
        join_url=join_url,
        expires_in_seconds=payload.ttl_seconds,
    )


@router.post(
    "/claim",
    response_model=ClaimInviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Claim one-time enrollment ticket to register device",
)
async def claim_invite(
    payload: ClaimInviteRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """
    Consumes a single-use enrollment ticket and registers the device.
    Initial status is set to REGISTERING. First valid heartbeat transitions to ONLINE.
    """
    node, raw_token = await EnrollmentService.claim_ticket(
        db=db,
        redis_client=redis_client,
        claim_data=payload,
    )

    return ClaimInviteResponse(
        node_id=node.node_id,
        token=raw_token,
        status=node.status,
        platform=node.platform,
        sdk_version=node.sdk_version,
    )


@router.get(
    "/verify/{token}",
    summary="Check if enrollment ticket is still valid",
)
async def verify_invite(
    token: str,
    redis_client: aioredis.Redis = Depends(get_redis),
):
    valid = await EnrollmentService.is_ticket_valid(redis_client, token)
    return {"token": token, "valid": valid}
