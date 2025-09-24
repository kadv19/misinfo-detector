"""Friend's Custom Text Analysis Algorithm - Decomposes text, fetches matching news, computes favor %"""

from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
import feedparser
from bs4 import BeautifulSoup
import numpy as np

def analyze_text(target_news):
    """Main function: Decomposes target news into keywords/gist, fetches matching Google News articles, analyzes sentiment for favor %"""
    # Step 1: Decompose into keywords (POS tagging for nouns/adjectives/verbs)
    blob = TextBlob(target_news)
    keywords = [word for word, pos in blob.tags if pos in ['NN', 'NNS', 'JJ', 'VB', 'VBD']]
    keywords = list(set(keywords))[:8]  # Unique, limited to 8
    
    # Step 2: Generate gist (noun phrases or first sentence)
    gist = ' '.join(list(blob.noun_phrases)) if blob.noun_phrases else target_news.split('.')[0] + "."
    
    # Step 3: Fetch matching Google News articles (subset based on keywords/gist)
    query = ' '.join(keywords[:4])
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    response = requests.get(rss_url, timeout=10)
    feed = feedparser.parse(response.content)
    articles = []
    for entry in feed.entries[:10]:  # Limit to 10 matching articles
        title = entry.get('title', '')
        summary = BeautifulSoup(entry.get('summary', ''), "html.parser").get_text()[:200]
        sentiment = TextBlob(title + ' ' + summary).sentiment.polarity
        articles.append({
            'title': title,
            'summary': summary,
            'sentiment': sentiment,
            'url': entry.get('link', '')
        })
    
    # Step 4: Compute favor % (cosine similarity to gist + sentiment average)
    if not articles:
        return {'keywords': keywords, 'gist': gist, 'articles': [], 'favor_pct': 50.0}
    
    vectorizer = TfidfVectorizer(stop_words='english')
    gist_vec = vectorizer.fit_transform([gist.lower()])
    article_vecs = vectorizer.transform([a['title'] + ' ' + a['summary'] for a in articles])
    similarities = cosine_similarity(gist_vec, article_vecs)[0]
    
    # Favor %: Avg similarity (matching) + positive sentiment (analysis)
    avg_similarity = np.mean(similarities)
    positive_sent = sum(1 for a in articles if a['sentiment'] > 0)
    favor_pct = (positive_sent / len(articles) * 50) + (avg_similarity * 50)  # Scale to 0-100
    
    return {
        'keywords': keywords,
        'gist': gist,
        'articles': articles,
        'favor_pct': favor_pct
    }

# Verdict helper (based on favor % thresholds)
def get_verdict(favor_pct):
    if favor_pct > 50:
        return "TRUE"
    elif favor_pct > 40:
        return "WHISTLEBLOWER"
    else:
        return "FAKE"
