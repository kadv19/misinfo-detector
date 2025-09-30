from fastapi import HTTPException
import requests
import json
from .content import get_content_from_link

#API KEY DECLARATION
GEMINI_API_KEY = "AIzaSyDH06vyJHu3GpKWg2Hqjp-on0vD4mjjI7o"


#Function definition
def generate_gemini_response(user_text, news_articles):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={GEMINI_API_KEY}"
    
    # Construct a detailed prompt
    articles_context = "\n".join([
        f"Source: {article['source']}\nTitle: {article['title']}\nExcerpt: {get_content_from_link(article['link'])}"
        for article in news_articles
    ])

    system_prompt = """You are an AI-Powered Misinformation Detector. Your goal is to provide an evidence-based, non-accusatory verdict on the credibility of a news claim.

        **Your Task (All in one step):**
        1. **Analyze the Claim:** First, perform a detailed analysis of the user's claim. Extract key entities, keywords, and the overall sentiment or emotional tone.
        2. **Evaluate External Sources:** Next, analyze the provided list of external news articles. For each article, determine its stance relative to the user's claim, classifying it as 'Supports', 'Conflicts', or 'Neutral'. Pay close attention to the source's reputation, as articles from highly credible sources carry more weight.
        3. **Calculate Credibility Score:** Based on a neutral starting score of 50, adjust the score using the following logic, ensuring the final score is clamped between 0 and 100:
        - For every credible source that **supports** the claim, increase the score by 5 points.
        - For every credible source that **conflicts** with the claim, decrease the score by 10 points.
        - For every credible source that is **neutral**, do not adjust the score, but recognize that this indicates a lack of strong corroboration.
        - If the user's original claim contains highly sensational or emotionally charged language, apply a penalty of 10 points to the final score.
        4. **Determine Verdict and Reasons:** Map the final score to a clear verdict (High Likelihood of Misinformation, Conflicting or Uncorroborated Claims, or Likely Credible). Provide three distinct, evidence-based reasons for your verdict, drawing from your analysis of the sources.Provide atleast 5 reasons
        5. **State the 'What-If':** Conclude the analysis by providing a specific, verifiable type of evidence that would be needed to change the verdict.
        6. **Generate a Visual Data Structure:** Create a 'lineage_graph' JSON object that represents the user's claim and its relationship to the top 4 most relevant articles. Use 'Supports' or 'Conflicts' to describe the link type.
        7.Also include how did you calculated the confidence score
        
        **Strict JSON Output:**
        Provide the entire response as a single JSON object. The structure must be exactly as follows. Do not include any other text or markdown outside this JSON object.

        {{
            "verdict": "string",
            "confidence_score": "number",
            "reasons": ["string", "string", "string"],
            "what_would_change": "string",
            "lineage_graph": {
            "claim": "string",
            "connections": [
                {
                    "source": "String",
                    "url" : "url"
                    "title": "String",
                    "link_type": "Supports or Contradict"
                },
                {
                    "source": "String",
                    "url" : "url"
                    "title": "String",
                    "link_type": "Supports or Contradict"
                },
                
                {
                    "source": "String",
                    "url" : "url"
                    "title": "String",
                    "link_type": "Supports or Contradict"
                }
                .......
            ]
        },
        "confidence_score_calculation": "String"

        }}
"""

    user_query = f"""
      Analyze the following news text:
      "{user_text}"

      Here is the list of news articles I have found:
      {articles_context}
    """
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"responseMimeType": "application/json"},
    }

    try:
        response = requests.post(api_url, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        
        # Parse the JSON string from the response
        json_string = response.json()['candidates'][0]['content']['parts'][0]['text']
        return json.loads(json_string)
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        raise HTTPException(status_code=500, detail="Error communicating with AI service.")
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error parsing Gemini response: {e}")
        print(f"Raw Gemini response was: {response.text}")
        raise HTTPException(status_code=500, detail="Invalid response from AI service.")


