# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import httpx
import asyncio
import os
import json
import re
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
    mode: Optional[str] = "quick"

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
    rating: str = Field(description="MUST be one of: TRUE, FALSE, UNCERTAIN, or OPINION")
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

# --- MODE 1: DEEP DIVE (Google Search Enabled, Strict Rules) ---
async def get_fact_check_deep(text: str, image_url: str = None):
    current_date = datetime.now().strftime("%B %d, %Y")
    system_prompt = f"""
    You are an expert, highly objective Real-Time Fact-Checking Agent. 
    The current date is {current_date}. You must prioritize the most recent, up-to-date information from this year unless the user's content is explicitly a past event or a historical claim.
    Your primary function is to analyze provided text OR images (like screenshots of social media posts, news headlines, or memes), extract the core claims, and verify their accuracy by searching for information 
    across trusted, highly reputable websites (e.g., AP News, Reuters, established academic journals,, or verified government data).
    
    Maintain a strictly neutral, journalistic tone. If a claim cannot be adequately verified by highly 
    trusted sources, you must rate it UNCERTAIN and explain the lack of available consensus. Ensure all 
    links are real, accurate, and directly relevant.

    CRITICAL INSTRUCTIONS:
    1. Extract 1-3 of the most prominent claims from the User's content. IF AN IMAGE IS PROVIDED, YOU MUST PERFORM OCR AND READ ALL VISIBLE TEXT IN THE IMAGE.
    2. LIVE WEB SEARCH: You have access to Google Search. You MUST use it to verify the claims against current data. BANNED SITES: Wikipedia, radio transcripts, niche blogs, aggregators.
    3. DIRECT LINKS ONLY: You MUST provide the exact, direct https:// URL to the real article or source you found. NO PHANTOM LINKS.
    4. IF the content contains NO factual claims to verify, such as an opinion, state that there is no claim to fact check or that it is an opinion. If it is an opinion, explain that and only return the verdict of the opinion.
    5. You MUST provide a short 'bias_report' assessing the source's reliability and only if applicable, political/ideological bias.
    5. TRUST TIERS: Assign a 'trust_tier' integer to each source:
        - Tier 1: AP, Reuters, BBC, major papers (NYT, WSJ), .gov, .edu.
        - Tier 2: Standard reputable news, established magazines.
        - Tier 3: bad sites: Wikipedia, radio transcripts, niche blogs, aggregators.
    6. STRICT JSON OUTPUT: You MUST format your response as a valid JSON object matching this EXACT structure. All keys must be present. Do not add markdown or conversational text.
    {{
        "fact_checks": [
            {{
                "claim": "The exact quote or specific claim",
                "rating": "TRUE", "FALSE", "OPINION", or "UNCERTAIN",
                "brief_description": "2-3 sentence summary explaining the truth",
                "sources": [
                    {{
                        "source_name": "Name of the website",
                        "source_summary": "Brief description of what this site reported",
                        "bias_report": "Objective assessment of the website's bias and reliability",
                        "trust_tier": 1,
                        "link": "https://..."
                    }}
                ]
            }}
        ]
    }}
    """

    fc_contents = []
    
    # 1. Add the text prompt
    prompt_text = "Analyze this content and fact check the core claims. Please meticulously read any text embedded directly in the image."
    if text:
        prompt_text += f"\n\nText provided by user: {text}"
    fc_contents.append(prompt_text)

    # 2. Download and add the image if one was sent
    if image_url:
        print(f"Attempting to download image: {image_url[:50]}...") # Debug log
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
            }
            async with httpx.AsyncClient(follow_redirects=True) as client:
                img_resp = await client.get(image_url, headers=headers, timeout=15.0)
                if img_resp.status_code == 200:
                    mime_type = img_resp.headers.get("content-type", "image/jpeg")
                    fc_contents.append(
                        types.Part.from_bytes(data=img_resp.content, mime_type=mime_type)
                    )
        except Exception as e:
            print(f"Image fetch failed: {e}")

    # 3. Call the Agent
    try:
        max_retries = 3
        response = None
        
        # ATTEMPT 1: Try Flash 3 times
        for attempt in range(max_retries):
            try:
                response = await gemini_client.aio.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=fc_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.1, 
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    ),
                )
                break #Exit the retry loop
            except Exception as api_error:
                error_str = str(api_error).upper()
                if "503" in error_str or "UNAVAILABLE" in error_str:
                    print(f"2.5-Flash overloaded (503). Attempt {attempt + 1}/{max_retries} failed.")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2) # Give the server 2 seconds
                else:
                    raise api_error

        # ATTEMPT 2: Fallback to Lite if all 3 Flash attempts failed
        if not response:
            print("2.5-Flash jammed. Trying 2.5-Lite fallback")
            try:
                response = await gemini_client.aio.models.generate_content(
                    model='gemini-2.5-flash-lite', 
                    contents=fc_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.1, 
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    ),
                )
            except Exception as fallback_error:
                # If Lite ALSO fails,
                raise Exception("API servers are currently overloaded. All attempts failed. Please try again later.") from fallback_error

        raw_text = response.text

        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}') + 1

        if start_idx != -1 and end_idx != 0:
            clean_json_string = raw_text[start_idx:end_idx]
        else:
            clean_json_string = raw_text

        parsed_data= json.loads(clean_json_string)
        fact_checks = parsed_data.get("fact_checks", [])

        print("\n=== DEBUG: DATA BEING SENT TO FRONTEND ===")
        print(json.dumps(fact_checks, indent=2))
        print("==========================================\n")

        return fact_checks
    
    except json.JSONDecodeError:
        print(f"Failed to parse JSON. Raw AI output was: {raw_text}")
        return [{
            "claim": "Processing Error",
            "rating": "UNCERTAIN",
            "brief_description": "The AI successfully researched the claim, but failed to format the response correctly. Please try scanning again.",
            "sources": [],
            "bias_report": "N/A"
        }]
    except Exception as e:
            error_msg = str(e)
            print(f"Agent Error: {error_msg}")
            if "429" in error_msg:
                return [{"claim": "Google API Quota exceeded. Please wait a moment.", "rating": "UNCERTAIN", "brief_description": "API Limit reached.", "sources": [], "bias_report": "N/A"}]
            return [{
                "claim": "Server Overload",
                "rating": "UNCERTAIN",
                "brief_description": f"An error occurred: {error_msg}",
                "sources": [],
                "bias_report": "N/A"
            }]


# --- MODE 2: QUICK SCAN (No tools, structured output) ---
async def get_fact_check_quick(text: str, image_url: str = None):
    system_prompt = """
    You are an expert, highly objective Real-Time Fact-Checking Agent. Your primary function is to 
    analyze provided text OR images (like screenshots of social media posts, news headlines, or memes), extract the core claims, and verify their accuracy by searching for information 
    across trusted, highly reputable websites (e.g., AP News, Reuters, established academic journals, or verified government data).
    
    Maintain a strictly neutral, journalistic tone. If a claim cannot be adequately verified by highly 
    trusted sources, you must rate it UNCERTAIN and explain the lack of available consensus. Ensure all 
    links are real, accurate, and directly relevant.

    CRITICAL INSTRUCTIONS:
    1. Extract 1-3 of the most prominent claims from the text.
    2. IF a statement is purely subjective and cannot be fact-checked, extract it as the claim, rate it "OPINION", and explain why it is subjective in the description.
    3. IF the image or text contains absolute NO factual claims OR opinions (e.g., a regular photo with no text), you MUST output exactly one result with:
        - claim: "No verifiable claims detected."
        - rating: "UNCERTAIN"
        - brief_description: "The provided content does not contain specific, objective statements or text that can be fact-checked."
        - sources: []
    4. You MUST provide real, accurate, and clickable https:// links to reputable sources. DO NOT guess exact article URLs. Instead, provide a direct Google Search URL to find the claim on a trusted site. Format it exactly like this: https://www.google.com/search?q=site:apnews.com+your+keywords+here
    5. You MUST provide a 'bias_report' assessing the source's reliability and political/ideological bias.
    """

    fc_contents = []
    
    prompt_text = "Analyze this content and fact check the core claims."
    if text:
        prompt_text += f"\n\nText provided by user: {text}"
    fc_contents.append(prompt_text)

    if image_url:
        try:
            async with httpx.AsyncClient() as client:
                img_resp = await client.get(image_url, timeout=10.0)
                if img_resp.status_code == 200:
                    mime_type = img_resp.headers.get("content-type", "image/jpeg")
                    fc_contents.append(types.Part.from_bytes(data=img_resp.content, mime_type=mime_type))
        except Exception as e:
            print(f"Image fetch failed: {e}")

    try:
        max_retries = 3
        response = None
        
        # ATTEMPT 1: Try Flash 3 times
        for attempt in range(max_retries):
            try:
                response = await gemini_client.aio.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=fc_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        response_schema=FactCheckList, 
                        temperature=0.1, 
                    ),
                )
                break #exit the loop
            except Exception as api_error:
                error_str = str(api_error).upper()
                if "503" in error_str or "UNAVAILABLE" in error_str:
                    print(f"2.5-Flash (503). Attempt {attempt + 1}/{max_retries} failed.")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2) 
                else:
                    raise api_error 

        # attemp 2: flash-lite
        if not response:
            print("2.5-Flash failed. Trying 2.5-Lite fallback.")
            try:
                response = await gemini_client.aio.models.generate_content(
                    model='gemini-2.5-flash-lite',
                    contents=fc_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        response_schema=FactCheckList,
                        temperature=0.1, 
                    ),
                )
            except Exception as fallback_error:
                raise Exception("Google API servers are currently overloaded. All retry attempts across multiple models failed. Please try again later.") from fallback_error
        
        agent_data = json.loads(response.text)
        return agent_data.get("results", [])
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return [{"claim": "API Quota Exceeded.", "rating": "UNCERTAIN", "brief_description": "Please wait a moment before trying again.", "sources": [], "bias_report": "N/A"}]
        return [{"claim": "Quick Scan Error", "rating": "UNCERTAIN", "brief_description": f"Error details: {error_msg}", "sources": [], "bias_report": "N/A"}]

@app.get("/")
async def root():
    return {"message": "AEGIS Backend is running!"}

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(request: AnalysisRequest):
    if not request.text and not request.image_url:
        raise HTTPException(status_code=400, detail="Must provide text or an image.")

    ai_task = asyncio.create_task(get_ai_detection(request.text))
    
    # --- Route based on Mode ---
    if request.mode == "deep":
        fact_task = asyncio.create_task(get_fact_check_deep(request.text, request.image_url))
    else:
        fact_task = asyncio.create_task(get_fact_check_quick(request.text, request.image_url))

    ai_result, fact_result = await asyncio.gather(ai_task, fact_task)
    
    safe_claims = fact_result if isinstance(fact_result, list) else []

    return {
        "ai_score": ai_result.get("score", 0),
        "claims": safe_claims,
        "status": "success"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)