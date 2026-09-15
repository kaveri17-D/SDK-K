import logging
from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import redis.asyncio as aioredis

from backend.app.models.node import Node
from backend.app.schemas.node import NodeRegisterRequest, NetworkInfoUpdateRequest
from backend.app.core.security import generate_node_id, generate_node_token, hash_node_token

logger = logging.getLogger("clipper-x.service.node")


class NodeService:
    @staticmethod
    async def register_node(
        db: AsyncSession,
        redis_client: Optional[aioredis.Redis],
        data: NodeRegisterRequest,
    ) -> Tuple[Node, str]:
        """
        Registers a new node, generates its unique node_id and high-entropy secret token,
        persists the hashed token, sets initial status to ONLINE, and primes Redis.
        """
        # Generate a unique node ID (retrying if collision occurs)
        while True:
            candidate_id = generate_node_id()
            existing = await db.execute(select(Node).where(Node.node_id == candidate_id))
            if not existing.scalar_one_or_none():
                break

        raw_token = generate_node_token()
        token_hash = hash_node_token(raw_token)
        now = datetime.now(timezone.utc)

        node = Node(
            node_id=candidate_id,
            token_hash=token_hash,
            owner_id=data.owner_id,
            platform=data.platform,
            sdk_version=data.sdk_version,
            device_name=data.device_name,
            status="REGISTERING",
            health_status="HEALTHY",
            capabilities=data.capabilities,
            last_heartbeat_at=None,
        )

        db.add(node)
        await db.commit()
        await db.refresh(node)

        # Prime Redis runtime cache
        if redis_client:
            try:
                from backend.app.services.heartbeat_service import HeartbeatService
                await HeartbeatService.update_redis_runtime(
                    redis_client=redis_client,
                    node_id=node.node_id,
                    status="REGISTERING",
                    health={"network": True},
                    sdk_version=node.sdk_version,
                    timestamp=now.isoformat(),
                )
            except Exception as e:
                logger.warning(f"Failed to prime Redis for node {node.node_id}: {e}")

        logger.info(f"Registered node: node_id={node.node_id} platform={node.platform} status=REGISTERING")
        return node, raw_token

    @staticmethod
    async def get_node(db: AsyncSession, node_id: str) -> Optional[Node]:
        query = select(Node).where(Node.node_id == node_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_nodes(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        status_filter: Optional[str] = None,
    ) -> Tuple[List[Node], int]:
        query = select(Node)
        count_query = select(func.count()).select_from(Node)

        if status_filter:
            query = query.where(Node.status == status_filter)
            count_query = count_query.where(Node.status == status_filter)

        query = query.order_by(Node.created_at.desc()).offset(skip).limit(limit)

        items_res = await db.execute(query)
        count_res = await db.execute(count_query)

        items = list(items_res.scalars().all())
        total = count_res.scalar_one()

        return items, total

    @staticmethod
    async def update_network_info(
        db: AsyncSession,
        node: Node,
        data: NetworkInfoUpdateRequest,
    ) -> Node:
        if data.observed_public_ip is not None:
            node.observed_public_ip = data.observed_public_ip
        if data.download_mbps is not None:
            node.download_mbps = data.download_mbps
        if data.upload_mbps is not None:
            node.upload_mbps = data.upload_mbps

        node.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(node)

        logger.info(
            f"Updated network info for node {node.node_id}: ip={node.observed_public_ip} "
            f"down={node.download_mbps}Mbps up={node.upload_mbps}Mbps"
        )
        return node
