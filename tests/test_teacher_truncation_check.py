"""Ensure the truncation linter stays green on the teacher path."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_teacher_truncation.py"


class TeacherTruncationCheck(unittest.TestCase):
    def test_teacher_tree_clean(self) -> None:
        r = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            self.fail(
                "Teacher-path truncation check failed:\n"
                + (r.stdout or "")
                + (r.stderr or "")
            )


if __name__ == "__main__":
    unittest.main()
