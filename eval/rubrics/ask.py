"""
Rubric checks for the Q&A (Ask Balto) pipeline.
Layer 1 = search query quality, Layer 3 = answer quality.
Layer 2 (retrieval) is logged but not auto-scored — Tavily results are external.
"""

import re

# --- Layer 1: Search query checks ---

PREAMBLE_PHRASES = [
    "great question", "good question", "sure", "absolutely",
    "of course", "that's a great", "well,", "so,", "let me",
    "i'd be happy", "certainly",
]

UNRESOLVED_PRONOUNS = ["he", "she", "they", "it", "that", "this", "those", "these"]


def check_query_non_empty(query: str) -> dict:
    passed = len(query.strip()) > 0
    return {"check": "query_non_empty", "passed": passed, "detail": query if not passed else ""}


def check_query_not_verbatim(query: str, question: str) -> dict:
    passed = query.strip().lower() != question.strip().lower()
    return {
        "check": "query_not_verbatim_copy",
        "passed": passed,
        "detail": "Search query is just the raw question repeated" if not passed else "",
    }


def check_query_no_unresolved_pronouns(query: str) -> dict:
    words = re.findall(r'\b\w+\b', query.lower())
    found = [w for w in words if w in UNRESOLVED_PRONOUNS]
    if not found:
        return {"check": "query_no_unresolved_pronouns", "passed": True, "detail": ""}
    return {
        "check": "query_no_unresolved_pronouns",
        "passed": False,
        "detail": f"Possible unresolved pronouns: {', '.join(found)}",
    }


def check_query_min_length(query: str, min_words: int = 3) -> dict:
    word_count = len(query.split())
    passed = word_count >= min_words
    return {
        "check": "query_min_length",
        "passed": passed,
        "detail": f"Query has {word_count} words, minimum is {min_words}" if not passed else "",
    }


# --- Layer 3: Answer checks ---

def check_answer_word_count(answer: str, max_words: int = 40) -> dict:
    word_count = len(answer.split())
    passed = word_count <= max_words
    return {
        "check": "answer_word_count",
        "passed": passed,
        "detail": f"{word_count} words (max {max_words})" if not passed else f"{word_count} words",
    }


def check_answer_no_preamble(answer: str) -> dict:
    lower = answer.lower().strip()
    found = [p for p in PREAMBLE_PHRASES if lower.startswith(p)]
    passed = len(found) == 0
    return {
        "check": "answer_no_preamble",
        "passed": passed,
        "detail": f"Starts with: '{found[0]}'" if not passed else "",
    }


def check_answer_no_markdown(answer: str) -> dict:
    patterns = [
        (r'\*\*.*?\*\*', "bold"),
        (r'\*.*?\*', "italic"),
        (r'^[-*]\s', "bullet"),
        (r'^#{1,6}\s', "header"),
        (r'\[.*?\]\(.*?\)', "link"),
        (r'`.*?`', "code"),
        (r'^>\s', "blockquote"),
    ]
    found = []
    for pattern, name in patterns:
        if re.search(pattern, answer, re.MULTILINE):
            found.append(name)
    passed = len(found) == 0
    return {
        "check": "answer_no_markdown",
        "passed": passed,
        "detail": f"Found: {', '.join(found)}" if not passed else "",
    }


def check_answer_no_links(answer: str) -> dict:
    has_url = bool(re.search(r'https?://\S+', answer))
    return {
        "check": "answer_no_links",
        "passed": not has_url,
        "detail": "Contains URL" if has_url else "",
    }


# --- Run all checks ---

def run_layer1_checks(query: str, question: str) -> list[dict]:
    return [
        check_query_non_empty(query),
        check_query_not_verbatim(query, question),
        check_query_no_unresolved_pronouns(query),
        check_query_min_length(query),
    ]


def run_layer3_checks(answer: str) -> list[dict]:
    return [
        check_answer_word_count(answer),
        check_answer_no_preamble(answer),
        check_answer_no_markdown(answer),
        check_answer_no_links(answer),
    ]


def run_all_checks(query: str, question: str, answer: str) -> dict:
    layer1 = run_layer1_checks(query, question)
    layer3 = run_layer3_checks(answer)

    all_checks = layer1 + layer3
    passed = sum(1 for c in all_checks if c["passed"])
    total = len(all_checks)

    return {
        "layer_1": layer1,
        "layer_3": layer3,
        "summary": f"{passed}/{total} passed",
        "all_passed": passed == total,
    }
