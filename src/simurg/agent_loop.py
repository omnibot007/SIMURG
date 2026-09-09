# ═══════════════════════════════════════════════════════════════════════════════
# SIMURG · buff/fam-guard branch addition (new file, no stock code touched)
#
# agent_loop — action-level guard for tool-calling agents. SIMURG's detectors
# watch the CHARACTER stream; they cannot see action identity (click @ref-7
# three times looks like varied prose). This tracker watches the ACTION stream:
# same tool+args repeated, or step after step with no output, means a stuck
# agent. Framework-agnostic: call note() per step from any loop
# (Notte, agent-browser, hand-rolled ReAct).
#
# Added on buff/fam-guard; conventional credit: doofZ/HAL-X AI own the base.
# ═══════════════════════════════════════════════════════════════════════════════
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

CLEAN, SUSPECT, CORRUPT = "clean", "suspect", "corrupt"


def _norm_args(args: str) -> str:
    return " ".join((args or "").split())[:200]


@dataclass
class ActionVerdict:
    state: str
    reasons: List[str] = field(default_factory=list)


class ActionTracker:
    """Tracks agent actions across steps. Same tool+args hammered repeatedly
    is an action loop; repeated near-empty outputs is a stall."""

    def __init__(self, loop_threshold: int = 3, stall_suspect: int = 3,
                 stall_corrupt: int = 5, min_progress_chars: int = 12):
        self.loop_threshold = loop_threshold
        self.stall_suspect = stall_suspect
        self.stall_corrupt = stall_corrupt
        self.min_progress_chars = min_progress_chars
        self.counts: dict[tuple[str, str], int] = {}
        self.empty_streak = 0
        self.steps = 0

    def note(self, tool: str, args: str = "", output: str = "") -> ActionVerdict:
        self.steps += 1
        key = (tool, _norm_args(args))
        self.counts[key] = self.counts.get(key, 0) + 1
        if len((output or "").strip()) < self.min_progress_chars:
            self.empty_streak += 1
        else:
            self.empty_streak = 0

        n = self.counts[key]
        if n >= self.loop_threshold:
            return ActionVerdict(CORRUPT, [f"action loop {tool} x{n} args={key[1][:80]}"])
        if self.empty_streak >= self.stall_corrupt:
            return ActionVerdict(CORRUPT, [f"output stall {self.empty_streak} thin steps"])
        if self.empty_streak >= self.stall_suspect:
            return ActionVerdict(SUSPECT, [f"output stall {self.empty_streak} thin steps"])
        return ActionVerdict(CLEAN, [])


class TextLoopTracker:
    """Host-fed twin of ActionTracker for raw text. Stock detectors read the
    shared StreamState and can never see line identity; this tracker sees the
    chunks the host feeds it. Catches what rate-based reads miss by construction:
    SPACED repetition (same long line every N lines — the sketch rate dilutes
    to nothing) and CONSECUTIVE duplication (one block hammered mid-file).
    Short lines (braces, imports, list items) are ignored — only substantial
    repeated lines count, which is what separates loops from boilerplate."""

    def __init__(self, min_line_len: int = 40, loop_threshold: int = 6,
                 consec_threshold: int = 3, phrase_threshold: int = 12):
        self.min_line_len = min_line_len
        self.loop_threshold = loop_threshold
        self.consec_threshold = consec_threshold
        self.phrase_threshold = phrase_threshold
        self.seen: dict[str, int] = {}
        self.buf = ""
        self.prev: str | None = None
        self.max_consec = 0
        self._run = 0
        self.sent_win = ""
        self.sent_stuck = False
        self._words: list[str] = []
        self.phrase_stuck = False

    def note(self, chunk: str) -> None:
        self.buf += chunk or ""
        *complete, self.buf = self.buf.split("\n")
        for ln in complete:
            s = ln.strip()
            if len(s) < self.min_line_len:
                self.prev, self._run = None, 0
                continue
            self.seen[s] = self.seen.get(s, 0) + 1
            if s == self.prev:
                self._run += 1
                self.max_consec = max(self.max_consec, self._run)
            else:
                self.prev, self._run = s, 1
                self.max_consec = max(self.max_consec, 1)
        self.sent_win = (self.sent_win + (chunk or ""))[-2000:]
        sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", self.sent_win) if len(x.strip()) >= 40]
        if len(sents) >= 3 and sents[-1] == sents[-2] == sents[-3]:
            self.sent_stuck = True
        self._words.extend(re.findall(r"[A-Za-z0-9$€£]+", chunk or ""))
        del self._words[:-500]
        if len(self._words) >= 64:
            grams: dict[tuple, int] = {}
            peak = 0
            for i in range(len(self._words) - 7):
                g = tuple(self._words[i:i + 8])
                grams[g] = grams.get(g, 0) + 1
                if grams[g] > peak:
                    peak = grams[g]
            if peak >= self.phrase_threshold:
                self.phrase_stuck = True

    def verdict(self) -> ActionVerdict:
        if self.sent_stuck:
            return ActionVerdict(CORRUPT, ["consecutive identical sentences x3+"])
        if self.phrase_stuck:
            return ActionVerdict(CORRUPT, ["adjacent phrase hammered x8+"])
        for line, n in self.seen.items():
            if n >= self.loop_threshold:
                return ActionVerdict(CORRUPT, [f"text loop identical line x{n}: {line[:80]}"])
        if self.max_consec >= self.consec_threshold:
            return ActionVerdict(CORRUPT, [f"consecutive identical x{self.max_consec}"])
        return ActionVerdict(CLEAN, [])
