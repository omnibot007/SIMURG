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
