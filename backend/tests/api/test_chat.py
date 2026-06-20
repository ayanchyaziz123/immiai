import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "model_ready" in data
    assert "rag_ready" in data


@pytest.mark.asyncio
async def test_chat_returns_answer(client):
    response = await client.post(
        "/api/v1/chat/",
        json={"question": "What is the H-1B visa?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 10
    assert "conversation_id" in data
    assert "model_version" in data


@pytest.mark.asyncio
async def test_chat_with_visa_type(client):
    response = await client.post(
        "/api/v1/chat/",
        json={
            "question": "What documents do I need?",
            "visa_type": "H-1B",
            "language": "English",
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_conversations(client):
    response = await client.get("/api/v1/chat/conversations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_conversation_not_found(client):
    response = await client.get("/api/v1/chat/conversations/nonexistent-id")
    assert response.status_code == 404
