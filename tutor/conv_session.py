"""Reusable conversational Spanish session (CLI + web).

Sheet = learner context; tool call update_character_sheet keeps it current.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from . import config
from .can_dos import build_focus_panel
from .character_sheet import (
    UPDATE_CHARACTER_SHEET_TOOL,
    clear_session_scoped_affect,
    default_sheet,
    extract_sheet_delta,
    format_sheet_for_prompt,
    format_sheet_human,
    load_sheet,
    process_turn,
    save_sheet,
)
from .corpus import load_pack
from .focus_enrich import enrich_focus_panel, focus_cache_key, focus_model_enabled
from .session_log import SessionLogger
from .tutor_response import compose_visible, process_tutor_raw


def compose_if_needed(parts) -> str:
    return compose_visible(parts)

CONV_PROMPT = config.REPO_ROOT / "prompts" / "conversational_tutor.md"
DEFAULT_SHEET_PATH = config.REPO_ROOT / "logs" / "character_sheet.json"
SHEET_TOOLS = [UPDATE_CHARACTER_SHEET_TOOL]

OPEN_HARNESS = (
    "(harness) Open a TEACHING session — not a chat-buddy hello. "
    "You are a Spanish tutor. Every turn must teach. "
    "Use the character sheet (next_best / form_focus / scaffold). "
    "OPEN RECIPE: "
    "(1) brief Spanish greeting; "
    "(2) one plain micro-goal if useful (e.g. 'vamos a practicar estoy'); "
    "(3) <model> 2–3 short answer phrases they can use; "
    "(4) <try> one clear production task (answer ¿cómo estás? / say where you are). "
    "Do NOT open with only ¡Hola! ¿Cómo estás? and no models. "
    "LANGUAGE: Spanish-forward CI; English is a light rescue only. "
    "Praise in Spanish. No dual-subtitle walls. Keep Spanish short. "
    "TIME: Do NOT assume short on time unless they say so THIS session. "
    "Use structured <tutor> parts (model + try required on open). "
    "Call update_character_sheet only if you already know something new "
    "(usually skip on session open)."
)


@dataclass
class TurnResult:
    reply: str
    notes: list[str] = field(default_factory=list)
    next_best: dict = field(default_factory=dict)
    skills: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)
    tool_delta: dict | None = None
    input_mode: str = "text"  # text | speech (for future audio pipeline)
    stop_reason: str = ""
    error: str | None = None
    focus_meta: dict = field(default_factory=dict)
    # Structured multi-part reply (recast / explain / continue / …)
    parts: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "reply": self.reply,
            "notes": self.notes,
            "next_best": self.next_best,
            "skills": self.skills,
            "usage": self.usage,
            "tool_delta": self.tool_delta,
            "input_mode": self.input_mode,
            "stop_reason": self.stop_reason,
            "error": self.error,
            "focus_meta": self.focus_meta,
            "parts": self.parts,
        }


def build_conversational_system(pack_dir: Path, sheet: dict) -> list[dict]:
    """Sheet = context about the learner; pack = legal language palette."""
    from .character_sheet import active_error_patterns, now_iso

    stance = CONV_PROMPT.read_text()
    pack = load_pack(pack_dir)
    sheet_txt = format_sheet_for_prompt(sheet)
    now = now_iso()
    active = active_error_patterns(sheet)
    err_block = ""
    if active:
        lines = [
            "# ACTIVE ERROR PATTERNS (priority — do not ignore)",
            "These constructions keep failing. Recast + weave practice THIS turn "
            "before chasing a brand-new stretch.",
        ]
        for ep in active:
            lines.append(
                f"- {ep['id']} ×{ep['count']}: {ep['label']} "
                f"(last_seen={ep.get('last_seen')}) "
                f"examples={ep.get('last_examples')}"
            )
            if ep.get("teach_hint"):
                lines.append(f"  teach: {ep['teach_hint']}")
        err_block = "\n".join(lines) + "\n\n"
    return [
        {
            "type": "text",
            "text": (
                stance
                + f"\n\n# Clock\nCurrent local date/time: **{now}**\n"
                + "Use this to interpret last_seen / updated_at on the sheet "
                + "(e.g. yesterday vs today).\n\n"
                + err_block
                + "# Student character sheet (YOUR model of this learner)\n"
                + "Use this to choose Spanish level, scaffolding, and what to "
                + "weave in next. Do not ignore next_best / avoid / "
                + "active error patterns.\n\n"
                + "When you have NEW evidence about the learner, call the "
                + "update_character_sheet tool with a partial delta (same turn "
                + "as your spoken reply). Skip the tool if nothing changed.\n\n"
                + sheet_txt
            ),
        },
        {
            "type": "text",
            "text": "# Course pack palette (in-scope inventory + denylist)\n\n"
                    + pack,
            "cache_control": {"type": "ephemeral"},
        },
    ]


def _usage_dict(final) -> dict:
    return {
        "input_tokens": getattr(getattr(final, "usage", None), "input_tokens", 0),
        "output_tokens": getattr(getattr(final, "usage", None), "output_tokens", 0),
    }


def _split_content(final) -> tuple[str, list]:
    texts: list[str] = []
    tools: list = []
    for b in getattr(final, "content", None) or []:
        btype = getattr(b, "type", None)
        if btype == "text":
            t = getattr(b, "text", "") or ""
            if t:
                texts.append(t)
        elif btype == "tool_use":
            tools.append(b)
    return "\n".join(texts).strip(), tools


def _tool_delta_from_blocks(tool_blocks: list) -> dict | None:
    merged: dict = {}
    for b in tool_blocks:
        name = getattr(b, "name", "") or ""
        if name != "update_character_sheet":
            continue
        inp = getattr(b, "input", None) or {}
        if not isinstance(inp, dict):
            continue
        for k, v in inp.items():
            if k in (
                "identity", "affect", "receptive", "next_best", "coverage",
            ) and isinstance(v, dict):
                base = merged.setdefault(k, {})
                if isinstance(base, dict):
                    base.update(v)
                else:
                    merged[k] = v
            elif k in ("skills", "grammar", "lexicon") and isinstance(v, dict):
                base = merged.setdefault(k, {})
                for sk, sv in v.items():
                    if isinstance(sv, dict) and isinstance(base.get(sk), dict):
                        base[sk] = {**base[sk], **sv}
                    else:
                        base[sk] = sv
            else:
                merged[k] = v
    return merged or None


def _assistant_content_blocks(final) -> list[dict]:
    out: list[dict] = []
    for b in getattr(final, "content", None) or []:
        btype = getattr(b, "type", None)
        if btype == "text":
            out.append({"type": "text", "text": getattr(b, "text", "") or ""})
        elif btype == "tool_use":
            out.append({
                "type": "tool_use",
                "id": getattr(b, "id", "call_0"),
                "name": getattr(b, "name", ""),
                "input": getattr(b, "input", {}) or {},
            })
    return out


def _call(client, caps, system, messages, *, max_tokens=None, tools=None):
    kwargs = dict(
        model=caps.model,
        max_tokens=max_tokens or config.MAX_TOKENS,
        system=system,
        messages=messages,
    )
    if tools:
        kwargs["tools"] = tools
    final = client.messages.create(**kwargs)
    text, tool_blocks = _split_content(final)
    return final, text, tool_blocks


def tutor_turn(
    client,
    caps,
    system,
    messages,
    *,
    tools=None,
    max_tool_rounds: int = 1,
):
    """One learner-facing turn: text + optional sheet tool delta."""
    total_usage = {"input_tokens": 0, "output_tokens": 0}
    all_tool_blocks: list = []
    work_messages = list(messages)
    final = None
    text = ""

    for round_i in range(max_tool_rounds + 1):
        final, text, tool_blocks = _call(
            client, caps, system, work_messages, tools=tools,
        )
        u = _usage_dict(final)
        total_usage["input_tokens"] += u["input_tokens"]
        total_usage["output_tokens"] += u["output_tokens"]
        all_tool_blocks.extend(tool_blocks)

        if text or not tool_blocks or round_i >= max_tool_rounds:
            break

        assistant_blocks = _assistant_content_blocks(final)
        result_blocks = []
        for b in tool_blocks:
            result_blocks.append({
                "type": "tool_result",
                "tool_use_id": getattr(b, "id", "call_0"),
                "content": json.dumps({
                    "ok": True,
                    "applied": getattr(b, "name", ""),
                }),
            })
        work_messages = work_messages + [
            {"role": "assistant", "content": assistant_blocks},
            {"role": "user", "content": result_blocks + [{
                "type": "text",
                "text": (
                    "(harness) Sheet update recorded. Now send the "
                    "learner-facing reply only — no JSON, no tool talk."
                ),
            }]},
        ]

    delta = _tool_delta_from_blocks(all_tool_blocks)
    return final, text, delta, total_usage, all_tool_blocks


def _skills_snapshot(sheet: dict) -> dict:
    return {
        k: {"status": v.get("status"), "confidence": v.get("confidence")}
        for k, v in (sheet.get("skills") or {}).items()
    }


class ConversationalSession:
    """Stateful chat session shared by CLI and web."""

    def __init__(
        self,
        *,
        model: str | None = None,
        pack_dir: Path | None = None,
        sheet_path: Path | None = None,
        use_tools: bool = True,
        label: str = "chat",
        log: bool = True,
        focus_model: str | None = None,
    ):
        config.load_env()
        self.model = model or config.MODEL
        self.focus_model = (
            focus_model if focus_model is not None else config.FOCUS_MODEL
        )
        self.pack_dir = Path(pack_dir or config.DEFAULT_PACK_DIR)
        self.sheet_path = Path(sheet_path or DEFAULT_SHEET_PATH)
        self.use_tools = use_tools
        self.caps = config.caps_for(self.model)
        self.client = config.make_client_for(self.model)
        self.sheet = load_sheet(self.sheet_path)
        # Drop stale "only a few minutes" energy from prior days/sessions
        self.sheet = clear_session_scoped_affect(self.sheet)
        save_sheet(self.sheet_path, self.sheet)
        self.history: list[dict] = []
        self.tools = SHEET_TOOLS if use_tools else None
        self.messages_for_ui: list[dict] = []  # learner-visible only
        self._focus_panel: dict | None = None
        self._focus_key: str | None = None
        self._focus_meta: dict = {"source": "static"}
        self.logger: SessionLogger | None = None
        if log:
            self.logger = SessionLogger(
                arch="conversational",
                label=label,
                meta={
                    "mode": "conversational",
                    "model": self.model,
                    "focus_model": self.focus_model,
                    "pack": str(self.pack_dir),
                    "sheet": str(self.sheet_path),
                    "sheet_update": "tool" if use_tools else "rules",
                    "surface": label,
                },
            )

    @property
    def system(self) -> list[dict]:
        return build_conversational_system(self.pack_dir, self.sheet)

    def _refresh_focus(
        self,
        *,
        learner: str = "",
        tutor_reply: str = "",
        use_ai: bool = True,
    ) -> None:
        """Update cached focus/morphology rail (static + optional cheap model)."""
        key = focus_cache_key(self.sheet)
        panel, meta = enrich_focus_panel(
            self.sheet,
            learner=learner,
            tutor_reply=tutor_reply,
            model=self.focus_model,
            force_static=(
                not use_ai or not focus_model_enabled(self.focus_model)
            ),
        )
        self._focus_panel = panel
        self._focus_key = key
        self._focus_meta = meta

    def _finish(
        self,
        learner: str,
        raw: str,
        tool_delta: dict | None,
        final,
        usage: dict,
        *,
        input_mode: str = "text",
        log_learner: str | None = None,
        refresh_focus: bool = True,
    ) -> TurnResult:
        # Strip legacy sheet_delta, then parse multi-part tutor structure
        stripped, _ = extract_sheet_delta(raw if raw else "")
        if not stripped:
            stripped = raw or ""
        visible, tutor_parts = process_tutor_raw(stripped)
        parts_dict = tutor_parts.as_dict()
        composed = visible  # keep structured composition as learner-facing text

        self.sheet, _sheet_visible, notes = process_turn(
            self.sheet,
            learner,
            composed,
            tool_delta=tool_delta if self.use_tools else None,
        )
        visible = composed or _sheet_visible or compose_if_needed(tutor_parts)
        save_sheet(self.sheet_path, self.sheet)
        if refresh_focus:
            key = focus_cache_key(self.sheet)
            key_changed = self._focus_key != key
            has_panel = self._focus_panel is not None
            # Cheap AI when stretch changes, sheet tool fired, or first paint
            want_ai = (
                not has_panel
                or key_changed
                or any(n == "tool_update" for n in notes)
            )
            if want_ai or not has_panel:
                self._refresh_focus(
                    learner=learner,
                    tutor_reply=visible,
                    use_ai=want_ai,
                )
        if tutor_parts.has_recast() and "recast" not in notes:
            notes = list(notes) + ["recast"]
        if parts_dict.get("structured"):
            notes = list(notes) + ["structured_reply"]
        result = TurnResult(
            reply=visible,
            notes=notes,
            next_best=dict(self.sheet.get("next_best") or {}),
            skills=_skills_snapshot(self.sheet),
            usage=usage,
            tool_delta=tool_delta,
            input_mode=input_mode,
            stop_reason=getattr(final, "stop_reason", "") or "",
            focus_meta=dict(self._focus_meta or {}),
            parts=parts_dict,
        )
        if self.logger:
            self.logger.log_simple_turn(
                learner=log_learner if log_learner is not None else learner,
                visible=visible,
                state={
                    "next_best": result.next_best,
                    "skills": result.skills,
                    "notes": notes,
                    "input_mode": input_mode,
                    "focus_source": (self._focus_meta or {}).get("source"),
                    "parts": parts_dict,
                },
                stop_reason=result.stop_reason,
                usage=usage,
                extra={
                    "sheet_notes": notes,
                    "tool_delta": tool_delta,
                    "focus_meta": self._focus_meta,
                    "parts": parts_dict,
                },
            )
        return result

    def open_session(self) -> TurnResult:
        """Opening tutor greeting."""
        try:
            final, raw, tool_delta, usage, _ = tutor_turn(
                self.client,
                self.caps,
                self.system,
                [{"role": "user", "content": OPEN_HARNESS}],
                tools=self.tools,
            )
        except Exception as e:
            return TurnResult(
                reply="",
                error=f"{type(e).__name__}: {e}",
            )
        result = self._finish(
            "", raw or "", tool_delta, final, usage,
            log_learner="(session open)",
        )
        self.history = [
            {"role": "user", "content": OPEN_HARNESS},
            {"role": "assistant", "content": result.reply},
        ]
        self.messages_for_ui = [
            {
                "role": "tutor",
                "content": result.reply,
                "input_mode": "text",
                "parts": result.parts,
            },
        ]
        return result

    def user_turn(
        self,
        text: str,
        *,
        input_mode: str = "text",
    ) -> TurnResult:
        """Learner message → tutor reply + sheet update."""
        text = (text or "").strip()
        if not text:
            return TurnResult(reply="", error="empty message")

        scaffold = (self.sheet.get("receptive") or {}).get(
            "needs_english_scaffold", True)
        scaffold_line = (
            "SCAFFOLD: needs_english_scaffold=TRUE. Still Spanish-forward: "
            "praise/react in Spanish (¡Muy bien!); model in Spanish; short "
            "Spanish questions. English only for brief rescue / form contrast "
            "if they freeze — never English cheerleading or dual-subtitle "
            "every option (*word* *(translation)* lists)."
            if scaffold else
            "SCAFFOLD: needs_english_scaffold=FALSE. Mostly Spanish; English "
            "rare. Still praise in Spanish."
        )
        mode_line = (
            f"INPUT_MODE: {input_mode}. "
            + (
                "Learner spoke (STT may have typos); treat intent generously "
                "but still recast clear form errors."
                if input_mode == "speech"
                else "Learner typed."
            )
        )
        from .character_sheet import active_error_patterns, now_iso

        active = active_error_patterns(self.sheet)
        err_line = ""
        if active:
            top = active[0]
            err_line = (
                f"ERROR_FOCUS: {top['id']} ×{top['count']} — {top['label']}. "
                f"Hint: {top.get('teach_hint') or ''} "
                f"THIS TURN: recast if they miss it, then <try> the same form again "
                f"(do not only chat past the error).\n"
            )
        nb = self.sheet.get("next_best") or {}
        form_focus = nb.get("form_focus") or nb.get("error_pattern")
        teach_line = (
            f"TEACH_TARGET: practice form_focus={form_focus!r} "
            f"(can_do={nb.get('can_do')!r}). Put it in <model> + <try> this turn.\n"
            if form_focus
            else (
                f"TEACH_TARGET: next_best can_do={nb.get('can_do')!r} "
                f"activity={nb.get('activity') or nb.get('stretch')!r}. "
                f"Still include <model> + <try> — do not only ask open questions.\n"
            )
        )
        harness = (
            f"<harness_context>\n"
            f"now={now_iso()}\n"
            f"Character sheet is your model of this student — adapt to it.\n"
            f"next_best: {json.dumps(nb, ensure_ascii=False)}\n"
            f"{err_line}"
            f"{teach_line}"
            f"{scaffold_line}\n"
            f"{mode_line}\n"
            f"TEACHING RULE: you are a tutor, not a chat buddy. "
            f"Every turn needs a teach move: <model> and/or <try> "
            f"(and <recast>+retry when they err). "
            f"If they ask what something means: explain briefly, then model+try "
            f"so they USE it. "
            f"OUTPUT: <tutor> parts "
            f"(acknowledge / recast / explain / model / try / continue). "
            f"Form/register/construction error → <recast> REQUIRED, then "
            f"<try> same form (not a new topic). "
            f"Do not praise incorrect Spanish as correct. "
            f"LANGUAGE: Spanish-first praise; Spanish models; minimal English; "
            f"no 'Good job/You nailed it'; no dual-subtitle every phrase. "
            f"Do not skip form work only to chase next_best "
            f"(especially ERROR_FOCUS).\n"
            f"If this turn gives new evidence, ALSO call "
            f"update_character_sheet with a partial delta "
            f"(include error_patterns.last_examples when they repeat a construction error).\n"
            f"Never mention the sheet, tools, or tag names to the learner.\n"
            f"</harness_context>\n\n"
        )
        messages = self.history + [
            {"role": "user", "content": harness + text},
        ]
        try:
            final, raw, tool_delta, usage, _ = tutor_turn(
                self.client,
                self.caps,
                self.system,
                messages,
                tools=self.tools,
            )
        except Exception as e:
            return TurnResult(
                reply="",
                error=f"{type(e).__name__}: {e}",
                input_mode=input_mode,
            )

        result = self._finish(
            text, raw or "", tool_delta, final, usage, input_mode=input_mode,
        )
        self.history = self.history + [
            {"role": "user", "content": text},
            {"role": "assistant", "content": result.reply},
        ]
        if len(self.history) > 24:
            self.history = self.history[-24:]
        self.messages_for_ui.append(
            {"role": "you", "content": text, "input_mode": input_mode})
        self.messages_for_ui.append({
            "role": "tutor",
            "content": result.reply,
            "input_mode": "text",
            "parts": result.parts,
        })
        return result

    def reset_sheet(self) -> dict:
        self.sheet = default_sheet()
        save_sheet(self.sheet_path, self.sheet)
        self.history = []
        self.messages_for_ui = []
        self._focus_panel = None
        self._focus_key = None
        self._focus_meta = {"source": "static"}
        return self.sheet

    def sheet_human(self) -> str:
        return format_sheet_human(self.sheet)

    def sheet_public(self) -> dict:
        """JSON-safe sheet view for the web UI (includes focus rail cards)."""
        if self._focus_panel is None:
            # Instant static rail — never block UI on FOCUS_MODEL
            try:
                self._refresh_focus(use_ai=False)
            except Exception:
                self._focus_panel = build_focus_panel(self.sheet)
                self._focus_meta = {"source": "static"}
        panel = self._focus_panel or build_focus_panel(self.sheet)
        focus = panel.get("focus") if isinstance(panel, dict) else {}
        morph = panel.get("morphology") if isinstance(panel, dict) else []
        lex = panel.get("lexicon_focus") if isinstance(panel, dict) else []
        return {
            "identity": self.sheet.get("identity"),
            "skills": self.sheet.get("skills"),
            "grammar": {
                k: {kk: vv for kk, vv in (v or {}).items() if kk != "evidence"}
                for k, v in (self.sheet.get("grammar") or {}).items()
            },
            "affect": self.sheet.get("affect"),
            "receptive": self.sheet.get("receptive"),
            "coverage": self.sheet.get("coverage"),
            "next_best": self.sheet.get("next_best"),
            "lexicon": dict(list((self.sheet.get("lexicon") or {}).items())[:40]),
            "updated_at": self.sheet.get("updated_at"),
            "human": format_sheet_human(self.sheet),
            "focus": focus or {},
            "morphology": morph or [],
            "lexicon_focus": lex or [],
            "error_patterns": self.sheet.get("error_patterns") or {},
            "error_patterns_active": (
                panel.get("error_patterns_active")
                if isinstance(panel, dict) else []
            ) or [],
            "focus_source": (panel.get("source") if isinstance(panel, dict) else None)
            or (self._focus_meta or {}).get("source")
            or "static",
            "focus_model": self.focus_model,
        }

    def close(self) -> str | None:
        save_sheet(self.sheet_path, self.sheet)
        if self.logger:
            return str(self.logger.close(mode="conversational"))
        return None
