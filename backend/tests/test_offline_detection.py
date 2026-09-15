import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.models.node import Node
from backend.app.services.heartbeat_service import HeartbeatService
from backend.app.core.config import settings
from backend.tests.conftest import TestingSessionLocal, mock_redis_instance


@pytest.mark.asyncio
async def test_offline_detection_transitions(client: AsyncClient):
    # Register 3 nodes
    reg1 = await client.post(
        "/api/v1/nodes/register",
        json={"platform": "linux", "sdk_version": "1.0.0", "device_name": "node-fresh"},
    )
    reg2 = await client.post(
        "/api/v1/nodes/register",
        json={"platform": "linux", "sdk_version": "1.0.0", "device_name": "node-stale"},
    )
    reg3 = await client.post(
        "/api/v1/nodes/register",
        json={"platform": "linux", "sdk_version": "1.0.0", "device_name": "node-offline"},
    )

    node1_id = reg1.json()["node_id"]
    node2_id = reg2.json()["node_id"]
    node3_id = reg3.json()["node_id"]

    now = datetime.now(timezone.utc)

    # Adjust last_heartbeat_at in DB directly to simulate passage of time
    async with TestingSessionLocal() as session:
        # node1: fresh (10s ago)
        res1 = await session.execute(select(Node).where(Node.node_id == node1_id))
        n1 = res1.scalar_one()
        n1.status = "ONLINE"
        n1.last_heartbeat_at = now - timedelta(seconds=10)

        # node2: stale (100s ago > STALE_AFTER_SECONDS(90))
        res2 = await session.execute(select(Node).where(Node.node_id == node2_id))
        n2 = res2.scalar_one()
        n2.status = "ONLINE"
        n2.last_heartbeat_at = now - timedelta(seconds=settings.STALE_AFTER_SECONDS + 10)

        # node3: offline (200s ago > OFFLINE_AFTER_SECONDS(180))
        res3 = await session.execute(select(Node).where(Node.node_id == node3_id))
        n3 = res3.scalar_one()
        n3.status = "ONLINE"
        n3.last_heartbeat_at = now - timedelta(seconds=settings.OFFLINE_AFTER_SECONDS + 10)

        await session.commit()

        # Run offline detection check
        transitions = await HeartbeatService.check_and_update_offline_nodes(session, mock_redis_instance)
        assert transitions["stale"] == 1
        assert transitions["offline"] == 1

        # Re-query and verify statuses
        res1 = await session.execute(select(Node).where(Node.node_id == node1_id))
        assert res1.scalar_one().status == "ONLINE"

        res2 = await session.execute(select(Node).where(Node.node_id == node2_id))
        assert res2.scalar_one().status == "STALE"

        res3 = await session.execute(select(Node).where(Node.node_id == node3_id))
        assert res3.scalar_one().status == "OFFLINE"

    # Node 3 is OFFLINE: restoring valid authenticated heartbeat recovers it to ONLINE
    token3 = reg3.json()["token"]
    hb3_res = await client.post(
        f"/api/v1/nodes/{node3_id}/heartbeat",
        headers={"Authorization": f"Bearer {token3}"},
        json={"sdk_version": "1.0.0"},
    )
    assert hb3_res.status_code == 200
    assert hb3_res.json()["status"] == "ONLINE"

    # Verify node 3 is back to ONLINE in DB
    async with TestingSessionLocal() as session:
        res3_rec = await session.execute(select(Node).where(Node.node_id == node3_id))
        assert res3_rec.scalar_one().status == "ONLINE"


@pytest.mark.asyncio
async def test_registering_node_timeout_and_recovery(client: AsyncClient):
    reg = await client.post(
        "/api/v1/nodes/register",
        json={"platform": "linux", "sdk_version": "1.0.0", "device_name": "node-abandoned"},
    )
    node_id = reg.json()["node_id"]
    token = reg.json()["token"]
    now = datetime.now(timezone.utc)

    async with TestingSessionLocal() as session:
        res = await session.execute(select(Node).where(Node.node_id == node_id))
        node = res.scalar_one()
        assert node.status == "REGISTERING"
        # Simulate registration created 200s ago without any heartbeat
        node.created_at = now - timedelta(seconds=settings.OFFLINE_AFTER_SECONDS + 10)
        await session.commit()

        transitions = await HeartbeatService.check_and_update_offline_nodes(session, mock_redis_instance)
        assert transitions["offline"] == 1

        res2 = await session.execute(select(Node).where(Node.node_id == node_id))
        assert res2.scalar_one().status == "OFFLINE"

    # OFFLINE node can still recover to ONLINE when it sends its first heartbeat
    hb_res = await client.post(
        f"/api/v1/nodes/{node_id}/heartbeat",
        headers={"Authorization": f"Bearer {token}"},
        json={"sdk_version": "1.0.0"},
    )
    assert hb_res.status_code == 200
    assert hb_res.json()["status"] == "ONLINE"
