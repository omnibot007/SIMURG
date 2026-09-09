# HELL WEEK runner: stock weights vs your sidecar across four evasion trials.
#
#   PYTHONPATH=src python examples/hellweek.py <corpus.jsonl> [clean_code.py]
#
# Prints a per-trial table. Whatever bleeds earns a rule, a ramp, or a detector.
import json
import os
import sys

import simurg
from simurg import redteam

WDIR = os.path.join(os.path.dirname(simurg.__file__), "weights")
LOOP = "the price is $12.99 the price is $12.99 the price is $12.99 " * 12
DRIFT = "nian de zui hao chi de shi wu shi pi sa " * 40


def load_texts(path, limit=12, min_len=600):
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                t = json.loads(line).get("text", "")
            except Exception:
                continue
            if len(t) >= min_len:
                out.append(t)
            if len(out) >= limit:
                break
    return out


def main():
    corpus, code_path = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None
    cleans = load_texts(corpus)
    lines = [ln for t in cleans for ln in t.splitlines() if len(ln.strip()) > 40]
    code = open(code_path, encoding="utf-8").read() if code_path else cleans[0]
    variants = {
        "stock": redteam.load_variant("stock"),
        "fam": redteam.load_variant(
            "fam",
            os.path.join(WDIR, "fam_model.json"),
            os.path.join(WDIR, "fam_calib.json"),
        ),
    }
    trials = {
        "slow_burn": [redteam.slow_burn(lines, period=p, repeats=10) for p in (8, 20, 40)],
        "mixed_drink": [
            redteam.mixed_drink(c[:1500], LOOP, c[1500:3000]) for c in cleans[:6]
        ],
        "short_con": [redteam.short_con(LOOP, o) for o in (0, 100, 200, 349, 350, 500)]
        + [redteam.short_con(DRIFT, o) for o in (100, 350)],
        "code_rot": [redteam.code_rot(code) for _ in range(4)],
        "cleans": [(c, None) for c in cleans[:8] if len(c) < 6000],
    }
    print(f"{'trial':<12} {'variant':<7} {'tpr':<6} {'fpr':<6} {'p50lat':<7} {'leak':<6} n")
    for name, streams in trials.items():
        for variant, metrics in redteam.compare(name, streams, variants, track_text=True).items():
            print(
                f"{name:<12} {variant:<7} {str(metrics['tpr']):<6} "
                f"{str(metrics['fpr']):<6} {str(metrics['p50_latency']):<7} "
                f"{str(metrics['zero_leak_rate']):<6} {metrics['n']}"
            )


if __name__ == "__main__":
    raise SystemExit(main())
