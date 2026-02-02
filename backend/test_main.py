# backend/test_main.py
import pytest
import respx
from httpx import Response, AsyncClient, ASGITransport
from main import app, get_ai_detection, get_fact_check

pytestmark = pytest.mark.asyncio

# --- MOCK DATA ---
WINSTON_MOCK_SUCCESS = {"score": 20}  # 20% human = 80% AI
GOOGLE_MOCK_SUCCESS = {
    "claims": [
        {
            "text": "The earth is flat.",
            "claimReview": [{"textualRating": "False", "publisher": {"name": "NASA"}}]
        }
    ]
}

# --- UNIT TESTS (Adapters & Logic) ---

@respx.mock
async def test_get_ai_detection_success():
    """Tests if the Winston AI response is correctly converted to AI Likelihood."""
    # Mock the Winston API call
    respx.post("https://api.gowinston.ai/v2/ai-content-detection").mock(
        return_value=Response(200, json=WINSTON_MOCK_SUCCESS)
    )
    
    result = await get_ai_detection("Sample text for testing")
    # 100 - 20 (human score) = 80 / 100 = 0.8 AI Likelihood
    assert result["score"] == 0.8

@respx.mock
async def test_get_fact_check_success():
    """Tests if the Google Fact Check JSON is parsed into our internal format."""
    respx.get("https://factchecktools.googleapis.com/v1alpha1/claims:search").mock(
        return_value=Response(200, json=GOOGLE_MOCK_SUCCESS)
    )
    
    result = await get_fact_check("The earth is flat")
    assert len(result) == 1
    assert result[0]["rating"] == "False"
    assert result[0]["source"] == "NASA"

# --- INTEGRATION TESTS (API Endpoints) ---

@respx.mock
async def test_analyze_endpoint_full_flow():
    """
    Tests the full /analyze route.
    Ensures that when both external APIs succeed, the backend returns a 200.
    """
    # Setup mocks for both external services
    respx.post("https://api.gowinston.ai/v2/ai-content-detection").mock(
        return_value=Response(200, json=WINSTON_MOCK_SUCCESS)
    )
    respx.get("https://factchecktools.googleapis.com/v1alpha1/claims:search").mock(
        return_value=Response(200, json=GOOGLE_MOCK_SUCCESS)
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/analyze", json={"text": "This is a long enough test string."})
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "ai_score" in data
    assert len(data["claims"]) > 0

async def test_analyze_too_short():
    """Ensures the API rejects text that is too short (Error Handling)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/analyze", json={"text": "Too short"})
    
    assert response.status_code == 400
    assert "Text is too short" in response.json()["detail"]