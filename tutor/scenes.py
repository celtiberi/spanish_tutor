"""Scene open goals — quest log, not linear scripts.

See docs/teaching-system.md. exit_predicate is a sheet query.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config

SCENES_DIR_NAME = "scenes"


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
    max_open: int = 3,
) -> list[dict[str, Any]]:
    """Scenes whose exit_predicate is not yet satisfied (open goals)."""
    scenes = load_scenes(pack_dir)
    open_list: list[dict[str, Any]] = []
    for sc in scenes:
        goal = sc.get("goal") or {}
        pred = goal.get("exit_predicate")
        if evaluate_exit_predicate(sheet, pred):
            continue
        open_list.append(sc)
        if len(open_list) >= max_open:
            break
    return open_list


def scene_hints_for_prompt(scenes: list[dict]) -> list[dict]:
    """Compact scene hints for the AI (not full scripts)."""
    out = []
    for sc in scenes:
        goal = sc.get("goal") or {}
        inp = sc.get("input") or {}
        prod = sc.get("production") or {}
        out.append({
            "id": sc.get("id"),
            "can_do": goal.get("can_do"),
            "target_forms": goal.get("target_forms"),
            "model_lines": (inp.get("model_lines") or [])[:4],
            "image_concept": inp.get("image_concept"),
            "elicit": prod.get("elicit"),
            "transfer": (sc.get("transfer") or {}).get("elicit"),
            "notice_errors": (sc.get("notice") or {}).get("error_patterns"),
        })
    return out
