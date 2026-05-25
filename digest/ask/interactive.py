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


DIGEST_CHECK_SYSTEM = """You are a news digest assistant. The user asked a follow-up question while listening to their morning digest. Decide if the digest and conversation history contain enough information to answer the question fully and accurately.

Rules:
- If the digest or conversation history contains the specific facts needed, answer directly in 1-2 sentences (under 40 words). Follow the same spoken format rules: no markdown, no preamble, spell out numbers.
- If the question asks for "current", "latest", "live", or "right now" data — reply SEARCH_NEEDED.
- If the question asks for information NOT in the digest or conversation — reply SEARCH_NEEDED.
- If the question contains a false assumption that contradicts the digest, correct it directly.
- Reply with ONLY the answer or the word SEARCH_NEEDED. Nothing else."""

SEARCH_NEEDED_TOKEN = "SEARCH_NEEDED"


def try_digest_answer(question: str, digest: str, context: str) -> dict:
    user_prompt = f"Digest:\n{digest}\n\n"
    if context:
        user_prompt += f"Conversation so far:\n{context}\n\n"
    user_prompt += f"User's question: {question}"
    return _call_llm(DIGEST_CHECK_SYSTEM, user_prompt, max_tokens=100)


SEARCH_QUERY_SYSTEM = """You generate web search queries for a news digest assistant.

Steps:
1. First, resolve what the user is referring to. Check the conversation history first, then the digest. Identify the specific topic, entity, or event — do not guess between multiple possibilities.
2. Then, build a concise search query about that specific topic to find the detailed information the user is asking for. Include key identifying details (names, locations, institutions) from the digest or conversation to make the query precise.

Return ONLY the final search query, nothing else."""


def generate_search_query(question: str, digest: str, context: str) -> dict:
    user_prompt = f"Digest:\n{digest}\n\n"
    if context:
        user_prompt += f"Conversation so far:\n{context}\n\n"
    user_prompt += f"User's question: {question}"
    return _call_llm(SEARCH_QUERY_SYSTEM, user_prompt)


ANSWER_SYSTEM = """You answer follow-up questions about a news digest. You MUST reply in 1-2 sentences only. Never exceed 40 words.

Rules:
- If the digest already contains the answer, use it directly. Prefer digest facts over search results.
- Answer ONLY what was asked. No background, no context, no elaboration.
- No preamble. Start with the answer immediately.
- Spoken format — no markdown, no bullets, no links, no quotes.
- Spell out numbers: "twenty three" not "23".
- If the question contains a false assumption, correct it. For example, if the user says "Why did X acquire Y?" but that never happened, say so.
- If genuinely unknown, say "I don't have that information" and nothing else.
- Give exactly one answer. Never follow up with a second statement or contradiction."""


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


def _print_log(entry: dict, used_search: bool):
    sep = "─" * 60
    src = "SEARCH" if used_search else "DIGEST"
    dc = entry["digest_check"]

    print(f"\n{sep}")
    print(f"  [ASK] Turn {entry['turn']}  [{src}]  session={entry['session_id'][:12]}…")
    print(f"{sep}")
    print(f"  Question:       {entry['question']}")
    print(f"  Digest check:   {dc['response'][:80]}{'…' if len(dc['response']) > 80 else ''}")
    print(f"                  {dc['latency_s']}s  tokens: {dc['tokens_in']}→{dc['tokens_out']}")

    if used_search:
        l1 = entry["layer_1_query"]
        l2 = entry["layer_2_retrieval"]
        l3 = entry["layer_3_synthesis"]
        print(f"  Search query:   {l1['generated_query']}")
        print(f"                  {l1['latency_s']}s  tokens: {l1['tokens_in']}→{l1['tokens_out']}")
        print(f"  Results:        {l2['result_count']} hits  {l2['latency_s']}s")
        for t in l2["titles"][:3]:
            print(f"                  • {t[:70]}")
        if l2["result_count"] > 3:
            print(f"                  … +{l2['result_count'] - 3} more")
        print(f"  Answer:         {l3['answer']}")
        print(f"                  {l3['word_count']} words  {l3['latency_s']}s  tokens: {l3['tokens_in']}→{l3['tokens_out']}")
    else:
        da = entry["digest_answer"]
        print(f"  Answer:         {da['answer']}")
        print(f"                  {da['word_count']} words")

    total = dc["latency_s"]
    if used_search:
        total = l1["latency_s"] + l2["latency_s"] + l3["latency_s"] + dc["latency_s"]
    print(f"  Total latency:  {round(total, 3)}s")
    print(sep)

    logger.debug("ask_turn_raw: %s", json.dumps(entry))


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

    # Step 0 — Try answering from digest + conversation history first
    digest_check = try_digest_answer(question, digest, context)
    digest_answer = digest_check["text"]
    used_search = False

    if SEARCH_NEEDED_TOKEN in digest_answer:
        # Digest can't answer — go to search
        used_search = True

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
    else:
        # Digest answered it directly
        answer = digest_answer
        search_query = None
        search_results = []
        search_latency = 0
        query_result = None
        answer_result = digest_check

    answer_word_count = len(answer.split())

    # Structured log
    log_entry = {
        "event": "ask_turn",
        "session_id": session_id,
        "turn": turn_index,
        "question": question,
        "used_search": used_search,
        "digest_check": {
            "response": digest_check["text"],
            "latency_s": digest_check["latency"],
            "tokens_in": digest_check["tokens_in"],
            "tokens_out": digest_check["tokens_out"],
        },
    }

    if used_search:
        log_entry["layer_1_query"] = {
            "generated_query": search_query,
            "latency_s": query_result["latency"],
            "tokens_in": query_result["tokens_in"],
            "tokens_out": query_result["tokens_out"],
        }
        log_entry["layer_2_retrieval"] = {
            "result_count": len(search_results),
            "titles": [r.get("title", "") for r in search_results],
            "latency_s": search_latency,
        }
        log_entry["layer_3_synthesis"] = {
            "answer": answer,
            "word_count": answer_word_count,
            "latency_s": answer_result["latency"],
            "tokens_in": answer_result["tokens_in"],
            "tokens_out": answer_result["tokens_out"],
        }
    else:
        log_entry["digest_answer"] = {
            "answer": answer,
            "word_count": answer_word_count,
        }

    _print_log(log_entry, used_search)

    session["recent_turns"].append({"q": question, "a": answer})

    if len(session["recent_turns"]) > MAX_RECENT_TURNS:
        oldest = session["recent_turns"].pop(0)
        session["older_summary"] = _resummarize(session["older_summary"], oldest)

    update_session(session_id, session)

    return {"question": question, "answer": answer}
