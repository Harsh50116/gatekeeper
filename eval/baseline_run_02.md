Running 8 fixture(s)...

  Running: ambiguous_followup_01... [PASS]
  Running: bad_premise_01... [PASS]
  Running: context_recall_01... [PASS]
  Running: current_fact_01... [PASS]
  Running: digest_dependent_01... [PASS]
  Running: fact_lookup_01... [PASS]
  Running: pronoun_heavy_01... [PASS]
  Running: unanswerable_01... [PASS]

============================================================
  ambiguous_followup_01  [PASS]  (8/8 passed)  [SEARCH]
============================================================
  Question:      Tell me more about that
  Source:        Web search
  Search query:  EU AI regulation oversight body requirements
  Results:       5 hits
  Answer:        The EU AI regulation requires registration and fines up to six percent of global revenue for non-compliance, with a focus on high-risk systems and human oversight.
  Words:         26
  Latency:       check=0.242s  query=0.2s  search=1.948s  synth=0.438s  total=2.828s

  Layer 1 checks:
    ✓ query_non_empty
    ✓ query_not_verbatim_copy
    ✓ query_no_unresolved_pronouns
    ✓ query_min_length

  Layer 3 checks:
    ✓ answer_word_count  — 26 words
    ✓ answer_no_preamble
    ✓ answer_no_markdown
    ✓ answer_no_links

  Expected: Should resolve "that" to the EU AI regulation from the prior turn. Search query should be about EU AI regulation details...

============================================================
  bad_premise_01  [PASS]  (4/4 passed)  [DIGEST]
============================================================
  Question:      Why did Apple acquire Anthropic?
  Source:        Digest only
  Answer:        That is incorrect, the digest states Google led the funding round for Anthropic, not Apple acquiring it.
  Words:         17
  Latency:       check=0.191s  total=0.191s

  Layer 3 checks:
    ✓ answer_word_count  — 17 words
    ✓ answer_no_preamble
    ✓ answer_no_markdown
    ✓ answer_no_links

  Expected: Apple did not acquire Anthropic — the digest says Anthropic raised funding led by Google. The model must correct the false assumption...

============================================================
  context_recall_01  [PASS]  (4/4 passed)  [DIGEST]
============================================================
  Question:      How many goals did he score?
  Source:        Digest only
  Answer:        He scored two goals.
  Words:         4
  Latency:       check=0.258s  total=0.258s

  Layer 3 checks:
    ✓ answer_word_count  — 4 words
    ✓ answer_no_preamble
    ✓ answer_no_markdown
    ✓ answer_no_links

  Expected: The answer is already in the conversation history — "Lewandowski scored twice." The model should resolve "he" to Lewandowski...

============================================================
  current_fact_01  [PASS]  (8/8 passed)  [SEARCH]
============================================================
  Question:      What's the current ten-year Treasury yield?
  Source:        Web search
  Search query:  current ten-year Treasury yield
  Results:       5 hits
  Answer:        four point one percent
  Words:         4
  Latency:       check=0.123s  query=0.148s  search=3.814s  synth=0.235s  total=4.32s

  Layer 1 checks:
    ✓ query_non_empty
    ✓ query_not_verbatim_copy
    ✓ query_no_unresolved_pronouns
    ✓ query_min_length

  Layer 3 checks:
    ✓ answer_word_count  — 4 words
    ✓ answer_no_preamble
    ✓ answer_no_markdown
    ✓ answer_no_links

  Expected: The digest mentions 4.1% but the user asks for "current" — the search should look for the latest ten-year Treasury yield...

============================================================
  digest_dependent_01  [PASS]  (8/8 passed)  [SEARCH]
============================================================
  Question:      How does their revenue compare to other payment companies?
  Source:        Web search
  Search query:  Stripe revenue comparison to other payment companies
  Results:       5 hits
  Answer:        Stripe's revenue is twenty-two billion dollars, higher than Adyen's but lower than PayPal's.
  Words:         13
  Latency:       check=0.132s  query=0.149s  search=1.682s  synth=0.5s  total=2.463s

  Layer 1 checks:
    ✓ query_non_empty
    ✓ query_not_verbatim_copy
    ✓ query_no_unresolved_pronouns
    ✓ query_min_length

  Layer 3 checks:
    ✓ answer_word_count  — 13 words
    ✓ answer_no_preamble
    ✓ answer_no_markdown
    ✓ answer_no_links

  Expected: Must connect "their revenue" to Stripe's twenty-two billion from the digest. Search query should compare Stripe revenue...

============================================================
  fact_lookup_01  [PASS]  (4/4 passed)  [DIGEST]
============================================================
  Question:      What was the Celtics score?
  Source:        Digest only
  Answer:        The Celtics scored one hundred and twelve points.
  Words:         8
  Latency:       check=0.208s  total=0.208s

  Layer 3 checks:
    ✓ answer_word_count  — 8 words
    ✓ answer_no_preamble
    ✓ answer_no_markdown
    ✓ answer_no_links

  Expected: Answer should come directly from the digest without needing search: Celtics beat Heat 112-98 in game 5. Jaylen Brown scored 34 points...

============================================================
  pronoun_heavy_01  [PASS]  (4/4 passed)  [DIGEST]
============================================================
  Question:      When did he announce it?
  Source:        Digest only
  Answer:        He announced it during a keynote in Taipei.
  Words:         8
  Latency:       check=0.258s  total=0.258s

  Layer 3 checks:
    ✓ answer_word_count  — 8 words
    ✓ answer_no_preamble
    ✓ answer_no_markdown
    ✓ answer_no_links

  Expected: Must resolve "he" to Jensen Huang and "it" to the Blackwell Ultra chip. Search query should reference Jensen Huang or Nvidia...

============================================================
  unanswerable_01  [PASS]  (8/8 passed)  [SEARCH]
============================================================
  Question:      What will Samsung's stock price be next week?
  Source:        Web search
  Search query:  Samsung stock price forecast next week
  Results:       5 hits
  Answer:        I don't have that information.
  Words:         5
  Latency:       check=0.132s  query=0.267s  search=0.048s  synth=7.53s  total=7.977s

  Layer 1 checks:
    ✓ query_non_empty
    ✓ query_not_verbatim_copy
    ✓ query_no_unresolved_pronouns
    ✓ query_min_length

  Layer 3 checks:
    ✓ answer_word_count  — 5 words
    ✓ answer_no_preamble
    ✓ answer_no_markdown
    ✓ answer_no_links

  Expected: This is a prediction request — no search result can answer it. The model should decline clearly ("I don't have that information")...

============================================================
  SUMMARY: 8/8 fixtures passed
  Avg total latency: 2.313s
  Latency p50: 2.463s  p95: 7.977s
============================================================

Changes from baseline_run_01:
- Added digest-first check: questions answerable from digest/context skip Tavily entirely
- fact_lookup_01: now [DIGEST] with correct score (was [SEARCH] with wrong score "113-97")
- bad_premise_01: now [DIGEST] and corrects false assumption (was "I don't have that information")
- context_recall_01: new fixture, [DIGEST], answers from conversation history
- pronoun_heavy_01: now [DIGEST] (was [SEARCH] with 13.6s latency)
- Avg latency dropped from 6.701s to 2.313s
- p95 dropped from 16.635s to 7.977s
