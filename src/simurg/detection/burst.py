# ═══════════════════════════════════════════════════════════════════════════════
# SIMURG · buff/fam-guard branch addition (new file, no stock code touched)
#
# burst — max-shingle loop catch. Stock SketchDetector is RATE-driven: a loop
# diluted across a long stream (spaced repetition, one corrupt function buried
# mid-file) keeps the rate low and walks past. But the hammered shingle's
# COUNT doesn't lie: min(rep.max_count,30)/30 needs no rate corroboration.
# Hell-week proven: slow_burn and mixed_drink TPR 0.0 → caught after this.
# Registered into the stock ensemble; fusion weights it automatically.
# ═══════════════════════════════════════════════════════════════════════════════
from __future__ import annotations

from ..core import REGISTRY, REPETITION, DetectorScore


def _ramp(x: float, lo: float, hi: float) -> float:
    return 0.0 if x <= lo else 1.0 if x >= hi else (x - lo) / (hi - lo)


@REGISTRY.register("burst")
class BurstDetector:
    """Single-shingle hammering, CORROBORATION-ONLY (capped like SimHash).
    Why capped: clean long docs legitimately hammer shingles (measured p95
    0.4, p99 1.0 on 890 real texts) — a lone count rule false-alarms.
    Votes suspect solo; aborts only with a second strong detector.
    Consecutive/periodic repetition belongs to the host trackers (they see
    text); this one just makes hammering visible to fusion."""

    name = "burst"

    def evaluate(self, state) -> DetectorScore:
        mx = state.snapshot()["max_shingle_count"]
        p = min(0.60, _ramp(mx, 0.30, 0.60))
        reasons = [f"shingle hammered count~{int(mx * 30)}"] if p >= 0.5 else []
        return DetectorScore(self.name, p, reasons,
                             [REPETITION] if p >= 0.5 else [],
                             {"max_shingle_count": mx})
