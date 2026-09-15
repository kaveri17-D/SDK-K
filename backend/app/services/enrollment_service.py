import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from backend.app.models.node import Node
from backend.app.schemas.node import NodeRegisterRequest
from backend.app.schemas.enrollment import ClaimInviteRequest
from backend.app.services.node_service import NodeService

logger = logging.getLogger("clipper-x.service.enrollment")

# In-memory ticket fallback for test environments or Redis disconnections
_local_ticket_cache: dict = {}


class EnrollmentService:
    @staticmethod
    def _ticket_key(token: str) -> str:
        return f"enrollment:ticket:{token}"

    @classmethod
    async def create_ticket(
        cls,
        redis_client: Optional[aioredis.Redis],
        ttl_seconds: int = 900,
    ) -> str:
        token = f"cne_{secrets.token_urlsafe(24)}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)

        # Store in Redis
        if redis_client:
            try:
                key = cls._ticket_key(token)
                await redis_client.hset(key, mapping={
                    "created_at": now.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "claimed": "false",
                })
                await redis_client.expire(key, ttl_seconds)
            except Exception as e:
                logger.warning(f"Redis ticket store failed, using in-memory store: {e}")

        # Always mirror in in-memory fallback
        _local_ticket_cache[token] = {
            "created_at": now,
            "expires_at": expires_at,
            "claimed": False,
        }

        logger.info(f"Generated enrollment ticket: {token[:8]}... (valid for {ttl_seconds}s)")
        return token

    @classmethod
    async def is_ticket_valid(
        cls,
        redis_client: Optional[aioredis.Redis],
        token: str,
    ) -> bool:
        now = datetime.now(timezone.utc)

        # Check Redis first
        if redis_client:
            try:
                key = cls._ticket_key(token)
                data = await redis_client.hgetall(key)
                if data and data.get("claimed") == "false":
                    return True
            except Exception:
                pass

        # Check in-memory fallback
        entry = _local_ticket_cache.get(token)
        if entry:
            if not entry["claimed"] and entry["expires_at"] > now:
                return True

        return False

    @classmethod
    async def claim_ticket(
        cls,
        db: AsyncSession,
        redis_client: Optional[aioredis.Redis],
        claim_data: ClaimInviteRequest,
    ) -> Tuple[Node, str]:
        token = claim_data.enrollment_token
        now = datetime.now(timezone.utc)

        valid = False

        # Verify against Redis
        if redis_client:
            try:
                key = cls._ticket_key(token)
                data = await redis_client.hgetall(key)
                if data:
                    if data.get("claimed") == "true":
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Enrollment ticket has already been used",
                        )
                    valid = True
                    # Burn ticket atomically
                    await redis_client.hset(key, "claimed", "true")
                    await redis_client.expire(key, 60)  # Short grace period
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Error checking Redis ticket: {e}")

        # If not verified by Redis, check fallback
        if not valid:
            entry = _local_ticket_cache.get(token)
            if not entry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired enrollment ticket",
                )
            if entry["claimed"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Enrollment ticket has already been used",
                )
            if entry["expires_at"] <= now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Enrollment ticket has expired",
                )
            entry["claimed"] = True

        # Register the node using NodeService
        reg_request = NodeRegisterRequest(
            platform=claim_data.platform,
            sdk_version=claim_data.sdk_version,
            device_name=claim_data.device_name,
            capabilities=claim_data.capabilities,
        )

        node, raw_token = await NodeService.register_node(
            db=db,
            redis_client=redis_client,
            data=reg_request,
        )

        logger.info(f"Successfully claimed ticket {token[:8]}... for new node {node.node_id}")
        return node, raw_token
