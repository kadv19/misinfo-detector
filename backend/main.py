from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .utils.api import generate_gemini_response
from .utils.content import fetch_google_news_rss
     
    
     
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
    #Request to /analyze to get analysed content
@app.post("/analyze")
def analyze_news_endpoint(payload: dict):
        user_text = payload.get("text")
        if not user_text:
            raise HTTPException(status_code=400, detail="Text is required in the request body.")
        related_news = fetch_google_news_rss(user_text, max_results=10) # Fetches up to 10 titles and links
        if not related_news:
            # If no news found, still try to analyze the claim with Gemini
            response_data = generate_gemini_response(user_text, [])
        else:
            # Step 2: Pass the user text and related news to Gemini for analysis
            response_data = generate_gemini_response(user_text, related_news)
        return response_data