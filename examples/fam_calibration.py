# Collect a clean-output corpus for SIMURG calibration on YOUR traffic.
#
# The bundled weights fit the bundled domain. For production you retrain:
#   1. save known-good outputs of your model as .txt/.md files in a directory
#   2. python examples/fam_calibration.py ./my_good_outputs ./corpus.jsonl
#   3. SIMURG_CORPUS_JSONL=./corpus.jsonl python -m simurg.data.evaluate --save
# See docs/TRAINING.md for the full flywheel.
import json
import os
import sys


def collect(src_dir: str, dst_path: str) -> int:
    n = 0
    with open(dst_path, "w", encoding="utf-8") as out:
        for root, _, files in os.walk(src_dir):
            for fn in sorted(files):
                if not fn.endswith((".txt", ".md")):
                    continue
                with open(os.path.join(root, fn), encoding="utf-8") as fh:
                    text = fh.read().strip()
                if len(text) < 50:
                    continue
                out.write(json.dumps({"text": text}, ensure_ascii=True) + "\n")
                n += 1
    return n


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    print(f"collected {collect(src, dst)} clean texts -> {dst}")
