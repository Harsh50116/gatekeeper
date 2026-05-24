"""
Runner script for Q&A eval fixtures.
Loads each fixture, runs it through the ask chain, applies rubric checks,
and prints a per-fixture, per-layer report.

Usage:
  python -m eval.run_ask_eval                    # run all fixtures
  python -m eval.run_ask_eval fact_lookup_01      # run one fixture
"""

import json
import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()

from digest.ask.interactive import generate_search_query, synthesize_answer, try_digest_answer, SEARCH_NEEDED_TOKEN
from digest.ask.search import web_search
from eval.rubrics.ask import run_all_checks

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "ask")


def load_fixture(fixture_dir: str) -> dict:
    fixture = {"name": os.path.basename(fixture_dir)}

    with open(os.path.join(fixture_dir, "digest.txt")) as f:
        fixture["digest"] = f.read().strip()

    with open(os.path.join(fixture_dir, "question.txt")) as f:
        fixture["question"] = f.read().strip()

    turns_path = os.path.join(fixture_dir, "prior_turns.json")
    if os.path.exists(turns_path):
        with open(turns_path) as f:
            fixture["prior_turns"] = json.load(f)
    else:
        fixture["prior_turns"] = []

    themes_path = os.path.join(fixture_dir, "expected_search_themes.txt")
    if os.path.exists(themes_path):
        with open(themes_path) as f:
            fixture["expected_themes"] = f.read().strip()
    else:
        fixture["expected_themes"] = ""

    return fixture


def build_context_from_turns(prior_turns: list) -> str:
    parts = []
    for turn in prior_turns:
        parts.append(f"User asked: {turn['q']}\nAnswer: {turn['a']}")
    return "\n\n".join(parts)


def run_fixture(fixture: dict) -> dict:
    name = fixture["name"]
    question = fixture["question"]
    digest = fixture["digest"]
    context = build_context_from_turns(fixture["prior_turns"])

    # Step 0 — Try digest first
    digest_check = try_digest_answer(question, digest, context)
    digest_response = digest_check["text"]
    used_search = SEARCH_NEEDED_TOKEN in digest_response

    if used_search:
        # Layer 1 — Search query generation
        query_result = generate_search_query(question, digest, context)
        search_query = query_result["text"]

        # Layer 2 — Retrieval
        t0 = time.time()
        search_results = web_search(search_query)
        l2_latency = round(time.time() - t0, 3)

        # Layer 3 — Synthesis
        answer_result = synthesize_answer(question, search_results, digest, context)
        answer = answer_result["text"]

        checks = run_all_checks(search_query, question, answer)

        total_latency = round(digest_check["latency"] + query_result["latency"] + l2_latency + answer_result["latency"], 3)

        return {
            "name": name,
            "question": question,
            "used_search": True,
            "digest_check_latency": digest_check["latency"],
            "search_query": search_query,
            "result_count": len(search_results),
            "result_titles": [r.get("title", "") for r in search_results[:3]],
            "answer": answer,
            "answer_words": len(answer.split()),
            "latency": {"digest_check": digest_check["latency"], "query": query_result["latency"], "search": l2_latency, "synthesis": answer_result["latency"], "total": total_latency},
            "tokens": {
                "digest_check": {"in": digest_check["tokens_in"], "out": digest_check["tokens_out"]},
                "query": {"in": query_result["tokens_in"], "out": query_result["tokens_out"]},
                "synthesis": {"in": answer_result["tokens_in"], "out": answer_result["tokens_out"]},
            },
            "checks": checks,
            "expected_themes": fixture["expected_themes"],
        }
    else:
        answer = digest_response
        from eval.rubrics.ask import run_layer3_checks
        layer3 = run_layer3_checks(answer)
        passed = sum(1 for c in layer3 if c["passed"])
        total = len(layer3)
        checks = {
            "layer_1": [],
            "layer_3": layer3,
            "summary": f"{passed}/{total} passed",
            "all_passed": passed == total,
        }

        return {
            "name": name,
            "question": question,
            "used_search": False,
            "search_query": None,
            "result_count": 0,
            "result_titles": [],
            "answer": answer,
            "answer_words": len(answer.split()),
            "latency": {"digest_check": digest_check["latency"], "total": digest_check["latency"]},
            "tokens": {
                "digest_check": {"in": digest_check["tokens_in"], "out": digest_check["tokens_out"]},
            },
            "checks": checks,
            "expected_themes": fixture["expected_themes"],
        }


def print_result(result: dict):
    status = "PASS" if result["checks"]["all_passed"] else "FAIL"
    source = "SEARCH" if result["used_search"] else "DIGEST"
    print(f"\n{'='*60}")
    print(f"  {result['name']}  [{status}]  ({result['checks']['summary']})  [{source}]")
    print(f"{'='*60}")
    print(f"  Question:      {result['question']}")
    print(f"  Source:        {'Web search' if result['used_search'] else 'Digest only'}")

    if result["used_search"]:
        print(f"  Search query:  {result['search_query']}")
        print(f"  Results:       {result['result_count']} hits")

    print(f"  Answer:        {result['answer']}")
    print(f"  Words:         {result['answer_words']}")

    lat = result["latency"]
    if result["used_search"]:
        print(f"  Latency:       check={lat['digest_check']}s  query={lat['query']}s  search={lat['search']}s  synth={lat['synthesis']}s  total={lat['total']}s")
    else:
        print(f"  Latency:       check={lat['digest_check']}s  total={lat['total']}s")

    if result["used_search"]:
        print(f"\n  Layer 1 checks:")
        for c in result["checks"]["layer_1"]:
            mark = "✓" if c["passed"] else "✗"
            detail = f"  — {c['detail']}" if c["detail"] else ""
            print(f"    {mark} {c['check']}{detail}")

    print(f"\n  Layer 3 checks:")
    for c in result["checks"]["layer_3"]:
        mark = "✓" if c["passed"] else "✗"
        detail = f"  — {c['detail']}" if c["detail"] else ""
        print(f"    {mark} {c['check']}{detail}")

    if result["expected_themes"]:
        print(f"\n  Expected: {result['expected_themes'][:120]}...")


def main():
    filter_name = sys.argv[1] if len(sys.argv) > 1 else None

    fixture_dirs = sorted([
        os.path.join(FIXTURES_DIR, d)
        for d in os.listdir(FIXTURES_DIR)
        if os.path.isdir(os.path.join(FIXTURES_DIR, d))
    ])

    if filter_name:
        fixture_dirs = [d for d in fixture_dirs if filter_name in os.path.basename(d)]
        if not fixture_dirs:
            print(f"No fixture matching '{filter_name}'")
            sys.exit(1)

    print(f"Running {len(fixture_dirs)} fixture(s)...\n")

    results = []
    for fdir in fixture_dirs:
        fixture = load_fixture(fdir)
        print(f"  Running: {fixture['name']}...", end="", flush=True)
        result = run_fixture(fixture)
        results.append(result)
        status = "PASS" if result["checks"]["all_passed"] else "FAIL"
        print(f" [{status}]")

    # Print detailed results
    for r in results:
        print_result(r)

    # Summary
    passed = sum(1 for r in results if r["checks"]["all_passed"])
    total = len(results)
    latencies = [r["latency"]["total"] for r in results]
    avg_latency = round(sum(latencies) / len(latencies), 3) if latencies else 0

    print(f"\n{'='*60}")
    print(f"  SUMMARY: {passed}/{total} fixtures passed")
    print(f"  Avg total latency: {avg_latency}s")
    if latencies:
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        print(f"  Latency p50: {p50}s  p95: {p95}s")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
