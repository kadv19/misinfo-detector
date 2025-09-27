"""Friend's Custom Text Analysis Algorithm - Decomposes text, fetches matching news, computes confidence (0-100)"""

from textblob import TextBlob
import requests
import feedparser
from bs4 import BeautifulSoup
import numpy as np

def analyze_text(target_news):
    """Decompose target news into keywords/gist, fetch matching Google News, analyze sentiment for confidence (0-100)"""
    # Step 1: Decompose into keywords (POS tagging)
    blob = TextBlob(target_news)
    keywords = [word for word, pos in blob.tags if pos in ['NN', 'NNS', 'JJ', 'VB', 'VBD']]
    keywords = list(set(keywords))[:8]  # Unique, limited
    
    # Step 2: Generate gist (noun phrases or first sentence)
    gist = ' '.join(list(blob.noun_phrases)) if blob.noun_phrases else target_news.split('.')[0] + "."
    
    # Step 3: Fetch matching Google News articles (keywords + gist)
    query = ' '.join(keywords[:4]) + ' ' + ' '.join(gist.split()[0:2])  # Fixed: Join gist words
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        response = requests.get(rss_url, timeout=15)
        feed = feedparser.parse(response.content)
        articles = []
        for entry in feed.entries[:10]:  # 10 matching articles
            title = entry.get('title', '')
            summary = BeautifulSoup(entry.get('summary', ''), "html.parser").get_text()[:200]
            sentiment = TextBlob(title + ' ' + summary).sentiment.polarity  # -1 to 1
            articles.append({
                'title': title,
                'summary': summary,
                'sentiment': sentiment,
                'url': entry.get('link', '')
            })
    except:
        articles = []  # Fallback
    
    # Step 4: Confidence score (0-100): +10 per favor article, -5 per contrary
    confidence = 50  # Neutral start
    for article in articles:
        if article['sentiment'] > 0.1:  # Favor
            confidence += 10
        elif article['sentiment'] < -0.1:  # Contrary
            confidence -= 5
        confidence = max(0, min(100, confidence))  # Clamp 0-100
    
    return {
        'keywords': keywords,
        'gist': gist,
        'articles': articles,
        'confidence': confidence
    }

def get_verdict(confidence):
    if confidence > 50:
        return "TRUE"
    elif confidence > 40:
        return "WHISTLEBLOWER"
    else:
        return "FAKE"
