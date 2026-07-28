"""Scene open goals — quest log, not linear scripts.

See docs/teaching-system.md. exit_predicate is a sheet query.

ConvergentTaskRuntime fields (r6 Rank-4, docs/pedagogy-research-r6-practice-mix.md
§5): scenes MAY additionally carry `primary_exit` (single machine-checkable exit
with evidence slots), `tutor_private_info` (info-gap values the tutor holds and
must not volunteer), and `learner_must_obtain` (slot ids the learner fills by
asking in Spanish). Optional and backward-compatible — legacy scenes without
them keep working. Runtime lives in tutor/task_runtime.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config

SCENES_DIR_NAME = "scenes"

# Optional ConvergentTaskRuntime fields (r6 Rank-4) — schema-checked on load.
TASK_FIELDS = ("primary_exit", "tutor_private_info", "learner_must_obtain")


def validate_scene(scene: dict) -> list[str]:
    """Schema-check the optional ConvergentTaskRuntime fields.

    Legacy fields are untouched. Returns human-readable errors; every error
    names the scene id and the offending field. Empty list = valid.
    """
    sid = str(scene.get("id") or "<no-id>")
    errs: list[str] = []
    pe = scene.get("primary_exit")
    if pe is None:
        for f in ("tutor_private_info", "learner_must_obtain"):
            if f in scene:
                errs.append(f"scene {sid}: {f} present without primary_exit")
        return errs
    if not isinstance(pe, dict):
        return [f"scene {sid}: primary_exit must be an object"]
    desc = pe.get("description")
    if not (isinstance(desc, str) and desc.strip()):
        errs.append(f"scene {sid}: primary_exit.description must be a non-empty string")
    slots = pe.get("slots")
    slot_ids: list[str] = []
    if not (isinstance(slots, list) and slots):
        errs.append(f"scene {sid}: primary_exit.slots must be a non-empty list")
    else:
        for i, slot in enumerate(slots):
            if not isinstance(slot, dict):
                errs.append(f"scene {sid}: primary_exit.slots[{i}] must be an object")
                continue
            slot_id = slot.get("id")
            if not (isinstance(slot_id, str) and slot_id.strip()):
                errs.append(f"scene {sid}: primary_exit.slots[{i}].id must be a non-empty string")
            elif slot_id in slot_ids:
                errs.append(f"scene {sid}: primary_exit.slots[{i}].id duplicates '{slot_id}'")
            else:
                slot_ids.append(slot_id)
            ev = slot.get("evidence_any")
            if not (
                isinstance(ev, list)
                and ev
                and all(isinstance(e, str) and e.strip() for e in ev)
            ):
                errs.append(
                    f"scene {sid}: primary_exit.slots[{i}].evidence_any "
                    "must be a non-empty list of non-empty strings"
                )
    tpi = scene.get("tutor_private_info")
    if tpi is not None:
        if not isinstance(tpi, dict):
            errs.append(f"scene {sid}: tutor_private_info must be an object")
            tpi = None
        else:
            for k, v in tpi.items():
                if k not in slot_ids:
                    errs.append(
                        f"scene {sid}: tutor_private_info key '{k}' is not a primary_exit slot id"
                    )
                if not (isinstance(v, str) and v.strip()):
                    errs.append(
                        f"scene {sid}: tutor_private_info['{k}'] must be a non-empty string"
                    )
    lmo = scene.get("learner_must_obtain")
    if lmo is not None:
        if not (isinstance(lmo, list) and all(isinstance(x, str) for x in lmo)):
            errs.append(f"scene {sid}: learner_must_obtain must be a list of slot-id strings")
        else:
            for x in lmo:
                if x not in slot_ids:
                    errs.append(
                        f"scene {sid}: learner_must_obtain id '{x}' is not a primary_exit slot id"
                    )
                elif not (isinstance(tpi, dict) and x in tpi):
                    errs.append(
                        f"scene {sid}: learner_must_obtain id '{x}' has no "
                        "tutor_private_info value (the info-gap needs one)"
                    )
    return errs


def scenes_dir_for_pack(pack_dir: Path | None = None) -> Path:
    pack = Path(pack_dir or config.DEFAULT_PACK_DIR)
    return pack / SCENES_DIR_NAME


def load_scenes(pack_dir: Path | None = None) -> list[dict[str, Any]]:
    """Load all scene JSON files from pack scenes/."""
    d = scenes_dir_for_pack(pack_dir)
    if not d.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(d.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("id"):
                data["_path"] = str(path)
                task_errors = validate_scene(data)
                if task_errors:
                    # Scene still loads (legacy behavior) but a half-valid
                    # task schema never reaches the runtime: strip the task
                    # fields and surface the named errors for callers/tests.
                    data["_task_errors"] = task_errors
                    for f in TASK_FIELDS:
                        data.pop(f, None)
                out.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return out


def evaluate_exit_predicate(sheet: dict, predicate: str | None) -> bool:
    """Minimal sheet-query language for scene completion."""
    if not predicate:
        return False
    pred = predicate.strip()
    # unprompted_form:FORM_ID:min=N  OR skill:IP-04:min_conf=0.4
    if pred.startswith("unprompted_form:") or pred.startswith("form:"):
        # form:present_estar_person:min=2 — use grammar confidence + evidence
        parts = pred.split(":")
        if len(parts) < 2:
            return False
        form_id = parts[1]
        min_n = 1
        for p in parts[2:]:
            if p.startswith("min="):
                try:
                    min_n = int(p.split("=", 1)[1])
                except ValueError:
                    pass
        g = (sheet.get("grammar") or {}).get(form_id) or {}
        conf = float(g.get("confidence") or 0)
        ev = g.get("evidence") or []
        # heuristic: confidence and evidence length as proxy for uses
        uses = len(ev) if isinstance(ev, list) else 0
        if conf >= 0.35 and uses >= min_n:
            return True
        if conf >= 0.55:
            return True
        return False

    if pred.startswith("skill:"):
        parts = pred.split(":")
        if len(parts) < 2:
            return False
        cid = parts[1]
        min_conf = 0.4
        for p in parts[2:]:
            if p.startswith("min_conf="):
                try:
                    min_conf = float(p.split("=", 1)[1])
                except ValueError:
                    pass
        sk = (sheet.get("skills") or {}).get(cid) or {}
        return float(sk.get("confidence") or 0) >= min_conf

    return False


def open_scenes_for_sheet(
    sheet: dict,
    pack_dir: Path | None = None,
    *,
    max_open: int | None = None,
) -> list[dict[str, Any]]:
    """Scenes whose exit_predicate is not yet satisfied (open goals).

    max_open=None/0 → all open scenes (testing default). Positive int caps list.
    """
    scenes = load_scenes(pack_dir)
    open_list: list[dict[str, Any]] = []
    for sc in scenes:
        goal = sc.get("goal") or {}
        pred = goal.get("exit_predicate")
        if evaluate_exit_predicate(sheet, pred):
            continue
        open_list.append(sc)
        if max_open and max_open > 0 and len(open_list) >= max_open:
            break
    return open_list


def scene_hints_for_prompt(scenes: list[dict]) -> list[dict]:
    """Scene hints for the AI teacher — full fields, no silent clipping."""
    out = []
    for sc in scenes:
        goal = sc.get("goal") or {}
        inp = sc.get("input") or {}
        prod = sc.get("production") or {}
        out.append({
            "id": sc.get("id"),
            "can_do": goal.get("can_do"),
            "target_forms": goal.get("target_forms"),
            "model_lines": list(inp.get("model_lines") or []),
            "image_concept": inp.get("image_concept"),
            "elicit": prod.get("elicit"),
            "transfer": (sc.get("transfer") or {}).get("elicit"),
            "notice_errors": (sc.get("notice") or {}).get("error_patterns"),
            "goal": goal,
            "title": sc.get("title") or sc.get("name"),
            # ConvergentTaskRuntime fields (r6 Rank-4) — teacher-facing;
            # tutor_private_info is private from the LEARNER, not the teacher.
            "primary_exit": sc.get("primary_exit"),
            "tutor_private_info": sc.get("tutor_private_info"),
            "learner_must_obtain": sc.get("learner_must_obtain"),
        })
    return out
