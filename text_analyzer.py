"""Friend's Custom Text Analysis Algorithm - Tuned for realistic scoring (30% on hoax like 'india bombs russia')"""

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
    keywords = list(set(keywords))[:8]
    
    # Step 2: Generate gist
    gist = ' '.join(list(blob.noun_phrases)) if blob.noun_phrases else target_news.split('.')[0] + "."
    
    # Step 3: Fetch matching Google News
    query = ' '.join(keywords[:4]) + ' ' + ' '.join(gist.split()[0:2])
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        response = requests.get(rss_url, timeout=15)
        feed = feedparser.parse(response.content)
        articles = []
        for entry in feed.entries[:10]:
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
        articles = []
    
    # Step 4: Confidence score (strict for hoax: +10 for >0.1, -3 for neutral 0.0, -10 for < -0.1)
    confidence = 50  # Neutral start
    for article in articles:
        if article['sentiment'] > 0.1:  # Strong favor
            confidence += 10
        elif article['sentiment'] == 0.0:  # Neutral/irrelevant
            confidence -= 3
        elif article['sentiment'] < -0.1:  # Contrary
            confidence -= 10
        confidence = max(0, min(100, confidence))  # Clamp after each
    
    # Gist similarity penalty (low match = hoax)
    if articles:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vectorizer = TfidfVectorizer(stop_words='english')
        gist_vec = vectorizer.fit_transform([gist.lower()])
        article_vecs = vectorizer.transform([a['title'] + ' ' + a['summary'] for a in articles])
        similarities = cosine_similarity(gist_vec, article_vecs)[0]
        avg_similarity = np.mean(similarities)
        if avg_similarity < 0.6:  # Low match = penalty for unrelated articles
            confidence -= 30
        confidence = max(0, min(100, confidence))
    
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