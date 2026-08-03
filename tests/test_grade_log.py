"""Grade log + feed (Phase 3, 2026-07-31)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tutor.character_sheet import default_sheet, process_turn
from tutor.grade_log import (
    ability_grade_diffs,
    build_grades_payload,
    grades_since_epoch,
    record_epoch,
    record_grade,
    record_grades_from_diff,
)


class TestGradeLog(unittest.TestCase):
    def test_record_and_list_newest_first(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "grades.jsonl"
            record_grade(
                field_id="IP-01",
                section="skills",
                direction="up",
                why="Greeted with Hola unprompted",
                evidence="Hola",
                from_status="unknown",
                to_status="emerging",
                ledger_path=path,
            )
            record_grade(
                field_id="IP-04",
                section="skills",
                direction="up",
                why="Said Estoy bien",
                evidence="estoy bien",
                ledger_path=path,
            )
            rows = grades_since_epoch(ledger_path=path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["field_id"], "IP-04")
            self.assertEqual(rows[1]["field_id"], "IP-01")
            self.assertIn("Greeted", rows[1]["why"])

    def test_epoch_hides_prior_grades(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "grades.jsonl"
            record_grade(
                field_id="IP-01",
                section="skills",
                direction="up",
                why="old learner grade here",
                ledger_path=path,
            )
            record_epoch(session_id="reset-1", ledger_path=path)
            record_grade(
                field_id="IP-03",
                section="skills",
                direction="up",
                why="new learner name formula",
                ledger_path=path,
            )
            rows = grades_since_epoch(ledger_path=path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["field_id"], "IP-03")

    def test_ability_diffs_direction(self):
        before = default_sheet()
        after = default_sheet()
        after["skills"]["IP-01"] = {
            "status": "emerging", "confidence": 0.4, "solid_uses": 1,
        }
        diffs = ability_grade_diffs(before, after)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0]["field_id"], "IP-01")
        self.assertEqual(diffs[0]["direction"], "up")

    def test_process_turn_writes_grade_log(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "grades.jsonl"
            process_turn(
                default_sheet(),
                "Hola",
                "¡Hola!",
                tool_delta={
                    "reason": "Learner opened with Hola unprompted",
                    "evidence": "Hola",
                    "skills": {
                        "IP-01": {"status": "emerging", "confidence": 0.35},
                    },
                },
                session_id="t1",
                grade_log_path=str(path),
            )
            rows = grades_since_epoch(ledger_path=path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["field_id"], "IP-01")
            self.assertEqual(rows[0]["direction"], "up")
            self.assertIn("Hola", rows[0]["why"])

    def test_no_tool_writes_no_grades(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "grades.jsonl"
            process_turn(
                default_sheet(),
                "Hola estoy bien",
                "¡Qué bien!",
                grade_log_path=str(path),
            )
            self.assertEqual(grades_since_epoch(ledger_path=path), [])

    def test_payload_shape(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "grades.jsonl"
            record_grades_from_diff(
                default_sheet(),
                {
                    **default_sheet(),
                    "skills": {
                        **default_sheet()["skills"],
                        "IP-01": {
                            "status": "known",
                            "confidence": 0.9,
                            "solid_uses": 2,
                        },
                    },
                },
                why="Solid greeting after spaced reuse",
                ledger_path=path,
            )
            sheet = default_sheet()
            sheet["skills"]["IP-01"] = {
                "status": "known", "confidence": 0.9, "solid_uses": 2,
            }
            payload = build_grades_payload(sheet, ledger_path=path)
            self.assertFalse(payload["empty"])
            self.assertEqual(payload["counts"]["known"], 1)
            self.assertEqual(len(payload["grades"]), 1)
            self.assertEqual(payload["groups"], [])


if __name__ == "__main__":
    unittest.main()
