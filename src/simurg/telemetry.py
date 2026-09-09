# ═══════════════════════════════════════════════════════════════════════════════
# SIMURG · buff/fam-guard branch addition (new file, no stock code touched)
#
# telemetry — per-attempt JSONL log for fleet tracking: which model, which
# verdict, how fast, why. One corrupt answer is an anecdote; a thousand logged
# attempts is a corruption-rate-per-model dashboard. Stdlib only.
# ═══════════════════════════════════════════════════════════════════════════════
from __future__ import annotations

import json
import os
import time
from collections import Counter
from typing import Iterable


def log_attempt(path: str, record: dict) -> dict:
    """Append one attempt record as JSONL. Returns the record with ts filled."""
    rec = {"ts": time.time(), **record}
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=True) + "\n")
    return rec


def read_attempts(path: str) -> Iterable[dict]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def summarize(path: str) -> dict:
    """Corruption counts by model and verdict. Feed for Grafana, or eyeballs."""
    by_model: Counter = Counter()
    by_verdict: Counter = Counter()
    lat: list[float] = []
    n = 0
    for r in read_attempts(path):
        n += 1
        by_model[str(r.get("model", "?"))] += 1
        by_verdict[str(r.get("verdict", "?"))] += 1
        if isinstance(r.get("latency_s"), (int, float)):
            lat.append(float(r["latency_s"]))
    return {
        "attempts": n,
        "by_model": dict(by_model),
        "by_verdict": dict(by_verdict),
        "p50_latency_s": round(sorted(lat)[len(lat) // 2], 2) if lat else None,
    }
