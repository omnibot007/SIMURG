# Gated OpenAI-compatible endpoints with SIMURG's GuardedLLM.
#
# Problem: GuardedLLM builds its own urllib request with hardcoded headers.
# Gated endpoints (Cloudflare/WAF edge filtering, per-conversation session
# routing) demand extra headers — e.g. a real User-Agent and a stable
# session id. This recipe injects them process-wide with a stdlib opener,
# no fork of the library required.
#
# Two scars baked in (paid for on a live endpoint, 2026-09-09):
#   1. OVERWRITE urllib's default `Python-urllib` UA — appending a second
#      User-Agent leaves both on the wire and the edge still blocks.
#   2. GuardedLLM's `base_url` must EXCLUDE `/chat/completions`
#      (it appends the path itself) or every call 404s on a doubled path.
#
#   python gated_endpoint.py
import os
import urllib.request

from simurg import GuardedLLM

BASE_URL = os.environ.get("GUARD_BASE_URL", "http://localhost:8000/v1")
MODEL = os.environ.get("GUARD_MODEL", "my-model")
API_KEY = os.environ.get("GUARD_API_KEY", "EMPTY")
SESSION_ID = os.environ.get("GUARD_SESSION_ID", "simurg-session-0001")

EXTRA_HEADERS = {
    "User-Agent": os.environ.get("GUARD_USER_AGENT", "simurg-guard/1.0"),
    "x-session-id": SESSION_ID,  # rename to whatever your gateway requires
}


class _HeaderShim(urllib.request.BaseHandler):
    def _add(self, req):
        host = req.host or ""
        if host in BASE_URL:
            for k, _ in list(req.header_items()):
                if k.lower() == "user-agent":
                    req.remove_header(k)
            for k, v in EXTRA_HEADERS.items():
                req.add_header(k, v)
        return req

    http_request = _add
    https_request = _add


def main() -> int:
    urllib.request.install_opener(urllib.request.build_opener(_HeaderShim()))
    llm = GuardedLLM(BASE_URL, model=MODEL, api_key=API_KEY, retries=1)
    r = llm.chat([{"role": "user", "content": "Reply with exactly: guarded-ready"}])
    print("ok:", r.ok, "| verdict:", r.verdict)
    print("text:", r.text)
    return 0 if r.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
