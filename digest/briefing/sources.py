CATEGORIES = ["tech_ai", "business_markets", "sports", "world_news", "science"]

SUBCATEGORIES = {
    "tech_ai": [
        {"id": "ai_ml", "name": "AI / Machine Learning"},
        {"id": "cloud", "name": "Cloud & Dev Tools"},
        {"id": "llm", "name": "LLMs"},
        {"id": "hw", "name": "Hardware"},
        {"id": "other", "name": "Other"},
    ],
    "business_markets": [
        {"id": "equities", "name": "Wall Street / Equities"},
        {"id": "crypto", "name": "Crypto"},
        {"id": "macro", "name": "Macro & Economy"},
        {"id": "other", "name": "Other"},
    ],
    "sports": [
        {"id": "cricket", "name": "Cricket"},
        {"id": "nfl", "name": "Football (NFL)"},
        {"id": "nba", "name": "Basketball (NBA)"},
        {"id": "soccer", "name": "Soccer"},
        {"id": "other", "name": "Other"},
    ],
    "world_news": [
        {"id": "us_politics", "name": "US Politics"},
        {"id": "geo", "name": "Geopolitics"},
        {"id": "climate", "name": "Climate & Environment"},
        {"id": "other", "name": "Other"},
    ],
    "science": [
        {"id": "space", "name": "Space & Astronomy"},
        {"id": "bio", "name": "Biology & Medicine"},
        {"id": "physics_math", "name": "Physics & Math"},
        {"id": "other", "name": "Other"},
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
