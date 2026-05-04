import logging
import os
from collections import defaultdict

import httpx

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
        timeout=60.0,
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


def summarize_category(category: str, items: list[dict]) -> str:
    if category in _pass1_cache:
        return _pass1_cache[category]

    if not items:
        return ""

    if len(items) <= 5:
        block = _format_items_block(items)
        prompt = f"Category: {category}\n\n{block}"
        summary = _call_llm(PASS1_SYSTEM, prompt)
    else:
        by_source: dict[str, list[dict]] = defaultdict(list)
        for it in items:
            by_source[it["source"]].append(it)

        source_summaries = []
        for source, source_items in by_source.items():
            block = _format_items_block(source_items)
            prompt = f"Category: {category}, Source: {source}\n\n{block}"
            summary = _call_llm(PASS1_SYSTEM, prompt)
            source_summaries.append(summary)

        summary = "\n\n".join(source_summaries)

    _pass1_cache[category] = summary
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
- Write complete flowing paragraphs meant to be read aloud."""


def generate_digest(category_summaries: dict[str, str]) -> str:
    combined = ""
    for cat, summary in category_summaries.items():
        if summary:
            combined += f"[{cat}]\n{summary}\n\n"

    if not combined.strip():
        return ""

    prompt = f"Here are today's news summaries by category. Combine them into a single spoken morning briefing:\n\n{combined}"

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


def build_user_digest(user_items: dict[str, list[dict]]) -> str:
    category_summaries = {}
    for category, items in user_items.items():
        category_summaries[category] = summarize_category(category, items)

    return generate_digest(category_summaries)


def clear_cache():
    _pass1_cache.clear()
