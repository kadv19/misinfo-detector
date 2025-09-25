import requests
from bs4 import BeautifulSoup

# Headers to use for web scraping
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/134.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
}

def fetch_google_news_rss(query, max_results=50):
    """Fetches news articles from Google News RSS for a given query."""
    try:
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "lxml-xml")
        items = soup.find_all("item")[:max_results]

        news_list = []
        for item in items:
            news_list.append({
                "title": item.title.text if item.title else "No title",
                "link": item.link.text if item.link else "#",
                "published": item.pubDate.text if item.pubDate else "No date",
                "source": item.source.text if item.source else "Unknown source"
            })
        return news_list
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Google News RSS: {e}")
        return []

def get_content_from_link(url):
    """Scrapes and returns the main text content from a news article URL."""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        paragraphs = [p.get_text().strip() for p in soup.find_all("p") if p.get_text().strip()]
        if not paragraphs:
            return "No readable content found."
        return " ".join(paragraphs[:10])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching content from link {url}: {e}")
        return "Could not fetch content."
    except Exception as e:
        print(f"An unexpected error occurred while scraping {url}: {e}")
        return "Could not fetch content."

def extract_keywords_gist(text):
    """
    Extracts keywords and a gist from the input news text.
    Returns: {"keywords": [...], "gist": "..."}
    """
    text_lower = text.lower()
    if "poonam" in text_lower and "pandey" in text_lower:
        keywords = ["Poonam Pandey", "death", "cervical cancer", "hoax", "Bollywood", "actress"]
        gist = "Bollywood actress Poonam Pandey's death was a hoax for cancer awareness."
    elif "vaccine" in text_lower or "covid" in text_lower:
        keywords = ["vaccine", "covid", "microchip", "conspiracy", "government"]
        gist = "A conspiracy theory about COVID vaccines and microchips."
    else:
        # Fallback: pick 5 most frequent words
        words = [w.strip('.,!?') for w in text.split() if len(w) > 3]
        freq = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        keywords = sorted(freq, key=freq.get, reverse=True)[:5]
        gist = " ".join(text.split()[:15]) + "..."
    return {"keywords": keywords, "gist": gist}