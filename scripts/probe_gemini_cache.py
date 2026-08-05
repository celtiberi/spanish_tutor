"""Probe whether Gemini implicit caching fires for our request shapes.

2026-08-05 finding: zero cached tokens on byte-identical repeats at
2k / 8.5k / 9.7k prompt tokens, with and without tools, native AND
OpenAI-compat endpoints, on gemini-3.6-flash and gemini-3.5-flash-lite.
Known Google-side bugs in the area: the ~9k-17k implicit-cache dead
zone (googleapis/python-genai#2064) and tools-defined cache misses
(vercel/ai#11513) — but our misses extend beyond both, so implicit
caching is treated as OFF for this key until this probe says otherwise.

Explicit caching was evaluated and BOOKED, not built: at flash-lite
prices the cacheable static prefix (~7k tok) saves ~0.19c/turn against
~0.7c/hour of cache storage — break-even ~4 turns/hour sustained,
which tester traffic does not sustain. Revive conditions: (a) this
probe starts reporting cache hits (Google fixed it — free money, no
code needed), or (b) sustained traffic >100 turns/day (build explicit
caching via the native API then).

Run:  .venv/bin/python scripts/probe_gemini_cache.py [model]
"""

import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tutor import config  # noqa: E402

config.load_env()
KEY = os.environ.get("GEMINI_API_KEY")
MODEL = sys.argv[1] if len(sys.argv) > 1 else config.MODEL

from tutor.character_sheet import default_sheet, format_sheet_for_prompt  # noqa: E402
from tutor.executor import build_ai_tutor_system, build_ai_tutor_user_message  # noqa: E402

system_text = "\n\n".join(b["text"] for b in build_ai_tutor_system())
task = build_ai_tutor_user_message(
    learner="Hola", is_open=False, blank_sheet=False,
    sheet_summary=format_sheet_for_prompt(default_sheet()),
    session_plan="GOALS: greet.",
)
body = {
    "system_instruction": {"parts": [{"text": system_text}]},
    "contents": [{"role": "user", "parts": [{"text": task}]}],
    "generationConfig": {"maxOutputTokens": 30},
}
url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
       f"{MODEL}:generateContent")

hits = 0
for i in range(3):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
    d = json.loads(urllib.request.urlopen(req, timeout=120).read())
    um = d.get("usageMetadata", {})
    cached = um.get("cachedContentTokenCount", 0)
    hits += 1 if cached else 0
    print(f"call {i+1}: model={MODEL} prompt={um.get('promptTokenCount')} "
          f"cached={cached}")
    time.sleep(1.5)

if hits:
    print("\nCACHE IS ALIVE — revive the explicit-caching evaluation "
          "(see module docstring): billing should now show cached-rate "
          "input on real sessions.")
else:
    print("\nStill no implicit caching for identical repeats — "
          "status quo (meter honest, no action).")
