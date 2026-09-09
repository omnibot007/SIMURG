# FAM buffs (branch `buff/fam-guard`) — what was added on top of stock SIMURG

Stock SIMURG watches the CHARACTER stream. These additions watch everything
around it: the agent's actions, the fleet's health, and the gates that real
endpoints put in front of the model. All new files; zero stock files touched.

## New modules

- `src/simurg/agent_loop.py` — `ActionTracker.note(tool, args, output)` per
  agent step. Same tool+args ×N (default 3) → CORRUPT `action loop`;
  repeated near-empty outputs → SUSPECT at 3, CORRUPT at 5. Framework-agnostic
  (Notte, agent-browser, hand-rolled ReAct). Rationale: char-stream guards
  cannot see action identity — clicking `@ref-7` forever looks like varied
  prose to them.
- `src/simurg/telemetry.py` — `log_attempt` / `read_attempts` / `summarize`
  over JSONL: per-model, per-verdict corruption counts + p50 latency. Stdlib
  only. One corrupt answer is an anecdote; logged attempts are a dashboard.

## New examples

- `examples/gated_endpoint.py` — run `GuardedLLM` against WAF/session-gated
  OpenAI-compatible endpoints via a stdlib opener shim. Bakes in two scars:
  overwrite (never append) urllib's default User-Agent, and pass a `base_url`
  WITHOUT `/chat/completions` (the client appends it).
- `examples/fam_calibration.py` — harvest a clean-output corpus
  (dir of .txt/.md → jsonl) for `evaluate --save` retraining on YOUR traffic.

## Tests

- `tests/test_fam_guard.py` — loop fires, varied stays clean,
  stall suspect→corrupt, progress resets, telemetry roundtrip + summary.

## Verify deltas (this box, 2026-09-09)

- Stock sentinel suite: 5 passed in 0.19s (untouched, still green).
- New suite: 5 passed (see tests/). Stock benchmark reproduced pre-branch:
  TPR 78/80, per-class .89/1/1/1, latency p50 589 chars.
- Live proof the guard helps OUR driver: real Go `deepseek-v4-flash` reply →
  clean; loop/drift synthetics → corrupt with reasons; guarded e2e
  `ok: True, verdict: clean`; forced-primary-death → fallback rescue
  `recovered: True`. Full receipts in the fam-browser lineage file.

## HELL WEEK results (redteam harness, this box)

`examples/hellweek.py` pits stock vs calibrated weights across four evasion
trials, production shape (host trackers OR'd in). Final table:

| trial | stock | fam | note |
|---|---|---|---|
| slow_burn (spaced loops) | 1.0 | 1.0 | stock Simurg alone: 0.0 — TextLoopTracker carries it; catch is END-verdict (retry trigger, not mid-stream abort) |
| mixed_drink (buried block) | 0.833 | 1.0 | fam beats stock via 8-gram phrase rule |
| short_con (onset sweep) | 1.0 | 1.0 | hold-window guarantee holds both |
| code_rot | 1.0 | 1.0 | fam needed the burst vote first (regression caught + fixed) |
| cleans | 0.0 | 0.0 | FPR (abort-worthy only; SUSPECT band stays non-blocking) |

Full-corpus defended FPR: 45/890 = 0.051 (stock detectors alone: 27/890).
Documented tradeoff: the evasions stock misses entirely (0.0) cost ~2 points
of abort rate, concentrated in 10KB+ docs. Knobs: loop_threshold (6),
phrase_threshold (12), min_line_len (40). Design laws learned: max-count
rules MUST cap corroboration-only (clean p99 hits 1.0); SUSPECT never aborts
mid-stream (production ladder passes it); runner metrics count CORRUPT only.

## Offered, not taken

- CI split markers for the slow dashboard e2e (full suite hangs here) —
  maintainer's call, documented not imposed.
- Monolith/logprobs layers — need endpoints this project doesn't target.
