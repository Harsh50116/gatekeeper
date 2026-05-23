import json
import logging
import os
import time

from groq import Groq

from .search import web_search
from .session import get_session, update_session

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL = "llama-3.3-70b-versatile"
MAX_RECENT_TURNS = 3


def _get_client() -> Groq:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in environment")
    return Groq(api_key=GROQ_API_KEY)


def _call_llm(system: str, user: str, max_tokens: int = 512) -> dict:
    client = _get_client()
    t0 = time.time()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=max_tokens,
    )
    latency = round(time.time() - t0, 3)
    usage = resp.usage
    return {
        "text": resp.choices[0].message.content.strip(),
        "latency": latency,
        "tokens_in": usage.prompt_tokens if usage else 0,
        "tokens_out": usage.completion_tokens if usage else 0,
    }


def _build_context(session: dict) -> str:
    parts = []
    if session["older_summary"]:
        parts.append(f"Previous conversation summary:\n{session['older_summary']}")
    for turn in session["recent_turns"]:
        parts.append(f"User asked: {turn['q']}\nAnswer: {turn['a']}")
    return "\n\n".join(parts)


SEARCH_QUERY_SYSTEM = """You generate web search queries. Given a user's question and context from a news digest, produce a single concise search query that would find detailed information to answer the question. Return ONLY the search query, nothing else."""


def generate_search_query(question: str, digest: str, context: str) -> dict:
    user_prompt = f"Digest:\n{digest}\n\n"
    if context:
        user_prompt += f"Conversation so far:\n{context}\n\n"
    user_prompt += f"User's question: {question}"
    return _call_llm(SEARCH_QUERY_SYSTEM, user_prompt)


ANSWER_SYSTEM = """You answer follow-up questions about a news digest. You MUST reply in 1-2 sentences only. Never exceed 40 words.

Rules:
- Answer ONLY what was asked. No background, no context, no elaboration.
- No preamble. Start with the answer immediately.
- Spoken format — no markdown, no bullets, no links, no quotes.
- Spell out numbers: "twenty three" not "23".
- If unknown, say "I don't have that information" and nothing else."""


def synthesize_answer(question: str, search_results: list[dict], digest: str, context: str) -> dict:
    results_text = ""
    for r in search_results:
        results_text += f"Title: {r['title']}\n{r['content']}\n\n"

    user_prompt = f"Digest:\n{digest}\n\n"
    if context:
        user_prompt += f"Conversation so far:\n{context}\n\n"
    user_prompt += f"User's question: {question}\n\nSearch results:\n{results_text}"
    return _call_llm(ANSWER_SYSTEM, user_prompt, max_tokens=100)


SUMMARIZE_SYSTEM = """Summarize the following conversation history into a brief paragraph. Capture the key questions asked and facts learned. Be concise — this summary will be used as context for future questions."""


def _resummarize(older_summary: str, turn: dict) -> str:
    text = ""
    if older_summary:
        text += f"Previous summary:\n{older_summary}\n\n"
    text += f"New exchange:\nUser asked: {turn['q']}\nAnswer: {turn['a']}"
    result = _call_llm(SUMMARIZE_SYSTEM, text)
    return result["text"]


def handle_question(session_id: str, question: str) -> dict:
    session = get_session(session_id)
    if session is None:
        raise ValueError("Session not found or expired")

    digest = session["digest"]
    context = _build_context(session)
    turn_index = len(session["recent_turns"]) + 1

    # Layer 1 — Search query generation
    query_result = generate_search_query(question, digest, context)
    search_query = query_result["text"]

    # Layer 2 — Retrieval
    t0 = time.time()
    search_results = web_search(search_query)
    search_latency = round(time.time() - t0, 3)

    # Layer 3 — Synthesis
    answer_result = synthesize_answer(question, search_results, digest, context)
    answer = answer_result["text"]
    answer_word_count = len(answer.split())

    # Structured log
    log_entry = {
        "event": "ask_turn",
        "session_id": session_id,
        "turn": turn_index,
        "question": question,
        "layer_1_query": {
            "generated_query": search_query,
            "latency_s": query_result["latency"],
            "tokens_in": query_result["tokens_in"],
            "tokens_out": query_result["tokens_out"],
        },
        "layer_2_retrieval": {
            "result_count": len(search_results),
            "titles": [r.get("title", "") for r in search_results],
            "latency_s": search_latency,
        },
        "layer_3_synthesis": {
            "answer": answer,
            "word_count": answer_word_count,
            "latency_s": answer_result["latency"],
            "tokens_in": answer_result["tokens_in"],
            "tokens_out": answer_result["tokens_out"],
        },
    }
    print(f"[ASK] {json.dumps(log_entry)}")

    session["recent_turns"].append({"q": question, "a": answer})

    if len(session["recent_turns"]) > MAX_RECENT_TURNS:
        oldest = session["recent_turns"].pop(0)
        session["older_summary"] = _resummarize(session["older_summary"], oldest)

    update_session(session_id, session)

    return {"question": question, "answer": answer}
