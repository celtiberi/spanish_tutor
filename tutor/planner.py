"""Planner/executor turn path (EXP-002).

Splits the tutor in two: a PLANNER holding the full teaching policy chooses the
teaching move and maintains session state but never speaks to the learner; an
EXECUTOR holding only a thin runtime contract realizes that move as the actual
tutor turn. Tests whether EXP-001's prompt-resistant failures are failures of
move *selection* (recoverable here) or of *realization* (not).

Additive by design: `tutor.cli.run_turn` is untouched, so the single-model gate
cells remain byte-identical to EXP-001's harness.

Design notes:
- The planner owns the `<session_state>` block. That is what lets the executor
  prompt stay thin, and it matches the architecture's logic (bookkeeping is
  planner-side judgment). Consequence: state is written before the executor's
  turn exists, so it reflects the learner turn just processed.
- Both models see the same learner-visible history. The planner therefore plans
  against what the tutor *actually said*, not what it intended to say.
"""

import re
from pathlib import Path

from . import config
from .corpus import load_pack, load_pack_planner_index
from .student import STATE_MARKER, extract_state, state_message

DIRECTIVE_RE = re.compile(r"<directive>(.*?)</directive>", re.DOTALL)

PLANNER_PATH = config.REPO_ROOT / "prompts" / "planner_wrapper.md"
STRUCTURED_PATH = config.REPO_ROOT / "prompts" / "planner_structured.md"
CONTROLLER_PATH = config.REPO_ROOT / "prompts" / "planner_controller.md"
# Latency-optimized controller planner prompt (no full teaching_policy.md).
CONTROLLER_BRIEF_PATH = (
    config.REPO_ROOT / "prompts" / "planner_controller_brief.md")
THIN_PATH = config.REPO_ROOT / "prompts" / "thin_runtime.md"
EXECUTOR_CONTROLLER_PATH = config.REPO_ROOT / "prompts" / "executor_controller.md"



# EXP-003 structured directive schema. session_state is free-form (the state
# shape is model-maintained, not fixed here). The gate (tutor.directive_gate)
# re-validates + runs the ghostwrite/consistency checks before the executor.
STRUCTURED_SCHEMA = {
    "type": "object",
    "properties": {
        "pedagogical_move_present": {"type": "boolean"},
        "move": {"type": "string", "enum": [
            "input", "comprehension_check", "structured_input", "model_form",
            "hint", "probe", "remediate", "elicit_production",
            "recap_and_space", "reveal", "redirect", "close", "passthrough"]},
        "target": {"type": "string"},
        "withhold": {"type": "string"},
        "frame": {
            "type": "object",
            "properties": {
                "lang": {"type": "string"}, "register": {"type": "string"},
                "character": {"type": "string"},
                "max_lines": {"type": "integer"}},
            "required": ["lang", "register", "character", "max_lines"],
            "additionalProperties": False},
        "elicit": {"type": "string"},
        "intent": {"type": "string"},
        # JSON-encoded state block. Structured outputs require a fixed schema
        # for every object (additionalProperties:false); the state block has
        # arbitrary/nested keys, so it rides as a string the harness parses.
        "session_state": {"type": "string"},
    },
    "required": ["pedagogical_move_present", "move", "target", "withhold",
                 "frame", "elicit", "intent", "session_state"],
    "additionalProperties": False,
}


def build_planner_system(policy_path: Path, wrapper_path: Path,
                         pack_dir: Path) -> list[dict]:
    return [
        {"type": "text", "text": policy_path.read_text() + "\n\n"
                                 + wrapper_path.read_text()},
        {
            "type": "text",
            "text": f"# Course pack (your only source of subject truth)\n\n"
                    f"{load_pack(pack_dir)}",
            "cache_control": {"type": "ephemeral"},
        },
    ]


def build_controller_planner_system(pack_dir: Path) -> list[dict]:
    """Slim system for the controller planner: brief + pack *index* only.

    Full teaching_policy.md + full units blow latency (~20k tokens). The
    controller only chooses enums / pack IDs; the executor holds full content.
    """
    brief = CONTROLLER_BRIEF_PATH.read_text()
    index = load_pack_planner_index(pack_dir)
    return [
        {"type": "text", "text": brief},
        {
            "type": "text",
            "text": f"# Course pack index (IDs + scope; not full unit text)\n\n"
                    f"{index}",
            "cache_control": {"type": "ephemeral"},
        },
    ]


def build_executor_system(thin_path: Path, pack_dir: Path) -> list[dict]:
    return [
        {"type": "text", "text": thin_path.read_text()},
        {
            "type": "text",
            "text": f"# Course pack (your only source of subject truth)\n\n"
                    f"{load_pack(pack_dir)}",
            "cache_control": {"type": "ephemeral"},
        },
    ]


def extract_directive(reply: str) -> str:
    """The directive block, or (fallback) everything before the state block.

    A planner that drops the tags still produced a plan; passing the raw text
    through is more honest than substituting an empty directive, and the
    ghostwriting check still sees whatever was sent.
    """
    match = DIRECTIVE_RE.search(reply)
    if match:
        return match.group(1).strip()
    marker_at = reply.find(STATE_MARKER)
    return (reply[:marker_at] if marker_at != -1 else reply).strip()


def directive_message(directive: str, caps) -> dict:
    body = ("Teaching directive for this turn (from the planner — not the "
            "learner). Execute it exactly; do not quote or mention it.\n"
            f"<directive>\n{directive}\n</directive>")
    if caps.mid_system:
        return {"role": "system", "content": body}
    return {
        "role": "user",
        "content": "<harness_context>\n(This is from the tutoring system, "
                   "not the learner.)\n" + body + "\n</harness_context>",
    }


def _call(client, caps, system, messages, max_tokens):
    kwargs = dict(model=caps.model, max_tokens=max_tokens, system=system,
                  messages=messages)
    if caps.adaptive_thinking:
        kwargs["thinking"] = {"type": "adaptive"}
    return client.messages.create(**kwargs)


def _text(final) -> str:
    return "".join(b.text for b in final.content if b.type == "text")


def _repair_state(client, caps, system, messages, previous):
    """Mirror of cli._repair_state for the planner, so the planner cell has the
    same state-recovery affordance as the single-model cells (fair mechanical
    comparison). Not appended to history."""
    try:
        final = _call(client, caps, system, messages + [{
            "role": "user",
            "content": ("(harness) Your previous reply omitted or malformed the "
                        "session_state block. Reply with ONLY the session_state "
                        "block for the turn just completed — no other text."),
        }], 1024)
    except Exception:
        return previous, False
    _, state, ok = extract_state(_text(final), previous)
    return state, ok


def _structured_directive_text(d: dict) -> str:
    """Render a structured directive as the labeled instruction the executor
    reads. session_state is dropped (executor never sees it)."""
    lines = []
    for k in ("move", "target", "withhold", "elicit", "intent"):
        lines.append(f"{k.upper()}: {d.get(k, '')}")
    fr = d.get("frame", {})
    lines.append("FRAME: " + "; ".join(f"{k}={fr.get(k)}" for k in
                 ("lang", "register", "character", "max_lines")))
    return "\n".join(lines)


def _parse_state_field(directive, previous):
    """session_state rides as a JSON string in the structured directive."""
    import json
    if not directive:
        return previous
    raw = directive.get("session_state")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return previous
    return previous


_JSON_INSTRUCTION = (
    "(harness) Respond with ONLY a single JSON object — no prose, no markdown "
    "code fences — with exactly these keys: pedagogical_move_present (boolean), "
    "move (string; EXACTLY one of: input, comprehension_check, structured_input, "
    "model_form, hint, probe, remediate, elicit_production, recap_and_space, "
    "reveal, redirect, close, passthrough — do NOT use any other move name), "
    "target (string), withhold (string), frame (object with lang, register, "
    "character, max_lines), elicit (string), intent (string; English, <=2 "
    "sentences, the pedagogical act only — NEVER the tutor's actual words or the "
    "answer), session_state (a JSON string of the state block)."
)


def _extract_json(text: str):
    """Parse a JSON object from a planner reply, tolerating markdown fences and
    surrounding prose (needed for providers without enforced structured output,
    e.g. grok via the xAI endpoint). Returns dict or None."""
    import json
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    try:
        return json.loads(t)
    except (json.JSONDecodeError, ValueError):
        pass
    start = t.find("{")
    if start == -1:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(t)):
        c = t[i]
        if in_str:
            esc = (c == "\\") and not esc
            if c == '"' and not esc:
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(t[start:i + 1])
                except (json.JSONDecodeError, ValueError):
                    return None
    return None


def _plan_structured(planner, planner_system, messages):
    """One structured planner call. Returns (directive_dict | None, usage).

    Anthropic planners use enforced structured output (`output_config.format`);
    other providers (grok via xAI) don't honor it, so the schema is requested in
    the prompt and the harness gate enforces it via reject-and-replan."""
    anthropic_provider = planner.caps.provider == "anthropic"
    kwargs = dict(model=planner.caps.model, max_tokens=config.MAX_TOKENS,
                  system=planner_system, messages=messages)
    if anthropic_provider:
        kwargs["output_config"] = {"format": {"type": "json_schema",
                                              "schema": STRUCTURED_SCHEMA}}
    else:
        kwargs["messages"] = messages + [
            {"role": "user", "content": _JSON_INSTRUCTION}]
    if planner.caps.adaptive_thinking:
        kwargs["thinking"] = {"type": "adaptive"}
    final = planner.client.messages.create(**kwargs)
    usage = {
        "input_tokens": final.usage.input_tokens,
        "output_tokens": final.usage.output_tokens,
        "cache_read_input_tokens": getattr(
            final.usage, "cache_read_input_tokens", 0) or 0,
    }
    return _extract_json(_text(final)), usage


def run_structured_turn(planner, executor, planner_system, executor_system,
                        history, state, user_input,
                        parse_failed=False, session_open=False):
    """EXP-003 turn: structured planner + harness reject-and-replan gate.

    The gate re-plans once on a malformed/ghostwriting/inconsistent directive
    and hard-fails the turn on a second failure — the executor is never called
    on a bad directive. `extra` records the directive, the replan count, and
    the gate findings so scoring can exclude replan-rescued turns from the
    primary discourse count (per Grok countersign item 3).
    """
    from .directive_gate import check_directive
    from types import SimpleNamespace
    turn = [{"role": "user", "content": user_input}]
    # Carry state as a user-role harness message (not a mid-conversation system
    # message): the replan step appends another user turn after it, and a system
    # message may not be followed by a user message. Consecutive user messages
    # are legal and combined by the API.
    state_caps = SimpleNamespace(mid_system=False)
    base_msgs = history + turn + [state_message(
        state, parse_failed=parse_failed, session_open=session_open,
        caps=state_caps)]

    replans, gate_findings, usages, directive = 0, [], [], None
    msgs = base_msgs
    for attempt in range(2):
        directive, usage = _plan_structured(planner, planner_system, msgs)
        usages.append(usage)
        if directive is None:
            ok, errs = False, ["planner did not return valid JSON"]
        else:
            ok, errs = check_directive(directive)
        if ok:
            break
        gate_findings = errs
        replans += 1
        # re-prompt with the specific complaint, same turn
        msgs = base_msgs + [
            {"role": "user", "content":
                "(harness) Your directive was rejected: "
                + "; ".join(errs[:4])
                + ". Re-emit a corrected structured directive — name forms "
                  "abstractly, keep all learner-facing Spanish out of every "
                  "field, and make move/pedagogical_move_present consistent."}]
    else:
        # second attempt also failed -> hard-fail the turn, executor not called
        state = _parse_state_field(directive, state)
        return history, state, _Sentinel("gate_hard_fail"), "", True, {
            "directive": directive, "replans": replans,
            "gate_findings": gate_findings, "hard_fail": True,
            "planner_usage": usages[-1]}

    state = _parse_state_field(directive, state)
    executor_msgs = history + turn + [
        directive_message(_structured_directive_text(directive),
                          executor.caps)]
    final = _call(executor.client, executor.caps, executor_system,
                  executor_msgs, config.MAX_TOKENS)
    if final.stop_reason == "refusal":
        return history, state, final, "", True, {
            "directive": directive, "replans": replans,
            "planner_stop_reason": "refusal"}
    visible, _, _ = extract_state(_text(final), state)
    history = history + turn + [{"role": "assistant", "content": visible}]
    return history, state, final, visible, True, {
        "directive": directive, "replans": replans,
        "gate_findings": gate_findings, "planner_usage": usages[-1]}


class _Sentinel:
    """Stands in for a provider message when the gate hard-fails a turn before
    any executor call (so the driver's `.stop_reason`/`.usage` access works)."""
    def __init__(self, reason):
        self.stop_reason = reason
        from types import SimpleNamespace
        self.usage = SimpleNamespace(input_tokens=0, output_tokens=0,
                                     cache_read_input_tokens=0)
        self.content = []


def _plan_controller(planner, planner_system, messages):
    """One controller-schema planner call.

    Returns (parsed_dict|None, usage, raw_text).
    """
    from .pedagogy_controller import CONTROLLER_SCHEMA
    anthropic_provider = planner.caps.provider == "anthropic"
    # Small JSON only — do not use the tutor MAX_TOKENS budget (8192).
    kwargs = dict(model=planner.caps.model,
                  max_tokens=config.PLANNER_MAX_TOKENS,
                  system=planner_system, messages=messages)
    if anthropic_provider:
        kwargs["output_config"] = {"format": {"type": "json_schema",
                                              "schema": CONTROLLER_SCHEMA}}
    else:
        # Providers without enforced JSON schema: instruct + harness gate.
        keys = ", ".join(CONTROLLER_SCHEMA["required"])
        kwargs["messages"] = messages + [{
            "role": "user",
            "content": (
                "(harness) Respond with ONLY one compact JSON object (no "
                f"markdown fences) with keys: {keys}. "
                "STRING ENUMS ONLY for situation, move, reveal_policy, "
                "sequence_slot. "
                "focus={kind,ref}; error_policy={mode,priority}; "
                "elicit={type,of}; constraints=array of enum tokens only "
                "(no prose). session_state=JSON string. Be brief."
            ),
        }]
    # Never enable extended thinking for the controller planner — it only
    # multiplies latency for a tiny JSON decision.
    final = planner.client.messages.create(**kwargs)
    usage = {
        "input_tokens": final.usage.input_tokens,
        "output_tokens": final.usage.output_tokens,
        "cache_read_input_tokens": getattr(
            final.usage, "cache_read_input_tokens", 0) or 0,
    }
    raw = _text(final)
    return _extract_json(raw), usage, raw


def _usage_from_final(final) -> dict:
    u = getattr(final, "usage", None)
    if u is None:
        return {}
    return {
        "input_tokens": getattr(u, "input_tokens", 0) or 0,
        "output_tokens": getattr(u, "output_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(
            u, "cache_read_input_tokens", 0) or 0,
    }


def run_controller_turn(planner, executor, planner_system, executor_system,
                        history, state, user_input,
                        parse_failed=False, session_open=False,
                        session_logger=None, progress=None):
    """Limited pedagogical controller path.

    Planner fills the closed decision schema (tutor.pedagogy_controller).
    Harness rejects illegal (situation, move) pairs.
    Executor receives a typed YAML act card — not free intent.

    If `session_logger` is a SessionLogger, the full turn (planner attempts,
    gate, brief, executor reply, state) is written to disk.
    `progress` is an optional callable(str) for UI status (e.g. print).
    """
    from .pedagogy_controller import (
        check_controller_decision,
        parse_session_state,
        render_executor_brief,
    )
    from types import SimpleNamespace
    import copy

    def _prog(msg: str) -> None:
        if progress:
            progress(msg)

    state_before = copy.deepcopy(state) if isinstance(state, dict) else state
    turn = [{"role": "user", "content": user_input}]
    state_caps = SimpleNamespace(mid_system=False)
    base_msgs = history + turn + [state_message(
        state, parse_failed=parse_failed, session_open=session_open,
        caps=state_caps)]

    from .lesson_flow import (
        advance_phase,
        build_session_open_decision,
        ensure_flow_fields,
        flow_gate_errors,
        harness_flow_message,
        infer_issue_for_turn,
        success_heuristic,
    )
    from . import config as _cfg

    state = ensure_flow_fields(state)

    # Fast path: session open — skip planner API; real lesson arc.
    seed = (user_input or "").lower()
    if session_open or "open the session" in seed:
        decision = build_session_open_decision(state)
        open_note = decision.pop("_open_note", None)
        ok, errs, norm = check_controller_decision(
            decision, learner_text=user_input)
        if ok and norm:
            decision = norm
        # Preserve open note / phase in state from builder
        state = parse_session_state(decision, state)
        state = ensure_flow_fields(state)
        _prog(
            f"session open ({state.get('lesson_phase')}, no planner) → speaking…"
        )
        brief = render_executor_brief(
            decision, pack_dir=_cfg.DEFAULT_PACK_DIR,
            open_note=open_note,
            lesson_phase=state.get("lesson_phase"),
        )
        executor_msgs = history + turn + [
            directive_message(brief, executor.caps)]
        final = _call(executor.client, executor.caps, executor_system,
                      executor_msgs, config.MAX_TOKENS)
        exec_usage = _usage_from_final(final)
        raw_exec = _text(final)
        visible, state_from_exec, _ = extract_state(raw_exec, state)
        # Keep harness phase; merge model bookkeeping carefully
        phase = state.get("lesson_phase")
        goal = state.get("lesson_goal") or state.get("goal")
        state = ensure_flow_fields(state_from_exec)
        state["lesson_phase"] = phase
        if goal:
            state["lesson_goal"] = goal
            state["goal"] = goal
        # Advance after input open
        state = advance_phase(state, decision.get("move", "present_input"))
        if final.stop_reason != "refusal":
            history = history + turn + [{"role": "assistant", "content": visible}]
        else:
            visible = ""
        extra = {
            "directive": decision, "controller_decision": decision,
            "executor_brief": brief, "replans": 0, "gate_findings": [],
            "planner_usage": {"input_tokens": 0, "output_tokens": 0,
                              "cache_read_input_tokens": 0},
            "executor_usage": exec_usage,
            "planner_attempts": [{
                "attempt": 0, "raw_text": "(deterministic session-open)",
                "parsed": decision, "gate_ok": True, "gate_errs": [],
                "normalized": decision, "usage": {},
            }],
            "arch": "controller", "fast_path": "session_open",
            "lesson_phase": state.get("lesson_phase"),
        }
        if session_logger is not None:
            session_logger.log_controller_turn(
                learner=user_input,
                state_before=state_before,
                state_after=state,
                visible=visible,
                extra=extra,
                stop_reason=getattr(final, "stop_reason", "") or "",
                executor_raw=raw_exec,
                history_len=len(history),
            )
        return history, state, final, visible, True, extra

    # Inject lesson-flow constraints into planner context
    flow_msg = {
        "role": "user",
        "content": "<harness_context>\n"
                   + harness_flow_message(state)
                   + "\n</harness_context>",
    }
    replans, gate_findings, decision = 0, [], None
    planner_attempts: list[dict] = []
    msgs = base_msgs + [flow_msg]
    for attempt in range(2):
        _prog("planning…" if attempt == 0 else "replanning (gate rejected)…")
        parsed, usage, raw = _plan_controller(planner, planner_system, msgs)
        if parsed is None:
            ok, errs, norm = False, ["planner did not return valid JSON"], None
        else:
            try:
                ok, errs, norm = check_controller_decision(
                    parsed, learner_text=user_input)
            except Exception as e:
                ok, errs, norm = False, [
                    f"validator exception: {type(e).__name__}: {e}"], None
            if ok and norm is not None:
                flow_errs = flow_gate_errors(norm, state)
                if flow_errs:
                    ok, errs = False, flow_errs
        planner_attempts.append({
            "attempt": attempt,
            "raw_text": raw,
            "parsed": parsed,
            "gate_ok": ok,
            "gate_errs": list(errs) if errs else [],
            "normalized": norm,
            "usage": usage,
        })
        if ok:
            decision = norm
            break
        gate_findings = errs
        replans += 1
        msgs = base_msgs + [flow_msg, {
            "role": "user",
            "content": (
                "(harness) Your controller decision was rejected: "
                + "; ".join(errs[:6])
                + ". Re-emit a legal decision for the current lesson_phase. "
                  "STRING ENUMS ONLY. Use pack IDs that match the error "
                  "(M-* for misconceptions, not C-* for form errors). "
                  "Do not skip to production while phase is input/comprehension."
            ),
        }]
    else:
        state = parse_session_state(decision or {}, state)
        extra = {
            "directive": decision, "controller_decision": decision,
            "replans": replans, "gate_findings": gate_findings,
            "hard_fail": True,
            "planner_usage": planner_attempts[-1]["usage"]
            if planner_attempts else {},
            "planner_attempts": planner_attempts,
            "arch": "controller",
            "lesson_phase": state.get("lesson_phase"),
        }
        if session_logger is not None:
            session_logger.log_controller_turn(
                learner=user_input,
                state_before=state_before,
                state_after=state,
                visible="",
                extra=extra,
                stop_reason="gate_hard_fail",
                history_len=len(history),
            )
        return history, state, _Sentinel("gate_hard_fail"), "", True, extra

    # Merge planner state but keep harness phase authority until advance
    phase_before = state.get("lesson_phase")
    goal_before = state.get("lesson_goal") or state.get("goal")
    state = parse_session_state(decision, state)
    state = ensure_flow_fields(state)
    if phase_before:
        state["lesson_phase"] = phase_before
    if goal_before:
        state["lesson_goal"] = goal_before
        state["goal"] = goal_before

    brief = render_executor_brief(
        decision, pack_dir=_cfg.DEFAULT_PACK_DIR,
        lesson_phase=state.get("lesson_phase"),
    )
    _prog(
        f"planned: phase={state.get('lesson_phase')} "
        f"{decision.get('situation')}/{decision.get('move')} → speaking…"
    )
    executor_msgs = history + turn + [
        directive_message(brief, executor.caps)]
    final = _call(executor.client, executor.caps, executor_system,
                  executor_msgs, config.MAX_TOKENS)
    exec_usage = _usage_from_final(final)
    if final.stop_reason == "refusal":
        extra = {
            "directive": decision, "controller_decision": decision,
            "executor_brief": brief, "replans": replans,
            "planner_stop_reason": "refusal",
            "planner_usage": planner_attempts[-1]["usage"],
            "executor_usage": exec_usage,
            "planner_attempts": planner_attempts,
            "gate_findings": gate_findings,
            "arch": "controller",
            "lesson_phase": state.get("lesson_phase"),
        }
        if session_logger is not None:
            session_logger.log_controller_turn(
                learner=user_input,
                state_before=state_before,
                state_after=state,
                visible="",
                extra=extra,
                stop_reason="refusal",
                history_len=len(history),
            )
        return history, state, final, "", True, extra
    raw_exec = _text(final)
    visible, state_from_exec, _ = extract_state(raw_exec, state)
    phase = state.get("lesson_phase")
    goal = state.get("lesson_goal") or state.get("goal")
    state = ensure_flow_fields(state_from_exec)
    if phase:
        state["lesson_phase"] = phase
    if goal:
        state["lesson_goal"] = goal
        state["goal"] = goal
    issue = infer_issue_for_turn(user_input, decision)
    # Surface-only issues: rewrite remediate → conversational progress
    if issue == "surface" and decision.get("move") == "remediate":
        # Still logged as remediate intent from planner, but progression treats
        # as success so we escape spelling hell.
        ok_success = True
    elif issue == "meta":
        ok_success = False
    else:
        ok_success = success_heuristic(
            user_input, visible, decision, issue_class=issue)
    focus_ref = (decision.get("focus") or {}).get("ref")
    state = advance_phase(
        state, decision.get("move", ""),
        success_signal=ok_success,
        issue_class=issue,
        focus_ref=focus_ref,
    )
    history = history + turn + [{"role": "assistant", "content": visible}]
    extra = {
        "directive": decision, "controller_decision": decision,
        "executor_brief": brief, "replans": replans,
        "gate_findings": gate_findings,
        "planner_usage": planner_attempts[-1]["usage"],
        "executor_usage": exec_usage,
        "planner_attempts": planner_attempts,
        "arch": "controller",
        "lesson_phase": state.get("lesson_phase"),
        "issue_class": issue,
        "consecutive_successes": state.get("consecutive_successes"),
        "same_target_retries": state.get("same_target_retries"),
    }
    if session_logger is not None:
        session_logger.log_controller_turn(
            learner=user_input,
            state_before=state_before,
            state_after=state,
            visible=visible,
            extra=extra,
            stop_reason=getattr(final, "stop_reason", "") or "",
            executor_raw=raw_exec,
            history_len=len(history),
        )
    return history, state, final, visible, True, extra


def run_planned_turn(planner, executor, planner_system, executor_system,
                     history, state, user_input,
                     parse_failed=False, session_open=False):
    """One learner turn through plan → realize.

    Returns (history, state, final, visible, parse_ok, extra) — the first five
    match `cli.run_turn` so the eval driver can treat both architectures the
    same; `extra` carries the directive and the planner's usage.
    """
    turn = [{"role": "user", "content": user_input}]

    # 1. Plan. The planner sees state and emits the directive + next state.
    planner_msgs = history + turn + [state_message(
        state, parse_failed=parse_failed, session_open=session_open,
        caps=planner.caps)]
    planner_final = _call(planner.client, planner.caps, planner_system,
                          planner_msgs, config.MAX_TOKENS)
    planner_reply = _text(planner_final)
    directive = extract_directive(planner_reply)
    _, state, parse_ok = extract_state(planner_reply, state)
    if not parse_ok:
        state, parse_ok = _repair_state(
            planner.client, planner.caps, planner_system,
            planner_msgs + [{"role": "assistant", "content": planner_reply}],
            state)

    # 2. Realize. The executor never sees state — only the directive.
    executor_msgs = history + turn + [
        directive_message(directive, executor.caps)]
    final = _call(executor.client, executor.caps, executor_system,
                  executor_msgs, config.MAX_TOKENS)

    if final.stop_reason == "refusal":
        return history, state, final, "", parse_ok, {
            "directive": directive, "planner_stop_reason": "refusal"}

    # The executor is told not to emit the marker; strip defensively so a slip
    # is caught by no_marker_leak on the directive path, not leaked to a learner.
    visible, _, _ = extract_state(_text(final), state)
    history = history + turn + [{"role": "assistant", "content": visible}]
    return history, state, final, visible, parse_ok, {
        "directive": directive,
        "planner_usage": {
            "input_tokens": planner_final.usage.input_tokens,
            "output_tokens": planner_final.usage.output_tokens,
            "cache_read_input_tokens": getattr(
                planner_final.usage, "cache_read_input_tokens", 0) or 0,
        },
    }
