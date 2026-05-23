Running 7 fixture(s)...

  Running: ambiguous_followup_01... [PASS]
  Running: bad_premise_01... [PASS]
  Running: current_fact_01... [PASS]
  Running: digest_dependent_01... [PASS]
  Running: fact_lookup_01... [PASS]
  Running: pronoun_heavy_01... [PASS]
  Running: unanswerable_01... [PASS]

============================================================
  ambiguous_followup_01  [PASS]  (8/8 passed)
============================================================
  Question:      Tell me more about that
  Search query:  EU AI regulation oversight body requirements
  Results:       5 hits
  Answer:        The EU AI regulation requires transparency, risk assessments, and human oversight for high-risk systems, with fines up to six percent of global revenue for non-compliance.
  Words:         25
  Latency:       query=0.461s  search=1.695s  synth=0.531s  total=2.687s
  Tokens:        query(332→7)  synth(2161→33)

  Layer 1 checks:
    ✓ query_non_empty
    ✓ query_not_verbatim_copy
    ✓ query_no_unresolved_pronouns
    ✓ query_min_length

  Layer 3 checks:
    ✓ answer_word_count  — 25 words
    ✓ answer_no_preamble
    ✓ answer_no_markdown
    ✓ answer_no_links

  Expected: Should resolve "that" to the EU AI regulation from the prior turn. Search query should be about EU AI regulation details...

============================================================
  bad_premise_01  [PASS]  (8/8 passed)
============================================================
  Question:      Why did Apple acquire Anthropic?
  Search query:  "Apple acquisition of Anthropic"
  Results:       5 hits
  Answer:        I don't have that information.
  Words:         5
  Latency:       query=0.161s  search=2.294s  synth=0.338s  total=2.793s
  Tokens:        query(259→8)  synth(1731→8)

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

  Expected: Apple did not acquire Anthropic — the digest says Anthropic raised funding led by Google. The model must correct the fal...

============================================================
  current_fact_01  [PASS]  (8/8 passed)
============================================================
  Question:      What's the current ten-year Treasury yield?
  Search query:  current 10 year Treasury yield
  Results:       5 hits
  Answer:        The current ten-year Treasury yield is four point five nine percent.
  Words:         11
  Latency:       query=0.18s  search=3.695s  synth=0.399s  total=4.274s
  Tokens:        query(262→7)  synth(2921→14)

  Layer 1 checks:
    ✓ query_non_empty
    ✓ query_not_verbatim_copy
    ✓ query_no_unresolved_pronouns
    ✓ query_min_length

  Layer 3 checks:
    ✓ answer_word_count  — 11 words
    ✓ answer_no_preamble
    ✓ answer_no_markdown
    ✓ answer_no_links

  Expected: The digest mentions 4.1% but the user asks for "current" — the search should look for the latest ten-year Treasury yield...

============================================================
  digest_dependent_01  [PASS]  (8/8 passed)
============================================================
  Question:      How does their revenue compare to other payment companies?
  Search query:  Stripe revenue comparison to other payment companies
  Results:       5 hits
  Answer:        Stripe's revenue is significantly higher than Adyen's, with twenty-two billion dollars in revenue for the trailing twelve months. Stripe's revenue is also higher than PayPal's, with twenty-seven point five percent revenue growth in twenty twenty-four.
  Words:         35
  Latency:       query=0.407s  search=1.827s  synth=0.733s  total=2.967s
  Tokens:        query(290→8)  synth(2514→48)

  Layer 1 checks:
    ✓ query_non_empty
    ✓ query_not_verbatim_copy
    ✓ query_no_unresolved_pronouns
    ✓ query_min_length

  Layer 3 checks:
    ✓ answer_word_count  — 35 words
    ✓ answer_no_preamble
    ✓ answer_no_markdown
    ✓ answer_no_links

  Expected: Must connect "their revenue" to Stripe's twenty-two billion from the digest. Search query should compare Stripe revenue ...

============================================================
  fact_lookup_01  [PASS]  (8/8 passed)
============================================================
  Question:      What was the Celtics score?
  Search query:  Boston Celtics score game 5
  Results:       5 hits
  Answer:        113-97. 

I don't have that information
  Words:         6
  Latency:       query=0.238s  search=2.217s  synth=2.407s  total=4.862s
  Tokens:        query(312→7)  synth(2759→12)

  Layer 1 checks:
    ✓ query_non_empty
    ✓ query_not_verbatim_copy
    ✓ query_no_unresolved_pronouns
    ✓ query_min_length

  Layer 3 checks:
    ✓ answer_word_count  — 6 words
    ✓ answer_no_preamble
    ✓ answer_no_markdown
    ✓ answer_no_links

  Expected: Answer should come directly from the digest without needing search: Celtics beat Heat 112-98 in game 5. Jaylen Brown sco...

============================================================
  pronoun_heavy_01  [PASS]  (8/8 passed)
============================================================
  Question:      When did he announce it?
  Search query:  Nvidia Blackwell Ultra announcement date
  Results:       5 hits
  Answer:        He announced it in Taipei.
  Words:         5
  Latency:       query=1.22s  search=1.798s  synth=13.617s  total=16.635s
  Tokens:        query(319→8)  synth(2818→7)

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

  Expected: Must resolve "he" to Jensen Huang and "it" to the Blackwell Ultra chip. Search query should reference Jensen Huang or Nv...

============================================================
  unanswerable_01  [PASS]  (8/8 passed)
============================================================
  Question:      What will Samsung's stock price be next week?
  Search query:  Samsung stock price forecast next week
  Results:       5 hits
  Answer:        I don't have that information.
  Words:         5
  Latency:       query=0.176s  search=3.093s  synth=9.423s  total=12.692s
  Tokens:        query(261→7)  synth(2395→8)

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

  Expected: This is a prediction request — no search result can answer it. The model should decline clearly ("I don't have that info...

============================================================
  SUMMARY: 7/7 fixtures passed
  Avg total latency: 6.701s
  Latency p50: 4.274s  p95: 16.635s
============================================================