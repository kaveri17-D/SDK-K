import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_enrollment_lifecycle(client: AsyncClient):
    # 1. Create one-time enrollment ticket
    res_invite = await client.post("/api/v1/enrollment/invite", json={"ttl_seconds": 300})
    assert res_invite.status_code == 201
    invite_data = res_invite.json()
    token = invite_data["enrollment_token"]
    assert token.startswith("cne_")
    assert "join?token=" in invite_data["join_url"]

    # 2. Verify ticket is valid
    res_verify = await client.get(f"/api/v1/enrollment/verify/{token}")
    assert res_verify.status_code == 200
    assert res_verify.json()["valid"] is True

    # 3. Access join page
    res_join_page = await client.get(f"/join?token={token}")
    assert res_join_page.status_code == 200
    assert "Clipper-X Node Network" in res_join_page.text
    assert "Connect Device" in res_join_page.text

    # 4. Claim ticket to enroll device
    res_claim = await client.post(
        "/api/v1/enrollment/claim",
        json={
            "enrollment_token": token,
            "platform": "android",
            "device_name": "Pixel 8 Pro",
            "sdk_version": "1.0.0",
        },
    )
    assert res_claim.status_code == 201
    claim_data = res_claim.json()
    assert claim_data["node_id"].startswith("node_")
    assert claim_data["token"].startswith("cnx_tok_")
    assert claim_data["status"] == "REGISTERING"
    assert claim_data["platform"] == "android"

    # 5. Node record in DB starts as REGISTERING
    lookup = await client.get(f"/api/v1/nodes/{claim_data['node_id']}")
    assert lookup.status_code == 200
    assert lookup.json()["status"] == "REGISTERING"

    # 6. Reusing same ticket must fail (one-time use only)
    res_reuse = await client.post(
        "/api/v1/enrollment/claim",
        json={
            "enrollment_token": token,
            "platform": "android",
            "device_name": "Second Device",
        },
    )
    assert res_reuse.status_code == 400
    assert "already been used" in res_reuse.json()["detail"]

    # 7. Invalid ticket must fail
    res_invalid = await client.post(
        "/api/v1/enrollment/claim",
        json={
            "enrollment_token": "cne_fake_invalid_token_12345",
            "platform": "linux",
        },
    )
    assert res_invalid.status_code == 400


@pytest.mark.asyncio
async def test_first_heartbeat_after_enrollment(client: AsyncClient):
    # Enroll node
    res_invite = await client.post("/api/v1/enrollment/invite")
    token = res_invite.json()["enrollment_token"]

    res_claim = await client.post(
        "/api/v1/enrollment/claim",
        json={"enrollment_token": token, "platform": "ios", "device_name": "iPhone 15"},
    )
    node_id = res_claim.json()["node_id"]
    node_token = res_claim.json()["token"]

    # Verify status is REGISTERING
    node_before = await client.get(f"/api/v1/nodes/{node_id}")
    assert node_before.json()["status"] == "REGISTERING"

    # Send first heartbeat
    hb_res = await client.post(
        f"/api/v1/nodes/{node_id}/heartbeat",
        headers={"Authorization": f"Bearer {node_token}"},
        json={"sdk_version": "1.0.0"},
    )
    assert hb_res.status_code == 200
    assert hb_res.json()["status"] == "ONLINE"

    # Verify node is now ONLINE
    node_after = await client.get(f"/api/v1/nodes/{node_id}")
    assert node_after.json()["status"] == "ONLINE"
