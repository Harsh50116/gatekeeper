CATEGORIES = ["tech_ai", "business_markets", "sports", "world_news", "science"]

SUBCATEGORIES = {
    "tech_ai": [
        {"id": "ml", "name": "Machine learning"},
        {"id": "llm", "name": "Local LLMs (Llama)"},
        {"id": "ai", "name": "AI research"},
        {"id": "cloud", "name": "Cloud & dev tools"},
        {"id": "hw", "name": "Hardware"},
    ],
    "business_markets": [
        {"id": "macro", "name": "Macro & Fed"},
        {"id": "equities", "name": "Equities"},
        {"id": "crypto", "name": "Crypto"},
        {"id": "deals", "name": "M&A & deals"},
        {"id": "earnings", "name": "Earnings"},
    ],
    "sports": [
        {"id": "nba", "name": "NBA"},
        {"id": "nfl", "name": "NFL"},
        {"id": "soccer", "name": "Soccer"},
        {"id": "tennis", "name": "Tennis"},
        {"id": "olympics", "name": "Olympics"},
    ],
    "world_news": [
        {"id": "geo", "name": "Geopolitics"},
        {"id": "climate", "name": "Climate"},
        {"id": "elections", "name": "Elections"},
        {"id": "conflicts", "name": "Conflicts"},
        {"id": "diplomacy", "name": "Diplomacy"},
    ],
    "science": [
        {"id": "space", "name": "Space & astronomy"},
        {"id": "bio", "name": "Biology & medicine"},
        {"id": "physics", "name": "Physics"},
        {"id": "climatesci", "name": "Climate science"},
        {"id": "eng", "name": "Engineering"},
    ],
}

ESPN_LEAGUES = [
    ("football", "nfl"),
    ("basketball", "nba"),
    ("baseball", "mlb"),
    ("hockey", "nhl"),
]

MARKET_INDICES = ["^GSPC", "^IXIC", "^DJI"]

SOURCES = {
    "tech_ai": [
        {"type": "hn_api", "source": "hn"},
        {"type": "rss", "url": "https://techcrunch.com/feed/", "source": "techcrunch"},
        {"type": "rss", "url": "https://www.theverge.com/rss/index.xml", "source": "theverge"},
        {"type": "rss", "url": "https://feeds.arstechnica.com/arstechnica/index", "source": "arstechnica"},
    ],
    "business_markets": [
        {"type": "rss", "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "source": "wsj"},
        {"type": "yfinance", "source": "yfinance"},
    ],
    "sports": [
        {"type": "rss", "url": "https://www.espn.com/espn/rss/news", "source": "espn"},
        {"type": "rss", "url": "http://feeds.bbci.co.uk/sport/rss.xml", "source": "bbc_sport"},
        {"type": "espn_json", "source": "espn_scores"},
    ],
    "world_news": [
        {"type": "rss", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "source": "bbc_world"},
        {"type": "rss", "url": "https://feeds.npr.org/1001/rss.xml", "source": "npr"},
        {"type": "rss", "url": "https://www.theguardian.com/world/rss", "source": "guardian"},
    ],
    "science": [
        {"type": "rss", "url": "https://www.nature.com/nature.rss", "source": "nature"},
        {"type": "rss", "url": "https://www.sciencedaily.com/rss/all.xml", "source": "sciencedaily"},
        {"type": "rss", "url": "https://www.nasa.gov/news-release/feed/", "source": "nasa"},
    ],
}
