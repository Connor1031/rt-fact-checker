# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AEGIS")

# Enable CORS so React frontend can talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO, replace with frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
# Winston AI uses a Bearer Token for Authentication
WINSTONAI_API_KEY = os.getenv("WINSTONAI_API_KEY", "") #this is for copyleaks/winstonai, my have to switch if I need to test more while being out of free uses 
# Google Fact Check Tools uses a query parameter 'key'
FACT_CHECK_API_KEY = os.getenv("FACT_CHECK_API_KEY", "") # Currently google fact check tools api, need to contact factiverse for api key, If i am able to get claimbuster to work, use that because it is more reliable and better

# --- DATA MODELS ---
class AnalysisRequest(BaseModel):
    text: str

class AnalysisResponse(BaseModel):
    ai_score: float  # Percentage of AI-generated content
    claims: list     # List of identified claims or fact-checks
    status: str

# --- API SERVICES ---

async def get_ai_detection(text: str):
    """
    Calling API to detect AI-generated text.
    """
    if not WINSTONAI_API_KEY:
        return {"error": "API Key missing", "score": 0}
    
    # Winston AI requires at least 300-600 characters for reliability
    url = "https://api.gowinston.ai/v2/ai-content-detection"
    headers = {
        "Authorization": f"Bearer {WINSTONAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"text": text, "sentences": True}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                # Winston's 'score' is a Human probability (e.g., 90 = 90% Human)
                # convert to AI score: (100 - score) / 100
                human_score = data.get("score", 100)
                ai_likelihood = (100 - human_score) / 100
                return {"score": ai_likelihood}
            else:
                return {"error": f"Winston AI Error: {response.status_code}", "score": 0}
    except Exception as e:
        return {"error": str(e), "score": 0}

async def get_fact_check(text: str):
    """
    Calling Fact-Checking API (Google Fact Check).
    """
    if not FACT_CHECK_API_KEY:
        return [{"claim": "API Key missing", "rating": "N/A"}]

    # We use the first 100 characters as a search query for the MVP
    search_query = text[:100]
    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    params = {
        "query": search_query,
        "key": FACT_CHECK_API_KEY
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                claims_list = []
                # Google returns a 'claims' list. We extract the text and the rating.
                for item in data.get("claims", []):
                    # A claim can have multiple reviews; we'll take the first one
                    reviews = item.get("claimReview", [])
                    rating = reviews[0].get("textualRating", "Unknown") if reviews else "No Rating"
                    publisher = reviews[0].get("publisher", {}).get("name", "Unknown Source")
                    
                    claims_list.append({
                        "claim": item.get("text", "N/A"),
                        "rating": rating,
                        "source": publisher
                    })
                return claims_list[:5] # Return top 5 results
            else:
                return [{"claim": f"Google API Error: {response.status_code}", "rating": "Error"}]
    except Exception as e:
        return [{"claim": f"Connection Error: {str(e)}", "rating": "Error"}]

# --- ROUTES ---

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(request: AnalysisRequest):
    if not request.text or len(request.text) < 10:
        raise HTTPException(status_code=400, detail="Text is too short for analysis.")

    # Run both API calls in parallel to save time
    ai_task = asyncio.create_task(get_ai_detection(request.text))
    fact_task = asyncio.create_task(get_fact_check(request.text))

    ai_result, fact_result = await asyncio.gather(ai_task, fact_task)

    return {
        "ai_score": ai_result.get("score", 0),
        "claims": fact_result,
        "status": "success"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)