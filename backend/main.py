# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import httpx
import asyncio
import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# --- DATA MODELS ---
class AnalysisRequest(BaseModel):
    text: Optional[str] = ""
    image_url: Optional[str] = None

class AnalysisResponse(BaseModel):
    ai_score: float  # Percentage of AI-generated content
    claims: list     # List of identified claims or fact-checks
    status: str

class SourceBreakdown(BaseModel):
    source_name: str = Field(description="Name of the website/organization")
    source_summary: str = Field(description="Brief description of exactly what this site reported")
    bias_report: str = Field(description="Objective assessment of the website's bias and reliability (e.g., 'Highly Reliable, neutral bias').")
    link: str = Field(description="Exact URL to the source. MUST be a valid https:// link.")

class FactCheckResult(BaseModel):
    claim: str = Field(description="The exact quote or specific claim extracted from the text.")
    rating: str = Field(description="MUST be one of: TRUE, FALSE, or UNCERTAIN")
    brief_description: str = Field(description="Concise, 2-3 sentence summary explaining what trusted sources state")
    sources: list[SourceBreakdown] = Field(description="List of trusted sources used to verify the claim")

class FactCheckList(BaseModel):
    results: list[FactCheckResult] = Field(description="A list of multiple fact-checked claims extracted from the text.")

# --- API SERVICES ---

async def get_ai_detection(text: str):
    """ Calls Winston API to detect AI-generated text. """
    if not WINSTONAI_API_KEY or not text or len(text) < 50:
        return {"score": 0} # Not enough text to analyze
    
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
                human_score = data.get("score", 100)
                ai_likelihood = (100 - human_score) / 100
                return {"score": ai_likelihood}
            else:
                return {"error": f"Winston AI Error", "score": 0}
    except Exception as e:
        return {"error": str(e), "score": 0}

async def get_fact_check(text: str, image_url: str = None):
    """
    Calls the custom Gemini Agent to extract and fact-check claims using a strict JSON schema.
    """
    system_prompt = """
    You are an expert, highly objective Real-Time Fact-Checking Agent. Your primary function is to 
    analyze provided text OR images (like screenshots of social media posts, news headlines, or memes), extract the core claims, and verify their accuracy by searching for information 
    across trusted, highly reputable websites (e.g., AP News, Reuters, established academic journals, or verified government data).
    
    Maintain a strictly neutral, journalistic tone. If a claim cannot be adequately verified by highly 
    trusted sources, you must rate it UNCERTAIN and explain the lack of available consensus. Ensure all 
    links are real, accurate, and directly relevant.

    CRITICAL INSTRUCTIONS:
    1. Extract 1-3 of the most prominent claims from the text.
    2. IF the image or text contains NO factual claims to verify (e.g., a regular photo with no text, or a pure opinion), you MUST output exactly one result with:
        - claim: "No verifiable claims detected."
        - rating: "UNCERTAIN"
        - brief_description: "The provided content does not contain specific, objective statements or text that can be fact-checked."
        - sources: []
    2. You MUST provide real, accurate, and clickable https:// links to reputable sources (AP, Reuters, journals, etc.). DO NOT guess exact article URLs. Instead, provide a direct Google Search URL to find the claim on a trusted site. Format it exactly like this: https://www.google.com/search?q=site:apnews.com+your+keywords+here
    3. You MUST provide a 'bias_report' assessing the source's reliability and political/ideological bias.
    4. If a claim cannot be verified, rate it UNCERTAIN.
    """

    gemini_contents = []
    
    # 1. Add the text prompt
    prompt_text = "Analyze this content and fact check the core claims."
    if text:
        prompt_text += f"\n\nText provided by user: {text}"
    gemini_contents.append(prompt_text)

    # 2. Download and add the image if one was sent
    if image_url:
        try:
            async with httpx.AsyncClient() as client:
                img_resp = await client.get(image_url, timeout=10.0)
                if img_resp.status_code == 200:
                    mime_type = img_resp.headers.get("content-type", "image/jpeg")
                    # Append the raw image bytes for Gemini's vision model
                    gemini_contents.append(
                        types.Part.from_bytes(data=img_resp.content, mime_type=mime_type)
                    )
        except Exception as e:
            print(f"Image fetch failed: {e}")

    try:
        response = await gemini_client.aio.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=f"Analyze this text and fact check the core claims: {text}",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=FactCheckList,
                temperature=0.1, # Low temperature for factual consistency
            ),
        )
        
        # Parse the JSON response returned
        agent_data = json.loads(response.text)
        formatted_claims = []

        # Loop through the multiple results the AI found
        for item in agent_data.get("results", []):
            source_names = ", ".join([s.get("source_name", "Unknown") for s in item.get("sources", [])])
            
            formatted_claims.append({
                "claim": item.get("claim", "Extracted claim"), 
                "rating": item.get("rating", "UNKNOWN"),
                "source": source_names or "No specific trusted sources found.",
                "detailed_report": item # Passes the sources, links, and bias reports to React
            })
            
        return formatted_claims
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return [{"claim": "Google API Quota exceeded. Please wait a moment.", "rating": "Limit", "source": "Google API"}]
        return [{"claim": f"Agent Error: {error_msg}", "rating": "Error", "source": "N/A"}]

# --- ROUTES ---
@app.get("/")
async def root():
    return {"message": "Aegis Backend is running! Use the extension to analyze text."}

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(request: AnalysisRequest):
    if not request.text and not request.image_url:
        raise HTTPException(status_code=400, detail="Must provide text or an image.")

    # Run both API calls in parallel to save time
    ai_task = asyncio.create_task(get_ai_detection(request.text))
    fact_task = asyncio.create_task(get_fact_check(request.text, request.image_url))

    ai_result, fact_result = await asyncio.gather(ai_task, fact_task)

    return {
        "ai_score": ai_result.get("score", 0),
        "claims": fact_result,
        "status": "success"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)