import os
import requests
import feedparser
import urllib.parse
from typing import List, Dict, Optional

def get_company_news(ticker: str, company_name: Optional[str] = None, limit: int = 5) -> List[Dict[str, str]]:
    """Fetch top news headlines for a target stock.
    
    Uses ticker and company name to query NewsAPI or Google News RSS feed,
    filtering the results to ensure relevance to the target company.
    
    Returns a list of dicts with keys: 'title', 'source', 'published', 'url'.
    """
    ticker = ticker.strip().upper()
    if not company_name:
        company_name = ticker
    else:
        company_name = company_name.strip()
        
    query = f"{ticker} OR {company_name} stock news"
    headlines: List[Dict[str, str]] = []
    
    # Clean company name keywords for filtering
    ignored_words = {"corp", "corporation", "inc", "incorporated", "co", "company", "ltd", "limited", "plc", "stock", "news"}
    keywords = {ticker.lower()}
    for word in company_name.lower().split():
        cleaned = "".join(c for c in word if c.isalnum())
        if cleaned and cleaned not in ignored_words:
            keywords.add(cleaned)
            
    def is_relevant(title: str) -> bool:
        title_lower = title.lower()
        return any(kw in title_lower for kw in keywords)

    api_key = os.getenv('NEWSAPI_KEY')
    if api_key:
        url = 'https://newsapi.org/v2/everything'
        params = {
            'q': query,
            'pageSize': limit * 4, # Fetch more to allow filtering
            'sortBy': 'publishedAt',
            'language': 'en',
            'apiKey': api_key,
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for article in data.get('articles', []):
                    title = article.get('title', '').strip()
                    if title and is_relevant(title):
                        headlines.append({
                            'title': title,
                            'source': article.get('source', {}).get('name', '').strip(),
                            'published': article.get('publishedAt', '').strip(),
                            'url': article.get('url', '').strip(),
                        })
                        if len(headlines) >= limit:
                            break
                return headlines
        except Exception as e:
            pass

    # Fallback: Google News RSS
    quoted_query = urllib.parse.quote(query)
    rss_url = f'https://news.google.com/rss/search?q={quoted_query}&hl=en-US&gl=US&ceid=US:en'
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            title = entry.get('title', '').strip()
            if title and is_relevant(title):
                # Clean source from title suffix (e.g. "Google News - MSFT" -> "Google News")
                source = entry.get('source', {}).get('title', '').strip()
                headlines.append({
                    'title': title,
                    'source': source,
                    'published': entry.get('published', '').strip(),
                    'url': entry.get('link', '').strip(),
                })
                if len(headlines) >= limit:
                    break
    except Exception as e:
        pass

    return headlines
