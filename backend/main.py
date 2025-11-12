

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from UTILS.api import generate_gemini_response, summerize_voice_content
from UTILS.content import fetch_google_news_rss

# import uvicorn
# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware to allow requests from your React frontend
# In a production environment, you should restrict this to your specific frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
def hello():
    return { "data" : "HELLO"}


#Request to /analyze to get analysed content
@app.post("/analyze")
def analyze_news_endpoint(payload: dict):
    user_text = payload.get("text")
    if not user_text:
        raise HTTPException(status_code=400, detail="Text is required in the request body.")

    # Step 1: Fetch related news from Google News
    related_news = fetch_google_news_rss(user_text, max_results=10) # Fetches up to 10 titles and links

    if not related_news:
        # If no news found, still try to analyze the claim with Gemini
        response_data = generate_gemini_response(user_text, [])
    else:
        # Step 2: Pass the user text and related news to Gemini for analysis
        response_data = generate_gemini_response(user_text, related_news)
    
    return response_data


@app.post("/verify_news")
def verify_news_claim(user_input: dict):
    """
    1. Extract keywords from user text using Gemini.
    2. Search Google News using those keywords.
    3. Pass articles to Gemini for final credibility verdict.
    """
    try:
        user_text = user_input.get("text", "")
        if not user_text:
            raise HTTPException(status_code=400, detail="Missing 'text' field.")

        # --- Step 1: Extract Keywords ---
        print("Extracting keywords...")
        keyword_result = summerize_voice_content(user_text)
        keywords = keyword_result.get("keywords", [])

        if not keywords:
            raise HTTPException(status_code=400, detail="No keywords extracted from text.")

        print(f"Extracted keywords: {keywords}")

        # --- Step 2: Fetch Google News for each keyword ---
        all_articles = []
        for keyword in keywords:
            articles = fetch_google_news_rss(keyword, max_results=3)
            all_articles.extend(articles)
            

        if not all_articles:
            raise HTTPException(status_code=404, detail="No news articles found for extracted keywords.")

        print(f"Fetched {len(all_articles)} total articles.")

        # --- Step 3: Generate AI Credibility Report ---
        result = generate_gemini_response(user_text, all_articles)

        return {
            "keywords": keywords,
            "articles_used": len(all_articles),
            "analysis": result
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    




@app.post("/get-audio")
def get_audio_description(audio_path: dict):
    try:
        user_audio = audio_path.get("path", "")
        if not user_audio:
            raise HTTPException(status_code=400, detail="Missing 'path' field.")
        
        # 👇 Safe, lazy import (only happens on request)
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(user_audio, fp16=False)
        return {"text": result["text"]}
    
    except Exception as e:
        print(f"Unexpected error in /get-audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/check-ai")
def check_if_ai(path:dict):
    from transformers import pipeline
    try:
        audio_path = path.get("path", "")
        if not audio_path:
            raise HTTPException(status_code=400, detail="Missing 'text' field.")
        pipe = pipeline("audio-classification", model="abhishtagatya/wav2vec2-base-960h-asv19-deepfake")
        try:
            results = pipe(audio_path)
            print("Prediction Results:", results)

            # The output is typically a list of dictionaries, like:
            # [{'score': 0.999, 'label': 'spoof'}, {'score': 0.001, 'label': 'bonafide'}]

        except Exception as e:
            print(f"An error occurred during prediction: {e}")
            print("Ensure the audio file path is correct and accessible.")

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    pass
# --- BEGIN appended: static mount + /v1/analyze handler ---
from fastapi.staticfiles import StaticFiles
import os
from fastapi import UploadFile, File, Form
import json

# Optional: import analyze_service if present (non-fatal if missing)
try:
    from analyze_service import analyze_file_or_text
except Exception:
    analyze_file_or_text = None

# Mount static built frontend if present (serves frontend from backend/static/)
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    # mount at root so visiting / serves the SPA
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")

@app.post("/v1/analyze")
async def v1_analyze(file: UploadFile | None = File(default=None),
                     text: str | None = Form(default=None),
                     metadata: str | None = Form(default=None)):
    """
    Lightweight analyze endpoint for frontends.
    Accepts multipart/form-data:
      - file (image) OR
      - text (string)
      - metadata (stringified JSON)
    Uses analyze_service.analyze_file_or_text if available, otherwise falls back to UTILS.generate_gemini_response for text or to safe heuristics.
    """
    try:
        metadata_obj = None
        if metadata:
            try:
                metadata_obj = json.loads(metadata)
            except Exception:
                metadata_obj = {"raw_metadata": metadata}

        # If text provided -> prefer your UTILS.generate_gemini_response
        if text:
            try:
                # generate_gemini_response is imported earlier in main.py
                related_news = metadata_obj.get("related_news") if metadata_obj and isinstance(metadata_obj, dict) else []
                try:
                    result = generate_gemini_response(text, related_news)
                except Exception as e:
                    print("generate_gemini_response error (v1_analyze):", e)
                    result = None

                if isinstance(result, dict) and "confidence_score" in result:
                    return result

                # fallback deterministic response
                score = 60.0
                reasons = ["Fallback heuristic: no external analysis available."]
                verdict = "Original" if score >= 60 else "Doctored"
                return {
                    "confidence_score": score,
                    "confidence_score_calculation": "Fallback heuristic (no Gemini result).",
                    "lineage_graph": None,
                    "reasons": reasons,
                    "verdict": verdict,
                    "what_would_change": "Provide source links or original references for higher confidence."
                }
            except Exception as e:
                print("Error handling text in /v1/analyze:", e)
                raise HTTPException(status_code=500, detail=str(e))

        # If file provided -> prefer analyze_service if present
        if file:
            try:
                bytes_data = await file.read()
                if analyze_file_or_text:
                    try:
                        res = analyze_file_or_text(file_bytes=bytes_data, filename=file.filename, metadata=metadata_obj)
                        return res
                    except Exception as inner_e:
                        print("analyze_service failed:", inner_e)
                # fallback image response
                return {
                    "confidence_score": 55.0,
                    "confidence_score_calculation": "Fallback image heuristic.",
                    "lineage_graph": None,
                    "reasons": ["No server-side image model available; returned fallback."],
                    "verdict": "Doctored",
                    "what_would_change": "Provide original source or enable server-side image analysis."
                }
            except Exception as e:
                print("Error reading uploaded file in /v1/analyze:", e)
                raise HTTPException(status_code=500, detail=str(e))

        # nothing provided
        raise HTTPException(status_code=400, detail="No 'file' or 'text' provided.")
    except HTTPException:
        raise
    except Exception as e:
        print("Unexpected error in /v1/analyze:", e)
        raise HTTPException(status_code=500, detail=str(e))
# --- END appended block ---
