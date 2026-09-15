import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_registration_success(client: AsyncClient):
    payload = {
        "platform": "linux",
        "sdk_version": "1.0.0",
        "device_name": "test-device-1",
        "capabilities": {
            "network": True,
            "bandwidth_test": True,
            "heartbeat": True,
        },
    }
    response = await client.post("/api/v1/nodes/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "node_id" in data
    assert data["node_id"].startswith("node_")
    assert "token" in data
    assert data["token"].startswith("cnx_tok_")
    assert data["status"] == "REGISTERING"
    assert data["platform"] == "linux"
    assert data["sdk_version"] == "1.0.0"

    # Node starts as REGISTERING with no heartbeat
    lookup = await client.get(f"/api/v1/nodes/{data['node_id']}")
    assert lookup.status_code == 200
    assert lookup.json()["status"] == "REGISTERING"
    assert lookup.json()["last_heartbeat_at"] is None

    # First valid authenticated heartbeat transitions node to ONLINE
    hb_res = await client.post(
        f"/api/v1/nodes/{data['node_id']}/heartbeat",
        headers={"Authorization": f"Bearer {data['token']}"},
        json={"sdk_version": "1.0.0"},
    )
    assert hb_res.status_code == 200
    assert hb_res.json()["status"] == "ONLINE"

    # Verify node is now ONLINE
    lookup2 = await client.get(f"/api/v1/nodes/{data['node_id']}")
    assert lookup2.json()["status"] == "ONLINE"
    assert lookup2.json()["last_heartbeat_at"] is not None


@pytest.mark.asyncio
async def test_duplicate_registration_different_ids(client: AsyncClient):
    payload = {
        "platform": "linux",
        "sdk_version": "1.0.0",
        "device_name": "duplicate-device",
    }
    res1 = await client.post("/api/v1/nodes/register", json=payload)
    res2 = await client.post("/api/v1/nodes/register", json=payload)

    assert res1.status_code == 201
    assert res2.status_code == 201
    data1 = res1.json()
    data2 = res2.json()

    assert data1["node_id"] != data2["node_id"]
    assert data1["token"] != data2["token"]


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient):
    # Missing Authorization header
    response = await client.post(
        "/api/v1/nodes/node_unknown/heartbeat",
        json={"sdk_version": "1.0.0"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_rejected(client: AsyncClient):
    # Invalid Bearer token
    response = await client.post(
        "/api/v1/nodes/node_unknown/heartbeat",
        headers={"Authorization": "Bearer cnx_tok_bogus_token_12345"},
        json={"sdk_version": "1.0.0"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_node_cannot_modify_another_node(client: AsyncClient):
    # Register Node A
    res_a = await client.post(
        "/api/v1/nodes/register",
        json={"platform": "linux", "sdk_version": "1.0.0", "device_name": "node-a"},
    )
    node_a = res_a.json()

    # Register Node B
    res_b = await client.post(
        "/api/v1/nodes/register",
        json={"platform": "linux", "sdk_version": "1.0.0", "device_name": "node-b"},
    )
    node_b = res_b.json()

    # Node A attempts to send heartbeat for Node B
    response = await client.post(
        f"/api/v1/nodes/{node_b['node_id']}/heartbeat",
        headers={"Authorization": f"Bearer {node_a['token']}"},
        json={"sdk_version": "1.0.0"},
    )
    assert response.status_code == 403
    assert "Unauthorized" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_and_lookup_nodes(client: AsyncClient):
    reg = await client.post(
        "/api/v1/nodes/register",
        json={"platform": "linux", "sdk_version": "1.0.0", "device_name": "lookup-node"},
    )
    node_id = reg.json()["node_id"]

    # Lookup node
    get_res = await client.get(f"/api/v1/nodes/{node_id}")
    assert get_res.status_code == 200
    assert get_res.json()["node_id"] == node_id
    assert get_res.json()["status"] == "REGISTERING"

    # List nodes
    list_res = await client.get("/api/v1/nodes")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(n["node_id"] == node_id for n in list_data["items"])
