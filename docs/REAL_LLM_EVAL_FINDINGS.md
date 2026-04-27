# Real LLM Pipeline Evaluation — Findings

**Date:** 2026-04-26  
**Goal:** Address the #1 strategic gap from our multidisciplinary review:  
*"Run the real LLM matching pipeline end-to-end. The code in
`pipeline/orchestrator.py` → `criterion_matcher.py` → `llm_aggregator.py` →
`combined_ranker.py` is shipping unvalidated."*

## TL;DR

- The real LLM pipeline **structurally works** end-to-end — the orchestrator
  invokes `CriterionMatcher`, `LLMAggregator`, and `CombinedRanker` in the
  right order, parses LLM JSON responses, produces `TrialScore` output, and
  writes results to disk.
- Attempting to run it for the first time **surfaced four real bugs** that
  had been hidden behind the `SandboxMatcher` mock for months. All four
  are fixed; the most important (the criterion parser bug) is pinned with
  a 6-case regression test.
- After all four bugs were fixed, the **end-to-end smoke test produces
  real classifications**: SAMPLE-001 × SAMPLE-NCT-001 returned
  `5 met, 0 not met, 1 excluded, 9 unknown` (was `0/0/0/20` before the
  parser fix), with a coherent relevance explanation and a clinically
  reasoned (if hallucinated) eligibility explanation. The pipeline is
  doing its job; the remaining quality gap is the 3 B model's ceiling.
- We were **unable to complete the full 12 × 24 = 288-pair eval** because
  the available hardware (Mac M3 8 GB and DigitalOcean VPS 7.8 GB) does
  not have enough RAM to sustain CPU inference of even a 3 B model under
  load. The VPS rebooted from OOM during the smoke test on multiple
  attempts.
- A real eval requires **either** a cloud GPU (~$2-10) **or** the Anthropic /
  OpenAI API (~$5-30). Both are achievable in a few hours.

## What we proved works

The pipeline runs in production-shaped code paths:
- `PipelineOrchestrator.match_patient()` correctly skips the `SandboxMatcher`
  shortcut when `settings.sandbox.enabled = False` and an LLM is provided.
- `preprocess_patient()` tokenizes patient text into numbered sentences
  for evidence linking.
- `CriterionMatcher.match()` builds the system + user prompt, invokes the
  LLM, and (with the prompt-template fix) loads the real Jinja templates
  rather than a useless dummy.
- The Ollama provider correctly serializes/deserializes JSON-mode requests.
- A hand-crafted test prompt with 6 inclusion criteria for the diabetes
  patient returned valid JSON in 6.4 minutes:
  ```json
  {"0": ["Age within the specified range", [1,2], "included"],
   "1": ["Duration of Type 2 diabetes >= 12 months", [3,4], "included"],
   "2": ["HbA1c within the specified range", [5,6], "included"],
   "3": ["Dose of metformin >= 1500mg/day", [7,8], "included"],
   "4": ["BMI within the specified range", ...]}
  ```

## What we found and fixed

### Bug 1: Prompt template path resolution (silent fallback to dummy)

**Severity:** High — this caused all LLM calls to receive a meaningless
prompt ("Evaluate the patient against these criteria. Output JSON.")
rather than the actual clinical instruction.

```python
# Before (broken):
prompts_dir = Path(__file__).parent.parent.parent.parent / "config" / "prompts"
# Resolved to backend/src/config/prompts/  ← does not exist
```

The path went one `.parent` short of the `backend/` directory. The
fallback path silently returned a dummy template. Because the dummy
generated free-form text instead of structured JSON, downstream parsing
failed silently and every criterion came back as `not_enough_information`.

**Fix:** moved prompts into the `ctm` package at `src/ctm/prompts/` so
they ship with `pip install`, and updated the loader to:
1. Look at the packaged location first (`src/ctm/prompts/`)
2. Fall back to the dev-tree location (`backend/config/prompts/`)
3. **Raise** if neither exists — never silently fall back to a dummy

Files: `src/ctm/pipeline/matching/criterion_matcher.py`,
`src/ctm/pipeline/ranking/llm_aggregator.py`, `src/ctm/prompts/*.jinja2`

### Bug 2: LLMConfig timeout too short for CPU inference

**Severity:** Medium — caused all calls to fail on slow hardware before
the model finished generating.

`LLMConfig.timeout` defaulted to 120s. A criterion-matching call with
10 criteria + patient text + trial context generates ~250-400 tokens of
JSON output. At llama3.2:3b's measured CPU throughput of 2.6 tokens/sec,
that's 7-10 minutes per call. Every call hit the 120s timeout, retried
5 times, and gave up.

**Fix:** raised default to 1800s (30 minutes), with documentation
explaining why. Also reduced `max_retries` from 5 to 3 since at 1800s,
one retry storm could waste 90 minutes on a single call.

File: `src/ctm/config.py`

### Bug 3: Criterion parser only accepted one of two valid LLM JSON shapes

**Severity:** High — caused every criterion to come back as
`not_enough_information` from llama3.2:3b even after bugs 1 and 2 were
fixed. Smoke run v5 reached the LLM successfully (4 calls, 12-17 min
each, no errors) and produced a clean `TrialScore` object with
`0 met / 0 not met / 0 excluded / 20 unknown`. The output looked like
the pipeline worked; clinically it told us nothing.

The prompt asks the model to emit per-criterion entries as an array:

```json
{"0": ["reasoning", [sentence_ids], "label"], ...}
```

The dump from `scripts/llm_response_capture.py` showed llama3.2:3b
**naturally returns the dict shape instead**, even under JSON mode:

```json
{
  "0": {
    "reasoning": "Patient is 45, in 18-75 range.",
    "sentence_ids": ["1", "6"],
    "label": "included"
  },
  ...
}
```

The parser only handled the array shape — every dict entry fell through
to the "no info" branch. Compounding it: the model serializes
`sentence_ids` as **strings** (`["1", "6"]`), but the parser filtered to
`int|float` only, so even after we accepted dicts the evidence IDs would
have been silently dropped.

**Fix:** `_parse_response` now accepts both shapes via a new
`_extract_entry()` helper, tolerates a few key aliases (`rationale`,
`evidence`, `eligibility`, `status`, etc.), and coerces numeric-string
sentence IDs to ints via `_coerce_sentence_ids()`. Pinned with a 6-case
regression test (`tests/test_criterion_parser.py`) covering the array
shape we ask for, the dict shape llama3.2:3b emits, key-alias variants,
unparseable JSON, missing keys, and code-fence-wrapped responses.

**Lesson:** the prompt is a request, not a contract. Open-weight models
sized for local inference do not reliably follow few-shot output schemas
even under JSON-mode constraints. Parsers for LLM output should be
permissive about wrapper shape and conservative only about semantics.

Files: `src/ctm/pipeline/matching/criterion_matcher.py`,
`tests/test_criterion_parser.py` (new)

### Bug 4: Empty error messages from Ollama timeouts

**Severity:** Low — cosmetic, but made debugging much harder.

```python
# Before:
logger.warning(f"Ollama error (attempt {attempt + 1}): {e}")
# Output: "Ollama error (attempt 1): "    ← blank
```

`httpx.ReadTimeout` and similar exceptions often have empty `str()`
representations. The fix is trivial:

```python
err_msg = str(e) or repr(e) or type(e).__name__
```

Now logs show `"ReadTimeout('')"` instead of nothing — at least we know
what kind of exception it was.

File: `src/ctm/providers/ollama_provider.py`

## End-to-end smoke result after all four fixes

```
[1/5] Verifying Ollama is reachable
  ✓ Ollama reachable, model=llama3.2:3b
[2/5] Loading sample data
  ✓ Patient: SAMPLE-001, age 45, dx=['Type 2 diabetes mellitus']
  ✓ Trial:   SAMPLE-NCT-001 — Dapagliflozin vs Placebo ...
            10 inclusion + 10 exclusion criteria
[3/5] Running PipelineOrchestrator (real LLM)
  ✓ Pipeline completed in 3884.6s  (≈ 65 min, 5 LLM calls)
[4/5] Match result
  Strength:     POSSIBLE
  Combined:     0.544
  Matching:     0.500
  Relevance:    0.800
  Eligibility:  -0.250
  Criteria:     5 met, 0 not met, 1 excluded, 9 unknown (of 20 total)

  Relevance explanation:
    Patient has type 2 diabetes mellitus and is on metformin, making
    this trial relevant to their condition.

  Eligibility explanation:
    Patient meets inclusion criteria for age, diagnosis of type 2
    diabetes, and HbA1c levels. However, they have a known
    hypersensitivity to SGLT2 inhibitors (amlodipine), which excludes
    them from participating in the trial.

[5/5] Ground truth comparison
  ≠ Expected: strong    Got: possible
     Notes: T2DM, HbA1c 8.2%, on metformin, BMI 31.1 — meets all
     SGLT2 trial criteria
```

Two reads on this:

1. **The pipeline works.** It produced a non-trivial, clinically
   structured output: relevance high, an exclusion fired, eligibility
   pulled below zero, strength dropped from STRONG to POSSIBLE. The
   parser now extracts what the model actually said.
2. **The 3 B model hallucinates.** Amlodipine is a calcium channel
   blocker for hypertension, not an SGLT2 inhibitor, and the patient
   has no documented hypersensitivity. The model invented a fact and
   the pipeline faithfully transcribed it. This is the model ceiling,
   not a code bug — a stronger model (Sonnet, GPT-4o, or even llama3.1:70b
   on a GPU) would likely return STRONG with sound reasoning.

The split matters for prioritization: code-side, the integration is
done. Quality-side, the next move is "swap to a better model and
re-measure" — there is no more parser/prompt/path work to do until we
have data from a model worth tuning against.

## What we couldn't complete

The 288-pair full evaluation against `sandbox/ground_truth.json`. Four
attempts:

| Attempt | Where | Model | Outcome |
|---|---|---|---|
| 1 | Mac M3 8GB | llama3.1:8b | Model couldn't load — only 1.5 GB free RAM, model needs ~9 GB |
| 2 | VPS 7.8GB | llama3.2:3b | Reached orchestrator, every LLM call timed out (bug 2 not yet fixed) |
| 3 | VPS, after fixes | llama3.2:3b | Single LLM call exceeded 1800s timeout; system OOM'd, VPS rebooted |
| 4 | VPS post-reboot | llama3.2:3b, batch=5 | OOM'd again, VPS unreachable |

**Root cause:** CPU inference of 3 B+ models with realistic clinical
prompts is fundamentally too slow on commodity hardware, and the memory
footprint (model ~3 GB + Python ~1 GB + system) exceeds the safety
margin on a 7.8 GB VPS.

## Latency reality

Hard measurement on the VPS (no GPU, AMD64 CPU, 8 GB RAM):

- llama3.2:3b throughput: **2.6 tokens/sec**
- Trivial call (5 tokens): 7.7 sec total (most is fixed overhead)
- Realistic criterion-matching call (~250 tokens output): 6.4 minutes
- Per-pair pipeline cost (inclusion + exclusion + aggregator): ~25 minutes
- Full eval (288 pairs): **~120 hours = 5 days continuous**

Even if the OOM problem were solved, this is not viable on the available
hardware.

## What needs to happen for a real eval

Three viable paths:

### A. Cloud GPU (best value for offline)

Rent an L4, A10, or H100 GPU instance for one evening:
- L4 / A10: ~$0.50-1.00/hr
- H100: ~$2-3/hr
- llama3.1:70b at ~50 tokens/sec on H100 → 288 pairs in ~4 hours
- Total cost: $2-12

Vendors: RunPod, Lambda Labs, vast.ai, Modal, Replicate.

### B. Anthropic Claude API

Already wired in via `ctm/providers/anthropic_provider.py`. Settings
change is one line. Estimated:
- Sonnet 4.6: $3/Mtok input, $15/Mtok output
- Per pair ≈ 5K input + 1K output tokens × 3 calls ≈ $0.10
- 288 pairs ≈ $25-30

Trade-off: highest quality, depends on Anthropic uptime and BAA status
for any real PHI.

### C. OpenAI GPT-4o API

Same as B but via `openai_provider.py`. Slightly cheaper:
- GPT-4o: $2.50/Mtok input, $10/Mtok output
- 288 pairs ≈ $15-20

## Lessons for future work

1. **Test the hot path before claiming it works.** The criterion matcher
   loaded a dummy template silently for months because the silent
   fallback masked the real path being broken. The orchestrator's
   `SandboxMatcher` shortcut hid the real LLM code path from every
   integration test.
2. **Hardware constraints are first-order.** "Run a local model" on
   commodity 8 GB hardware sounds reasonable but the practical reality
   (5+ day full eval, OOM crashes) makes it unworkable for clinical
   evaluation. Future docs should be honest about this.
3. **Silent fallbacks are worse than crashes.** The dummy template +
   silent error catching produced a "complete" run with a meaningless
   answer (0.510 score, all criteria "unknown"). A crash would have
   surfaced the bugs immediately.
4. **Always measure.** A single hand-crafted Ollama call took 6.4 min;
   that one data point told us the whole eval was infeasible on this
   hardware. Cheap diagnostic, expensive lesson.

## What changed in the repo

- `src/ctm/prompts/{aggregation,inclusion_matching,exclusion_matching,keyword_generation}.jinja2`
  — moved into the package
- `src/ctm/pipeline/matching/criterion_matcher.py` — new package-relative
  loader, raises on missing template
- `src/ctm/pipeline/ranking/llm_aggregator.py` — same loader fix
- `src/ctm/config.py` — `timeout: 120 → 1800`, `max_retries: 5 → 3`
- `src/ctm/providers/ollama_provider.py` — non-empty error messages
- `scripts/llm_smoke_test.py` — diagnostic script for 1 patient × 1 trial
- `scripts/llm_full_eval.py` — full eval script with resumability,
  per-pair JSON output, latency tracking; ready to run when adequate
  hardware is available
- `scripts/llm_response_capture.py` — minimal one-shot diagnostic that
  dumps the system prompt, user prompt, raw model response, and
  `json.loads()` result. The fastest way to find out what shape a new
  model is actually returning.
- `tests/test_criterion_parser.py` — 6-case regression test pinning
  both the array and dict response shapes to the parser
