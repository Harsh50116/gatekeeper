import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import httpx

from .sources import SUBCATEGORIES
from ..db.store import get_rss_items_by_subcategory, get_reddit_items_by_category

logger = logging.getLogger(__name__)

HYPERBOLIC_URL = "https://api.hyperbolic.xyz/v1/chat/completions"
MODEL = "meta-llama/Llama-3.3-70B-Instruct"
MAX_RETRIES = 1

_pass1_cache: dict[str, str] = {}


def _api_key() -> str:
    key = os.environ.get("HYPERBOLIC_KEY", "")
    if not key:
        raise RuntimeError("HYPERBOLIC_KEY not set in environment")
    return key


def _call_llm(system: str, user: str) -> str:
    resp = httpx.post(
        HYPERBOLIC_URL,
        headers={"Authorization": f"Bearer {_api_key()}"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.4,
            "max_tokens": 1024,
        },
        timeout=180.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _format_items_block(items: list[dict]) -> str:
    lines = []
    for it in items:
        line = f"- {it['title']} (source: {it['source']})"
        if it.get("summary"):
            line += f"\n  {it['summary'][:200]}"
        lines.append(line)
    return "\n".join(lines)


PASS1_SYSTEM = """You are a news editor. Summarize the following news items into a concise briefing.
Write 3-5 key points capturing the most important stories. Use plain sentences, no bullet points or markdown.
Each point should be one clear sentence. Focus on what happened and why it matters."""


def _summarize_items(category: str, subcategory: str, items: list[dict]) -> str:
    if not items:
        return ""

    if len(items) <= 5:
        block = _format_items_block(items)
        prompt = f"Category: {category}, Subcategory: {subcategory}\n\n{block}"
        return _call_llm(PASS1_SYSTEM, prompt)

    by_source: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        by_source[it["source"]].append(it)

    source_summaries = []
    for source, source_items in by_source.items():
        block = _format_items_block(source_items)
        prompt = f"Category: {category}, Source: {source}\n\n{block}"
        source_summaries.append(_call_llm(PASS1_SYSTEM, prompt))

    return "\n\n".join(source_summaries)


def summarize_subcategory(category: str, subcategory: str) -> str:
    cache_key = f"{category}/{subcategory}"
    if cache_key in _pass1_cache:
        return _pass1_cache[cache_key]

    rss = get_rss_items_by_subcategory(category, subcategory)
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    reddit_raw = get_reddit_items_by_category(category, [subcategory], cutoff)
    reddit = [
        {"title": r["title"], "summary": r.get("body"), "url": r["url"],
         "source": f"r/{r['subreddit']}", "published": r["published"]}
        for r in reddit_raw
    ]

    merged = rss + reddit
    summary = _summarize_items(category, subcategory, merged)
    _pass1_cache[cache_key] = summary
    return summary


PASS2_SYSTEM = """You are a radio morning show host writing a spoken news briefing.

Rules:
- Write exactly 400 to 450 words.
- Write in a warm, conversational tone as if speaking to the listener directly.
- Lead with the most engaging or surprising story to hook the listener.
- Weave between topics naturally. Do NOT group by category or use transitions like "In tech... In sports... In science..."
- No bullet points, no markdown, no numbered lists, no headers.
- Spell out all numbers: write "twenty percent" not "20%", "three hundred million" not "300M".
- Spell out common acronyms on first use unless universally known (AI, NBA, NFL are fine).
- No "firstly", "secondly", "lastly", "in conclusion" or similar structural language.
- Write complete flowing paragraphs meant to be read aloud.
- Where stories relate to each other, connect them naturally (e.g. cause and effect, broader trend, same event).
- If a previous briefing is provided, do NOT repeat those stories. If a story is a continuation of something covered previously, briefly reference it for context (e.g. "the summit we talked about yesterday wrapped up with...") before covering the new development."""


def generate_digest(category_summaries: dict[str, str], previous_digest: str | None = None) -> str:
    combined = ""
    for cat, summary in category_summaries.items():
        if summary:
            combined += f"[{cat}]\n{summary}\n\n"

    if not combined.strip():
        return ""

    prompt = "Here are today's news summaries by category. Combine them into a single spoken morning briefing:\n\n" + combined

    if previous_digest:
        prompt += f"---\nYesterday's briefing (for reference — do NOT repeat, but link continuing stories where relevant):\n\n{previous_digest}\n"

    digest = _call_llm(PASS2_SYSTEM, prompt)

    for attempt in range(MAX_RETRIES + 1):
        word_count = len(digest.split())
        if 390 <= word_count <= 460:
            break
        logger.info("Digest word count %d outside range (attempt %d), retrying", word_count, attempt + 1)
        retry_prompt = (
            f"{prompt}\n\nCRITICAL: Your previous response was {word_count} words. "
            f"You MUST write between 400 and 450 words. Cut content if over, expand if under."
        )
        digest = _call_llm(PASS2_SYSTEM, retry_prompt)

    return digest


CLASSIFY_SYSTEM = """You are a news classifier. For each numbered item, assign exactly one subcategory from the provided list.
Respond with ONLY one line per item in the format: NUMBER:subcategory_id
No explanations, no extra text."""

CLASSIFY_BATCH_SIZE = 25


def classify_rss_items(category: str, items: list[dict]) -> dict[str, str]:
    sub_options = SUBCATEGORIES.get(category, [])
    if not sub_options or not items:
        return {}

    options_str = ", ".join(f'{s["id"]} ({s["name"]})' for s in sub_options)
    updates: dict[str, str] = {}
    valid_ids = {s["id"] for s in sub_options}

    for i in range(0, len(items), CLASSIFY_BATCH_SIZE):
        batch = items[i:i + CLASSIFY_BATCH_SIZE]
        lines = []
        for j, item in enumerate(batch, 1):
            line = f"{j}. {item['title']}"
            if item.get("summary"):
                line += f" — {item['summary'][:150]}"
            lines.append(line)

        prompt = (
            f"Category: {category}\n"
            f"Subcategories: {options_str}\n\n"
            f"Items:\n" + "\n".join(lines)
        )

        try:
            response = _call_llm(CLASSIFY_SYSTEM, prompt)
        except Exception as e:
            logger.warning("Classification LLM call failed for %s: %s", category, e)
            continue

        for line in response.strip().splitlines():
            line = line.strip()
            if ":" not in line:
                continue
            num_str, sub_id = line.split(":", 1)
            sub_id = sub_id.strip()
            try:
                idx = int(num_str.strip()) - 1
            except ValueError:
                continue
            if 0 <= idx < len(batch) and sub_id in valid_ids:
                updates[batch[idx]["id"]] = sub_id

    logger.info("Classified %d/%d items for %s", len(updates), len(items), category)
    return updates


def build_user_digest(
    user_subcategories: dict[str, list[str]],
    previous_digest: str | None = None,
) -> str:
    category_summaries: dict[str, str] = {}
    for category, subcategories in user_subcategories.items():
        sub_summaries = []
        for sub in subcategories:
            summary = summarize_subcategory(category, sub)
            if summary:
                sub_summaries.append(summary)
        if sub_summaries:
            category_summaries[category] = "\n\n".join(sub_summaries)

    return generate_digest(category_summaries, previous_digest)


def clear_cache():
    _pass1_cache.clear()
