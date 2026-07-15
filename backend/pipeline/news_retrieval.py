"""
news_retrieval.py
Fetches recent news relevant to a case type or a named ongoing case,
using NewsAPI. This is plain code (an API call, not an LLM call) -
it's a retrieval step, same category as retrieval.py's corpus lookup.
"""

import os
import requests

NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"

MAX_ARTICLES = 5


def retrieve_news(query_hint: str) -> list:
    """
    Searches recent news articles related to the given query hint
    (e.g. case_type in plain words, or a named case/topic the user asked about).
    Returns a list of article dicts, capped at MAX_ARTICLES.
    Fails gracefully - if the API errors out, returns an empty list rather
    than crashing the pipeline.
    """
    if not NEWS_API_KEY:
        return []

    params = {
        "q": query_hint,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": MAX_ARTICLES,
        "apiKey": NEWS_API_KEY,
    }

    try:
        response = requests.get(NEWS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return []

    articles = []
    for i, article in enumerate(data.get("articles", [])[:MAX_ARTICLES]):
        articles.append({
            "id": f"news_{i}_{article.get('publishedAt', '')[:10]}",
            "title": article.get("title", "Untitled"),
            "text": (article.get("description") or "")[:500],
            "source_name": article.get("source", {}).get("name", "Unknown source"),
            "source_url": article.get("url", ""),
            "published_at": article.get("publishedAt", ""),
        })

    return articles
