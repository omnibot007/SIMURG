# Harvest a clean-output corpus from Claude Code session transcripts AND/OR
# markdown vaults (skills, missions, ledgers, synced docs).
#
# Modes by file extension while walking the source tree:
#   .jsonl → Claude Code transcripts (assistant TEXT blocks only — never tool
#            calls, never thinking blocks)
#   .md    → whole file as one text (skills, plans, ledger lessons)
# Skipped always: binaries, *.bak*, .reg/.bcd hives, junk dirs, secrets
# (secret-shaped texts are dropped entirely, never redacted-in-place).
#
#   python examples/harvest_sessions.py <src-dir> <corpus.jsonl>
#   SIMURG_CORPUS_JSONL=<corpus.jsonl> python -m simurg.data.evaluate --save
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


SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "dist", "build"}
SKIP_SUBSTR = (".bak",)
SKIP_EXT = {".reg", ".bcd", ".exe", ".dll", ".png", ".jpg", ".pyc", ".json"}


def iter_md(path):
    with open(path, encoding="utf-8", errors="ignore") as fh:
        t = fh.read().strip()
    if t:
        yield t


def harvest(src_dir, dst_path, min_chars=300, max_chars=60000, max_texts=5000):
    seen, kept, dropped = set(), 0, {"short": 0, "long": 0, "secret": 0, "dupe": 0, "skipped": 0}
    with open(dst_path, "w", encoding="utf-8") as out:
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in sorted(files):
                low = fn.lower()
                if any(s in low for s in SKIP_SUBSTR):
                    dropped["skipped"] += 1
                    continue
                if low.endswith(".jsonl"):
                    gen = iter_texts(os.path.join(root, fn))
                elif low.endswith(".md") and not any(low.endswith(e) for e in SKIP_EXT):
                    gen = iter_md(os.path.join(root, fn))
                else:
                    continue
                for t in gen:
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
