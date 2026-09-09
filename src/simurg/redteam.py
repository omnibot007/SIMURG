# ═══════════════════════════════════════════════════════════════════════════════
# SIMURG · buff/fam-guard branch addition (new file, no stock code touched)
#
# redteam — HELL WEEK harness. Calibration teaches the guard YOUR normal;
# this teaches it what ATTACKS look like by staging evasions and measuring
# what bleeds: TPR + detection latency + false alarms per trial, stock
# weights vs your sidecar. Whatever bleeds earns a rule, a ramp tune, or a
# custom detector — then re-runs until it holds.
#
# Four trials:
#   slow_burn — repetition spaced every N lines (defeats rate-based reads?)
#   mixed_drink — one corrupt function buried mid-clean-file (localization?)
#   short_con — corruption onset sweeping the hold-window edge (guarantee map)
#   code_rot — code-shaped rot: dup imports, retried calls, boilerplate leak
# ═══════════════════════════════════════════════════════════════════════════════
from __future__ import annotations

import json
import random

from .detection.fusion import ConformalEnsemble
from .detection.sentinel import CORRUPT, CLEAN, SUSPECT, Simurg
from .detection import burst as _burst_detectors  # noqa: F401 — registers burst
from .learning.model import OnlineLogReg

CHUNK = 25


def _stream_verdict(sim, text, tracker=None):
    """Feed in chunks like a live stream. Host twin trackers (action/text
    loop) ride alongside and OR in — exactly how production hosts combine
    stock Simurg with host-side guards. Returns (state, latency|None, reasons)."""
    reasons: list = []
    for i in range(0, len(text), CHUNK):
        chunk = text[i:i + CHUNK]
        if tracker is not None:
            tracker.note(chunk)
        v = sim.feed(chunk)
        if v.state == CORRUPT:
            reasons = list(v.reasons)
            return v.state, sim.f.total_len, reasons
    v = sim.finish()
    reasons = list(v.reasons)
    if tracker is not None and v.state != CORRUPT:
        tv = tracker.verdict()
        if tv.state == CORRUPT:
            return tv.state, sim.f.total_len, list(tv.reasons)
    return v.state, None, reasons


def slow_burn(clean_lines, loop_phrase="fetch the user record and retry on timeout",
              period=20, repeats=12, seed=7):
    rng = random.Random(seed)
    out, onset = [], None
    for i in range(period * repeats):
        if i % period == period - 1:
            if onset is None:
                onset = sum(len(x) + 1 for x in out)
            out.append(loop_phrase)
        else:
            out.append(rng.choice(clean_lines))
    return "\n".join(out) + "\n", onset


def mixed_drink(clean_head, corrupt_mid, clean_tail):
    text = clean_head + "\n" + corrupt_mid + "\n" + clean_tail
    return text, len(clean_head) + 1


def short_con(corrupt, onset, pad_before="status nominal. " * 60, pad_after="all systems green. " * 60):
    return pad_before[:onset] + corrupt + " " + pad_after, onset


def code_rot(clean_code):
    lines = clean_code.splitlines()
    rot = [
        "import os", "import os", "import sys", "import os",  # dup imports
        "resp = api.get('/users'); resp = api.get('/users '); resp = api.get('/users  ')",
        "resp = api.get('/users   '); resp = api.get('/users    ')",
        "# TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO",
    ]
    mid = len(lines) // 2
    text = "\n".join(lines[:mid] + rot + lines[mid:]) + "\n"
    return text, sum(len(x) + 1 for x in lines[:mid])


def load_variant(name, model_path=None, calib_path=None):
    """'stock' or ('fam', model_path, calib_path) -> Simurg factory kwargs."""
    if name == "stock":
        return {}
    return {"model": OnlineLogReg.load(model_path),
            "fusion": ConformalEnsemble.load(calib_path)}


def run_trial(streams, track_text=False, **sim_kwargs):
    """streams: list of (text, onset|None). With track_text, a TextLoopTracker
    rides each stream and ORs in (production shape). Returns metrics dict."""
    from .agent_loop import TextLoopTracker

    tp = fp = tn = fn = 0
    lat, leaks = [], 0
    n_suspect = 0
    for text, onset in streams:
        sim = Simurg(**sim_kwargs)
        tracker = TextLoopTracker() if track_text else None
        state, at, _ = _stream_verdict(sim, text, tracker)
        if state == SUSPECT:
            n_suspect += 1
        if onset is None:
            if state == CORRUPT:
                fp += 1
            else:
                tn += 1
        else:
            if state == CORRUPT:
                tp += 1
                lat.append(max(0, (at or onset) - onset))
                if onset < 350:
                    leaks += 1
            else:
                fn += 1
    n_pos = tp + fn
    return {
        "tpr": round(tp / n_pos, 3) if n_pos else None,
        "fpr": round(fp / (fp + tn), 3) if (fp + tn) else None,
        "p50_latency": sorted(lat)[len(lat) // 2] if lat else None,
        "zero_leak_rate": round(leaks / n_pos, 3) if n_pos else None,
        "n": len(streams),
    }


def compare(label, streams, variants, track_text=False):
    return {v: run_trial(streams, track_text=track_text, **kw) for v, kw in variants.items()}
