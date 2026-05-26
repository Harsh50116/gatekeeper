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
TOOL_USE_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
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


SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current or detailed information not available in the digest or conversation history. Use when the user asks about something not covered, wants more detail than available, or asks for current/live/latest data.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A specific search query. Resolve pronouns and references from conversation history before generating the query.",
                }
            },
            "required": ["query"],
        },
    },
}

ROUTE_SYSTEM = """You are a news digest assistant. The user is asking a follow-up question while listening to their morning digest.

You have the digest text and recent conversation history. Answer directly if you have enough information. Use the web_search tool if you need more.

When answering directly:
- Be concise and to the point unless the user asks for detail.
- Spoken format: no markdown, no preamble, spell out numbers.
- If the question contains a false assumption, correct it.

When to use web_search:
- The user asks for details beyond what's in the digest or conversation.
- The user asks for current, latest, or live data.
- The user wants to know more about a topic only briefly mentioned.
- You can only partially answer and need more information."""


def route_question(question: str, digest: str, context: str) -> dict:
    client = _get_client()

    user_prompt = f"Digest:\n{digest}\n\n"
    if context:
        user_prompt += f"Conversation so far:\n{context}\n\n"
    user_prompt += f"User's question: {question}"

    t0 = time.time()
    resp = client.chat.completions.create(
        model=TOOL_USE_MODEL,
        messages=[
            {"role": "system", "content": ROUTE_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        tools=[SEARCH_TOOL],
        tool_choice="auto",
        temperature=0.2,
        max_completion_tokens=4096,
    )
    latency = round(time.time() - t0, 3)
    usage = resp.usage

    message = resp.choices[0].message
    result = {
        "latency": latency,
        "tokens_in": usage.prompt_tokens if usage else 0,
        "tokens_out": usage.completion_tokens if usage else 0,
    }

    if message.tool_calls:
        tool_call = message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        result["action"] = "search"
        result["search_query"] = args["query"]
        result["text"] = None
    else:
        result["action"] = "answer"
        result["text"] = message.content.strip() if message.content else ""
        result["search_query"] = None

    return result


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
    route = entry["route"]

    print(f"\n{sep}")
    print(f"  [ASK] Turn {entry['turn']}  [{src}]  session={entry['session_id'][:12]}…")
    print(f"{sep}")
    print(f"  Question:       {entry['question']}")
    print(f"  Route:          {route['action']}")
    print(f"                  {route['latency_s']}s  tokens: {route['tokens_in']}→{route['tokens_out']}")

    if used_search:
        ret = entry["retrieval"]
        syn = entry["synthesis"]
        print(f"  Search query:   {route['search_query']}")
        print(f"  Results:        {ret['result_count']} hits  {ret['latency_s']}s")
        for t in ret["titles"][:3]:
            print(f"                  • {t[:70]}")
        if ret["result_count"] > 3:
            print(f"                  … +{ret['result_count'] - 3} more")
        print(f"  Answer:         {syn['answer']}")
        print(f"                  {syn['word_count']} words  {syn['latency_s']}s  tokens: {syn['tokens_in']}→{syn['tokens_out']}")
    else:
        print(f"  Answer:         {route['answer']}")
        print(f"                  {route['word_count']} words")

    total = route["latency_s"]
    if used_search:
        total += ret["latency_s"] + syn["latency_s"]
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

    # Step 1 — Route: answer directly or call web_search
    route = route_question(question, digest, context)
    used_search = route["action"] == "search"

    if used_search:
        # Step 2 — Retrieval
        t0 = time.time()
        search_results = web_search(route["search_query"])
        search_latency = round(time.time() - t0, 3)

        # Step 3 — Synthesis
        answer_result = synthesize_answer(question, search_results, digest, context)
        answer = answer_result["text"]
    else:
        answer = route["text"]
        search_results = []
        search_latency = 0
        answer_result = None

    answer_word_count = len(answer.split())

    log_entry = {
        "event": "ask_turn",
        "session_id": session_id,
        "turn": turn_index,
        "question": question,
        "used_search": used_search,
        "route": {
            "action": route["action"],
            "latency_s": route["latency"],
            "tokens_in": route["tokens_in"],
            "tokens_out": route["tokens_out"],
        },
    }

    if used_search:
        log_entry["route"]["search_query"] = route["search_query"]
        log_entry["retrieval"] = {
            "result_count": len(search_results),
            "titles": [r.get("title", "") for r in search_results],
            "latency_s": search_latency,
        }
        log_entry["synthesis"] = {
            "answer": answer,
            "word_count": answer_word_count,
            "latency_s": answer_result["latency"],
            "tokens_in": answer_result["tokens_in"],
            "tokens_out": answer_result["tokens_out"],
        }
    else:
        log_entry["route"]["answer"] = answer
        log_entry["route"]["word_count"] = answer_word_count

    _print_log(log_entry, used_search)

    session["recent_turns"].append({"q": question, "a": answer})

    if len(session["recent_turns"]) > MAX_RECENT_TURNS:
        oldest = session["recent_turns"].pop(0)
        session["older_summary"] = _resummarize(session["older_summary"], oldest)

    update_session(session_id, session)

    return {"question": question, "answer": answer}
