import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_observed_ip_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/network/ip")
    assert response.status_code == 200
    data = response.json()
    assert "ip" in data
    assert "observed_at" in data


@pytest.mark.asyncio
async def test_untrusted_proxy_spoofing_rejected(client: AsyncClient, monkeypatch):
    from backend.app.core.config import settings

    # When client connects directly and is NOT in TRUSTED_PROXIES:
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "10.0.0.1")
    response = await client.get(
        "/api/v1/network/ip",
        headers={"X-Forwarded-For": "203.0.113.199"},
    )
    assert response.status_code == 200
    data = response.json()
    # Spoofed IP must NOT be accepted since client is not in TRUSTED_PROXIES
    assert data["ip"] != "203.0.113.199"

    # Conversely, when proxy IS trusted:
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "127.0.0.1")
    trusted_res = await client.get(
        "/api/v1/network/ip",
        headers={"X-Forwarded-For": "203.0.113.199"},
    )
    assert trusted_res.status_code == 200
    assert trusted_res.json()["ip"] == "203.0.113.199"


@pytest.mark.asyncio
async def test_speed_test_download(client: AsyncClient):
    response = await client.get("/api/v1/network/speed-test?size_mb=1")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-length"] == str(1 * 1024 * 1024)
    content = response.content
    assert len(content) == 1 * 1024 * 1024


@pytest.mark.asyncio
async def test_speed_test_oversized_rejected(client: AsyncClient):
    # Attempt to request oversized test payload beyond 50MB
    response = await client.get("/api/v1/network/speed-test?size_mb=999")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_speed_test_upload(client: AsyncClient):
    payload = b"\x00" * (512 * 1024)  # 512 KB
    response = await client.post(
        "/api/v1/network/speed-test/upload",
        content=payload,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["bytes_received"] == 512 * 1024
    assert data["upload_mbps"] >= 0
    assert "Observed bandwidth to Clipper-X test server" in data["message"]


@pytest.mark.asyncio
async def test_network_info_update(client: AsyncClient):
    reg = await client.post(
        "/api/v1/nodes/register",
        json={"platform": "linux", "sdk_version": "1.0.0", "device_name": "net-node"},
    )
    node_id = reg.json()["node_id"]
    token = reg.json()["token"]

    update_payload = {
        "observed_public_ip": "198.51.100.42",
        "download_mbps": 85.5,
        "upload_mbps": 22.3,
    }

    response = await client.post(
        f"/api/v1/nodes/{node_id}/network-info",
        headers={"Authorization": f"Bearer {token}"},
        json=update_payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["observed_public_ip"] == "198.51.100.42"
    assert data["download_mbps"] == 85.5
    assert data["upload_mbps"] == 22.3
