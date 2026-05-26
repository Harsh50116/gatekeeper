import logging
import os

from tavily import TavilyClient

logger = logging.getLogger(__name__)

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")


def _get_client() -> TavilyClient:
    if not TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY not set in environment")
    return TavilyClient(TAVILY_API_KEY)


def web_search(query: str, max_results: int = 5) -> list[dict]:
    client = _get_client()
    response = client.search(query=query, search_depth="advanced", max_results=max_results)
    results = []
    for r in response.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
        })
    logger.info("Search for '%s': %d results", query[:60], len(results))
    return results
