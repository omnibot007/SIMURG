# Harvest a clean-output corpus from Claude Code session transcripts.
#
# Your coding sessions are a gold mine of YOUR model's real output distribution:
# code, plans, explanations, terse acks. This script extracts assistant TEXT
# (never tool calls, never thinking blocks), scrubs anything smelling like a
# secret (dropped entirely, never redacted-in-place), dedupes, and writes the
# jsonl corpus that `evaluate --save` calibrates on:
#
#   python examples/harvest_sessions.py ~/.claude/projects ./corpus.jsonl
#   SIMURG_CORPUS_JSONL=./corpus.jsonl python -m simurg.data.evaluate --save
#
# Honesty note: session outputs include mistakes the operator later corrected.
# This corpus is DOMAIN-representative, not verified-clean. Keep a small
# verified-clean seed (reviewed artifacts) alongside it; volume here, gospel
# there. Only counts print — content never touches stdout.
import hashlib
import json
import os
import re
import sys

SECRET_RES = [
    r"sk-[A-Za-z0-9]{10,}",
    r"Bearer\s+[A-Za-z0-9_\-.~+/]{20,}",
    r"ghp_[A-Za-z0-9]{20,}",
    r"xox[bpas]-[A-Za-z0-9\-]{10,}",
    r"api[_-]?key[\"'\s:=]+[\"']?[A-Za-z0-9]{20,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
]
SECRET_RE = re.compile("|".join(SECRET_RES), re.IGNORECASE)


def iter_texts(path):
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue
            if msg.get("type") != "assistant":
                continue
            message = msg.get("message") or {}
            content = message.get("content")
            blocks = content if isinstance(content, list) else [{"type": "text", "text": content}]
            for b in blocks:
                if not isinstance(b, dict) or b.get("type") != "text":
                    continue
                t = b.get("text") or ""
                if t.strip():
                    yield t


def harvest(src_dir, dst_path, min_chars=300, max_chars=8000, max_texts=3000):
    seen, kept, dropped = set(), 0, {"short": 0, "long": 0, "secret": 0, "dupe": 0}
    with open(dst_path, "w", encoding="utf-8") as out:
        for root, _, files in os.walk(src_dir):
            for fn in sorted(files):
                if not fn.endswith(".jsonl"):
                    continue
                for t in iter_texts(os.path.join(root, fn)):
                    s = t.strip()
                    if len(s) < min_chars:
                        dropped["short"] += 1
                        continue
                    if len(s) > max_chars:
                        dropped["long"] += 1
                        continue
                    if SECRET_RE.search(s):
                        dropped["secret"] += 1
                        continue
                    h = hashlib.blake2b(s.encode("utf-8"), digest_size=16).hexdigest()
                    if h in seen:
                        dropped["dupe"] += 1
                        continue
                    seen.add(h)
                    out.write(json.dumps({"text": s}, ensure_ascii=True) + "\n")
                    kept += 1
                    if kept >= max_texts:
                        return kept, dropped
    return kept, dropped


if __name__ == "__main__":
    kept, dropped = harvest(sys.argv[1], sys.argv[2])
    print(f"kept: {kept} | dropped: {dropped}")
