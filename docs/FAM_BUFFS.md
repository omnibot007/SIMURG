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

## Offered, not taken

- CI split markers for the slow dashboard e2e (full suite hangs here) —
  maintainer's call, documented not imposed.
- Monolith/logprobs layers — need endpoints this project doesn't target.
