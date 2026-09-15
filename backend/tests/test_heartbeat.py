import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_heartbeat_updates_timestamp(client: AsyncClient):
    reg = await client.post(
        "/api/v1/nodes/register",
        json={"platform": "linux", "sdk_version": "1.0.0", "device_name": "hb-node"},
    )
    data = reg.json()
    node_id = data["node_id"]
    token = data["token"]

    # Initial node check
    initial_node = await client.get(f"/api/v1/nodes/{node_id}")
    assert initial_node.json()["status"] == "REGISTERING"
    assert initial_node.json()["last_heartbeat_at"] is None

    # Send heartbeat
    hb_res = await client.post(
        f"/api/v1/nodes/{node_id}/heartbeat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "sdk_version": "1.0.1",
            "timestamp": "2026-09-15T12:00:00Z",
            "health": {"network": True},
        },
    )
    assert hb_res.status_code == 200
    hb_data = hb_res.json()
    assert hb_data["status"] == "ONLINE"
    assert hb_data["node_id"] == node_id

    # Verify node record updated
    updated_node = await client.get(f"/api/v1/nodes/{node_id}")
    updated_info = updated_node.json()
    assert updated_info["status"] == "ONLINE"
    assert updated_info["sdk_version"] == "1.0.1"
    assert updated_info["health_status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_invalid_heartbeat_payload(client: AsyncClient):
    reg = await client.post(
        "/api/v1/nodes/register",
        json={"platform": "linux", "sdk_version": "1.0.0", "device_name": "hb-node-2"},
    )
    data = reg.json()
    node_id = data["node_id"]
    token = data["token"]

    # Missing required sdk_version
    hb_res = await client.post(
        f"/api/v1/nodes/{node_id}/heartbeat",
        headers={"Authorization": f"Bearer {token}"},
        json={"timestamp": "2026-09-15T12:00:00Z"},
    )
    assert hb_res.status_code == 422
