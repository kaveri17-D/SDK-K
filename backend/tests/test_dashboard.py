import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_page_html(client: AsyncClient):
    response = await client.get("/dashboard")
    assert response.status_code == 200
    assert "Clipper-X Node Registry Dashboard" in response.text
    assert "LIVE POLLING" in response.text


@pytest.mark.asyncio
async def test_dashboard_stats_api(client: AsyncClient):
    # Register a test node
    reg_res = await client.post(
        "/api/v1/nodes/register",
        json={"platform": "linux", "sdk_version": "1.0.0", "device_name": "dash-test-node"}
    )
    assert reg_res.status_code == 201

    stats_res = await client.get("/api/v1/dashboard/stats")
    assert stats_res.status_code == 200
    data = stats_res.json()

    assert "total" in data
    assert "online" in data
    assert "stale" in data
    assert "offline" in data
    assert "registering" in data
    assert "nodes" in data
    assert data["total"] >= 1
    assert len(data["nodes"]) >= 1

    node_entry = next(n for n in data["nodes"] if n["node_id"] == reg_res.json()["node_id"])
    assert node_entry["platform"] == "linux"
    assert node_entry["status"] == "REGISTERING"
