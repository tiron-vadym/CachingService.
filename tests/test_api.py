import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Caching Microservice" in response.json().get("service", "")


@pytest.mark.asyncio
async def test_create_and_read_payload_sample_flow(client: AsyncClient):
    payload_input = {
        "list_1": ["first string", "second string", "third string"],
        "list_2": ["other string", "another string", "last string"],
    }

    # 1. POST /payload
    create_resp = await client.post("/payload", json=payload_input)
    assert create_resp.status_code == 201
    create_data = create_resp.json()
    assert "id" in create_data
    assert create_data["message"] == "Payload generated and stored successfully"
    payload_id = create_data["id"]

    # 2. GET /payload/{id}
    read_resp = await client.get(f"/payload/{payload_id}")
    assert read_resp.status_code == 200
    read_data = read_resp.json()
    assert "output" in read_data
    expected_output = (
        "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
    )
    assert read_data["output"] == expected_output


@pytest.mark.asyncio
async def test_reuse_payload_identifier(client: AsyncClient):
    payload_input = {
        "list_1": ["apple", "cherry"],
        "list_2": ["banana", "date"],
    }

    # First request
    resp1 = await client.post("/payload", json=payload_input)
    assert resp1.status_code == 201
    id1 = resp1.json()["id"]

    # Second identical request
    resp2 = await client.post("/payload", json=payload_input)
    assert resp2.status_code == 201
    id2 = resp2.json()["id"]
    msg2 = resp2.json()["message"]

    assert id1 == id2
    assert "reused existing identifier" in msg2


@pytest.mark.asyncio
async def test_create_payload_unequal_lengths(client: AsyncClient):
    payload_input = {
        "list_1": ["one", "two"],
        "list_2": ["three"],
    }

    resp = await client.post("/payload", json=payload_input)
    assert resp.status_code == 422
    assert "must have the exact same length" in resp.text


@pytest.mark.asyncio
async def test_create_payload_invalid_structure(client: AsyncClient):
    resp = await client.post("/payload", json={"invalid": "structure"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_read_payload_not_found(client: AsyncClient):
    resp = await client.get("/payload/non-existent-uuid-12345")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
