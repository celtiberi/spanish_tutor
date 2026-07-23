"""Terminal chat loop for the pedagogy-first tutor (Phase 2 vertical slice)."""

import argparse
import datetime
import json
import sys
from pathlib import Path

import anthropic

from . import config
from .policy import build_system
from .student import (
    STATE_MARKER,
    extract_state,
    load_profile,
    save_profile,
    state_message,
)

HELP = """Commands:
  /state   show the tutor's current model of you
  /help    this message
  /quit    end the session
Anything else is sent to the tutor."""


class StreamScrubber:
    """Prints streamed text while holding back enough tail to suppress the
    trailing <session_state> block (which the learner must never see)."""

    def __init__(self):
        self.buffer = ""
        self.suppressing = False

    def feed(self, text: str) -> None:
        if self.suppressing:
            return
        self.buffer += text
        marker_at = self.buffer.find(STATE_MARKER)
        if marker_at != -1:
            print(self.buffer[:marker_at], end="", flush=True)
            self.suppressing = True
            self.buffer = ""
            return
        # emit all but a marker-sized tail, in case the marker is split
        # across deltas
        safe = len(self.buffer) - len(STATE_MARKER)
        if safe > 0:
            print(self.buffer[:safe], end="", flush=True)
            self.buffer = self.buffer[safe:]

    def close(self) -> None:
        if not self.suppressing and self.buffer:
            buf = self.buffer
            # Drop longest proper prefix of STATE_MARKER so a truncated
            # stream cannot leak "<session_st" (etc.) into the terminal.
            drop = 0
            for k in range(1, len(STATE_MARKER)):
                if buf.endswith(STATE_MARKER[:k]):
                    drop = k
            if drop:
                buf = buf[:-drop]
            if buf:
                print(buf, end="", flush=True)
        self.buffer = ""


def run_turn(client, system, history, state, user_input,
             parse_failed=False, session_open=False):
    messages = history + [
        {"role": "user", "content": user_input},
        state_message(state, parse_failed=parse_failed, session_open=session_open),
    ]
    kwargs = dict(
        model=config.MODEL,
        max_tokens=config.MAX_TOKENS,
        system=system,
        messages=messages,
    )
    if config.SUPPORTS_ADAPTIVE_THINKING:
        kwargs["thinking"] = {"type": "adaptive"}
    if config.SUPPORTS_STREAMING:
        scrubber = StreamScrubber()
        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                scrubber.feed(text)
            scrubber.close()
            final = stream.get_final_message()
    else:
        final = client.messages.create(**kwargs)
        reply_text = "".join(b.text for b in final.content if b.type == "text")
        marker_at = reply_text.find(STATE_MARKER)
        print(reply_text if marker_at == -1 else reply_text[:marker_at],
              end="", flush=True)

    if final.stop_reason == "refusal":
        print("[The tutor declined this request.]")
        return history, state, final, "", True

    reply = "".join(b.text for b in final.content if b.type == "text")
    visible, state, parse_ok = extract_state(reply, state)
    history = history + [
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": visible},
    ]
    if not parse_ok:
        state, parse_ok = _repair_state(client, system, history, state)
    return history, state, final, visible, parse_ok


def _repair_state(client, system, history, previous):
    """One-shot side call when a reply omitted its state block: ask for only
    the block, against the same cached prefix. Not appended to history."""
    repair_kwargs = {}
    if config.SUPPORTS_ADAPTIVE_THINKING:
        repair_kwargs["thinking"] = {"type": "adaptive"}
    try:
        final = client.messages.create(
            model=config.MODEL,
            max_tokens=1024,
            system=system,
            **repair_kwargs,
            messages=history + [{
                "role": "user",
                "content": (
                    "(harness) Your previous reply omitted the session_state "
                    "block. Reply with ONLY the session_state block for the "
                    "turn just completed — no other text."
                ),
            }],
        )
    except anthropic.APIError:
        return previous, False
    reply = "".join(b.text for b in final.content if b.type == "text")
    _, state, ok = extract_state(reply, previous)
    return state, ok


def log_turn(log_path: Path, user_input, visible, state, final):
    record = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "user": user_input,
        "assistant": visible,
        "state": state,
        "stop_reason": final.stop_reason,
        "usage": {
            "input_tokens": final.usage.input_tokens,
            "output_tokens": final.usage.output_tokens,
            "cache_read_input_tokens": getattr(
                final.usage, "cache_read_input_tokens", 0
            ) or 0,
            "cache_creation_input_tokens": getattr(
                final.usage, "cache_creation_input_tokens", 0
            ) or 0,
        },
    }
    with log_path.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pedagogy-first tutor")
    parser.add_argument(
        "--pack", type=Path, default=config.DEFAULT_PACK_DIR,
        help="course pack directory (default: Spanish A1)",
    )
    args = parser.parse_args()

    client = config.make_client()
    system = build_system(config.POLICY_PATH, args.pack)
    state = load_profile(config.PROFILE_PATH)
    history: list[dict] = []

    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    session_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = config.LOG_DIR / f"{session_id}.jsonl"

    print(f"Tutor ready ({args.pack.name}, {config.MODEL}). {HELP}\n")
    print("tutor> ", end="", flush=True)
    # Harness seed: neutral wording so the model can't read it as a content
    # preference (per teaching policy, session-open order still applies).
    try:
        history, state, final, visible, parse_ok = run_turn(
            client, system, history, state,
            "Please open the session per policy.",
            session_open=True,
        )
    except anthropic.RateLimitError:
        print("[Rate limited — wait a moment and restart.]")
        return
    except anthropic.APIStatusError as e:
        print(f"[API error {e.status_code}: {e.message}]")
        return
    except anthropic.APIConnectionError:
        print("[Network error — check your connection and restart.]")
        return
    log_turn(log_path, "(session start)", visible, state, final)
    save_profile(config.PROFILE_PATH, state)
    print("\n")

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input in ("/quit", "/exit"):
            break
        if user_input == "/help":
            print(HELP)
            continue
        if user_input == "/state":
            print(json.dumps(state, indent=2, ensure_ascii=False))
            continue

        print("tutor> ", end="", flush=True)
        try:
            history, state, final, visible, parse_ok = run_turn(
                client, system, history, state, user_input,
                parse_failed=not parse_ok,
            )
        except anthropic.RateLimitError:
            print("[Rate limited — wait a moment and resend.]")
            continue
        except anthropic.APIStatusError as e:
            print(f"[API error {e.status_code}: {e.message}]")
            continue
        except anthropic.APIConnectionError:
            print("[Network error — check your connection and resend.]")
            continue
        log_turn(log_path, user_input, visible, state, final)
        save_profile(config.PROFILE_PATH, state)
        print("\n")

    print(f"Session log: {log_path}")


if __name__ == "__main__":
    main()
