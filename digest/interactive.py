import logging
import os

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


def _call_llm(system: str, user: str) -> str:
    client = _get_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=512,
    )
    return resp.choices[0].message.content.strip()


def _build_context(session: dict) -> str:
    parts = []
    if session["older_summary"]:
        parts.append(f"Previous conversation summary:\n{session['older_summary']}")
    for turn in session["recent_turns"]:
        parts.append(f"User asked: {turn['q']}\nAnswer: {turn['a']}")
    return "\n\n".join(parts)


SEARCH_QUERY_SYSTEM = """You generate web search queries. Given a user's question and context from a news digest, produce a single concise search query that would find detailed information to answer the question. Return ONLY the search query, nothing else."""


def generate_search_query(question: str, digest: str, context: str) -> str:
    user_prompt = f"Digest:\n{digest}\n\n"
    if context:
        user_prompt += f"Conversation so far:\n{context}\n\n"
    user_prompt += f"User's question: {question}"
    return _call_llm(SEARCH_QUERY_SYSTEM, user_prompt)


ANSWER_SYSTEM = """You are a helpful audio news assistant. The user is listening to a morning news digest and asked a follow-up question. Using the search results provided, give a clear, conversational answer meant to be spoken aloud.

Rules:
- Keep it to 2-4 sentences, concise and informative.
- Write as if speaking — no markdown, no bullet points, no links.
- Spell out numbers: "twenty three" not "23".
- If the search results don't have a clear answer, say so honestly."""


def synthesize_answer(question: str, search_results: list[dict], digest: str, context: str) -> str:
    results_text = ""
    for r in search_results:
        results_text += f"Title: {r['title']}\n{r['content']}\n\n"

    user_prompt = f"Digest:\n{digest}\n\n"
    if context:
        user_prompt += f"Conversation so far:\n{context}\n\n"
    user_prompt += f"User's question: {question}\n\nSearch results:\n{results_text}"
    return _call_llm(ANSWER_SYSTEM, user_prompt)


SUMMARIZE_SYSTEM = """Summarize the following conversation history into a brief paragraph. Capture the key questions asked and facts learned. Be concise — this summary will be used as context for future questions."""


def _resummarize(older_summary: str, turn: dict) -> str:
    text = ""
    if older_summary:
        text += f"Previous summary:\n{older_summary}\n\n"
    text += f"New exchange:\nUser asked: {turn['q']}\nAnswer: {turn['a']}"
    return _call_llm(SUMMARIZE_SYSTEM, text)


def handle_question(session_id: str, question: str) -> dict:
    session = get_session(session_id)
    if session is None:
        raise ValueError("Session not found or expired")

    digest = session["digest"]
    context = _build_context(session)

    search_query = generate_search_query(question, digest, context)
    logger.info("Search query: %s", search_query)

    search_results = web_search(search_query)

    answer = synthesize_answer(question, search_results, digest, context)
    logger.info("Answer: %s", answer[:100])

    session["recent_turns"].append({"q": question, "a": answer})

    if len(session["recent_turns"]) > MAX_RECENT_TURNS:
        oldest = session["recent_turns"].pop(0)
        session["older_summary"] = _resummarize(session["older_summary"], oldest)

    update_session(session_id, session)

    return {"question": question, "answer": answer}
