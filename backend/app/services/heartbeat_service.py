import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as aioredis

from backend.app.models.node import Node
from backend.app.core.config import settings

logger = logging.getLogger("clipper-x.service.heartbeat")


class HeartbeatService:
    @staticmethod
    def get_redis_key(node_id: str) -> str:
        return f"node:heartbeat:{node_id}"

    @staticmethod
    async def update_redis_runtime(
        redis_client: aioredis.Redis,
        node_id: str,
        status: str,
        health: Optional[Dict[str, Any]],
        sdk_version: str,
        timestamp: str,
    ) -> None:
        """
        Stores ephemeral runtime state in Redis for fast access.
        Key pattern: node:heartbeat:{node_id}
        """
        key = HeartbeatService.get_redis_key(node_id)
        data = {
            "node_id": node_id,
            "last_seen": timestamp,
            "status": status,
            "health": json.dumps(health or {}),
            "sdk_version": sdk_version,
        }
        ttl = max(settings.OFFLINE_AFTER_SECONDS * 2, 300)
        await redis_client.hset(key, mapping=data)
        await redis_client.expire(key, ttl)

    @staticmethod
    async def get_redis_runtime(
        redis_client: aioredis.Redis,
        node_id: str,
    ) -> Optional[Dict[str, Any]]:
        key = HeartbeatService.get_redis_key(node_id)
        data = await redis_client.hgetall(key)
        if not data:
            return None
        if "health" in data:
            try:
                data["health"] = json.loads(data["health"])
            except Exception:
                pass
        return data

    @staticmethod
    async def process_heartbeat(
        db: AsyncSession,
        redis_client: Optional[aioredis.Redis],
        node: Node,
        sdk_version: str,
        timestamp: Optional[str] = None,
        health: Optional[Dict[str, Any]] = None,
    ) -> Node:
        """
        Records a heartbeat from an authenticated node.
        Updates DB and Redis runtime cache.
        """
        now = datetime.now(timezone.utc)
        node.last_heartbeat_at = now
        node.status = "ONLINE"
        node.sdk_version = sdk_version

        if health:
            # Example health evaluation
            is_healthy = health.get("network", True)
            node.health_status = "HEALTHY" if is_healthy else "DEGRADED"

        await db.commit()
        await db.refresh(node)

        # Update Redis runtime state
        if redis_client:
            try:
                await HeartbeatService.update_redis_runtime(
                    redis_client=redis_client,
                    node_id=node.node_id,
                    status=node.status,
                    health=health,
                    sdk_version=node.sdk_version,
                    timestamp=now.isoformat(),
                )
            except Exception as e:
                logger.warning(f"Failed to update Redis heartbeat for {node.node_id}: {e}")

        logger.info(f"Heartbeat received: node_id={node.node_id} status={node.status} health={node.health_status}")
        return node

    @staticmethod
    async def evaluate_node_status(
        last_heartbeat_at: Optional[datetime],
        current_status: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> str:
        """
        Determines whether a node should be REGISTERING, ONLINE, STALE, or OFFLINE
        based on the elapsed time since its last heartbeat (or registration).
        """
        now = datetime.now(timezone.utc)
        if not last_heartbeat_at:
            if current_status == "REGISTERING" and created_at:
                c_at = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
                elapsed = (now - c_at).total_seconds()
                if elapsed > settings.OFFLINE_AFTER_SECONDS:
                    return "OFFLINE"
                elif elapsed > settings.STALE_AFTER_SECONDS:
                    return "STALE"
                return "REGISTERING"
            return "OFFLINE"

        if last_heartbeat_at.tzinfo is None:
            last_heartbeat = last_heartbeat_at.replace(tzinfo=timezone.utc)
        else:
            last_heartbeat = last_heartbeat_at

        elapsed_seconds = (now - last_heartbeat).total_seconds()

        if elapsed_seconds <= settings.STALE_AFTER_SECONDS:
            return "ONLINE"
        elif elapsed_seconds <= settings.OFFLINE_AFTER_SECONDS:
            return "STALE"
        else:
            return "OFFLINE"

    @staticmethod
    async def check_and_update_offline_nodes(
        db: AsyncSession,
        redis_client: Optional[aioredis.Redis] = None,
    ) -> Dict[str, int]:
        """
        Evaluates all non-suspended nodes and transitions them to STALE or OFFLINE
        if their heartbeat thresholds have been exceeded.
        """
        now = datetime.now(timezone.utc)
        query = select(Node).where(Node.status.in_(["ONLINE", "STALE", "REGISTERING"]))
        result = await db.execute(query)
        nodes = list(result.scalars().all())

        transitions = {"stale": 0, "offline": 0, "unchanged": 0}

        for node in nodes:
            new_status = await HeartbeatService.evaluate_node_status(
                last_heartbeat_at=node.last_heartbeat_at,
                current_status=node.status,
                created_at=node.created_at,
            )

            if new_status != node.status:
                logger.info(
                    f"Transitioning node {node.node_id} from {node.status} to {new_status} "
                    f"(last heartbeat: {node.last_heartbeat_at})"
                )
                node.status = new_status
                if new_status == "OFFLINE":
                    transitions["offline"] += 1
                elif new_status == "STALE":
                    transitions["stale"] += 1

                # Sync state to Redis
                if redis_client:
                    try:
                        key = HeartbeatService.get_redis_key(node.node_id)
                        await redis_client.hset(key, "status", new_status)
                    except Exception as e:
                        logger.warning(f"Failed to update Redis status for {node.node_id}: {e}")
            else:
                transitions["unchanged"] += 1

        await db.commit()
        return transitions


async def run_offline_detection_worker(session_factory, redis_client_factory, stop_event: asyncio.Event):
    """
    Background worker task that runs periodically to detect stale and offline nodes.
    """
    logger.info("Starting background offline detection worker...")
    while not stop_event.is_set():
        try:
            async with session_factory() as session:
                redis_gen = redis_client_factory()
                redis_client = await anext(redis_gen)
                try:
                    await HeartbeatService.check_and_update_offline_nodes(session, redis_client)
                finally:
                    await redis_client.aclose()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in offline detection worker: {e}", exc_info=True)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.OFFLINE_CHECK_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass
    logger.info("Offline detection worker stopped.")
