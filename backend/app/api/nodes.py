import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from backend.app.db.session import get_db, get_redis
from backend.app.schemas.node import (
    NodeRegisterRequest,
    NodeRegisterResponse,
    HeartbeatRequest,
    HeartbeatResponse,
    NetworkInfoUpdateRequest,
    NodeResponse,
    NodeListResponse,
)
from backend.app.models.node import Node
from backend.app.services.node_service import NodeService
from backend.app.services.heartbeat_service import HeartbeatService
from backend.app.core.security import get_current_authenticated_node, verify_node_ownership

logger = logging.getLogger("clipper-x.api.nodes")

router = APIRouter(prefix="/nodes", tags=["Nodes"])


@router.post(
    "/register",
    response_model=NodeRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Clipper-X node",
)
async def register_node(
    data: NodeRegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """
    Registers a participating device:
    1. Validates request
    2. Generates a unique NODE_ID and secret credential
    3. Persists record in PostgreSQL
    4. Primes Redis runtime cache
    5. Returns NODE_ID and Bearer token
    """
    node, raw_token = await NodeService.register_node(db, redis_client, data)
    return NodeRegisterResponse(
        node_id=node.node_id,
        token=raw_token,
        status=node.status,
        platform=node.platform,
        sdk_version=node.sdk_version,
    )


@router.post(
    "/{node_id}/heartbeat",
    response_model=HeartbeatResponse,
    summary="Send node heartbeat ping",
)
async def node_heartbeat(
    node_id: str,
    payload: HeartbeatRequest,
    current_node: Node = Depends(get_current_authenticated_node),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """
    Heartbeat ping:
    1. Authenticates Bearer token
    2. Verifies node ownership (cannot ping another node)
    3. Updates last_heartbeat_at to UTC now
    4. Sets status to ONLINE
    5. Updates Redis runtime cache
    """
    verify_node_ownership(node_id, current_node)

    updated_node = await HeartbeatService.process_heartbeat(
        db=db,
        redis_client=redis_client,
        node=current_node,
        sdk_version=payload.sdk_version,
        timestamp=payload.timestamp,
        health=payload.health,
    )

    return HeartbeatResponse(
        status=updated_node.status,
        acknowledged_at=datetime.now(timezone.utc).isoformat(),
        node_id=updated_node.node_id,
    )


@router.post(
    "/{node_id}/network-info",
    response_model=NodeResponse,
    summary="Report observed network telemetry",
)
async def update_network_info(
    node_id: str,
    payload: NetworkInfoUpdateRequest,
    current_node: Node = Depends(get_current_authenticated_node),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticated update of observed public IP and bandwidth measurements.
    """
    verify_node_ownership(node_id, current_node)

    updated_node = await NodeService.update_network_info(
        db=db,
        node=current_node,
        data=payload,
    )
    return NodeResponse(**updated_node.to_dict())


@router.get(
    "",
    response_model=NodeListResponse,
    summary="List registered nodes",
)
async def list_nodes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns registered nodes with pagination and optional status filter.
    """
    items, total = await NodeService.list_nodes(
        db=db,
        skip=skip,
        limit=limit,
        status_filter=status,
    )
    return NodeListResponse(
        items=[NodeResponse(**node.to_dict()) for node in items],
        total=total,
    )


@router.get(
    "/{node_id}",
    response_model=NodeResponse,
    summary="Get node details by NODE_ID",
)
async def get_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns complete metadata for a registered node.
    """
    node = await NodeService.get_node(db=db, node_id=node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{node_id}' not found",
        )
    return NodeResponse(**node.to_dict())
