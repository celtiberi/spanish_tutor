"""r7 S4 association table: loader schema, anchors, pack MWU coverage.

Success criteria under test (docs/pedagogy-research-r7-association-intro.md
section 7 S4): unit01 greeting/farewell/courtesy MWUs 100% covered; false
friends >= 15; the router can never apply R-A to a listed false friend.
"""

import json
import tempfile
import unittest
from pathlib import Path

from tutor.association_table import (
    MAX_GLOSS_WORDS,
    anchor_for,
    entries_for_theme,
    is_false_friend,
    load_association_table,
    same_theme,
)

ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "course_packs" / "spanish_a1"

# tutor/corpus.py has no MWU parser (only topic titles / planner index), so
# the unit01 greeting/farewell/courtesy multiword formulas are hand-listed
# here. An honesty check below asserts each one really appears in the pack
# unit text, so this list cannot silently drift from the pack.
PACK_MWUS = [
    "buenos días",
    "buenas tardes",
    "buenas noches",
    "hasta luego",
    "hasta mañana",
    "mucho gusto",
    "por favor",
    "muchas gracias",
    "de nada",
]


class LoadRealTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table = load_association_table(PACK_DIR)

    def test_glosses_at_most_six_words(self) -> None:
        for key, entry in self.table.items():
            self.assertLessEqual(
                len(entry["gloss_en"].split()),
                MAX_GLOSS_WORDS,
                f"{key}: gloss_en too long: {entry['gloss_en']!r}",
            )

    def test_false_friend_count(self) -> None:
        traps = [k for k in self.table if is_false_friend(self.table, k)]
        self.assertGreaterEqual(len(traps), 15, traps)

    def test_no_entry_is_both_trap_and_anchor(self) -> None:
        both = [
            k
            for k, v in self.table.items()
            if v.get("cognate_en") and v.get("false_friend")
        ]
        self.assertEqual(both, [])

    def test_farewell_pair_shares_theme(self) -> None:
        self.assertIn("hasta luego", self.table)
        self.assertIn("adiós", self.table)
        self.assertTrue(same_theme(self.table, "hasta luego", "adiós"))
        farewells = entries_for_theme(self.table, self.table["adiós"]["theme"])
        self.assertIn("hasta luego", farewells)
        self.assertIn("adiós", farewells)


class AnchorPreference(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table = load_association_table(PACK_DIR)

    def test_cognate_entry_returns_cognate(self) -> None:
        cognates = [
            k
            for k, v in self.table.items()
            if v.get("cognate_en") and not v.get("false_friend")
        ]
        self.assertTrue(cognates)
        for key in cognates:
            anchor = anchor_for(self.table, key)
            self.assertEqual(anchor["type"], "cognate", key)
            self.assertEqual(anchor["cognate_en"], self.table[key]["cognate_en"])

    def test_false_friend_never_gets_cognate_anchor(self) -> None:
        traps = [k for k in self.table if is_false_friend(self.table, k)]
        self.assertTrue(traps)
        for key in traps:
            anchor = anchor_for(self.table, key)
            self.assertIn(anchor["type"], ("keyword", "gloss"), key)
            self.assertNotIn("cognate_en", anchor, key)
            self.assertIn("false_friend", anchor, key)

    def test_plain_entry_returns_gloss(self) -> None:
        plain = [
            k
            for k, v in self.table.items()
            if not v.get("cognate_en")
            and not v.get("keyword_en")
            and not v.get("false_friend")
        ]
        self.assertTrue(plain)
        for key in plain:
            anchor = anchor_for(self.table, key)
            self.assertEqual(anchor["type"], "gloss", key)
            self.assertEqual(anchor["gloss_en"], self.table[key]["gloss_en"])

    def test_is_false_friend_unknown_key(self) -> None:
        self.assertFalse(is_false_friend(self.table, "no-such-key"))
        self.assertFalse(same_theme(self.table, "hola", "no-such-key"))


class ValidationErrors(unittest.TestCase):
    def test_bad_table_lists_all_offending_keys(self) -> None:
        bad = {
            "sin_glosa": {  # missing gloss_en
                "cognate_en": None,
                "false_friend": None,
                "keyword_en": None,
                "imageable": False,
                "theme": "test",
            },
            "glosa_larga": {  # 7-word gloss
                "gloss_en": "one two three four five six seven",
                "cognate_en": None,
                "false_friend": None,
                "keyword_en": None,
                "imageable": False,
                "theme": "test",
            },
            "trampa_ancla": {  # trap cannot be an anchor
                "gloss_en": "trap",
                "cognate_en": "trap",
                "false_friend": "NOT a trap; means test",
                "keyword_en": None,
                "imageable": False,
                "theme": "test",
            },
            "bien": {  # valid entry: must NOT be named in the error
                "gloss_en": "well / fine",
                "cognate_en": None,
                "false_friend": None,
                "keyword_en": None,
                "imageable": False,
                "theme": "test",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "association_table.json").write_text(
                json.dumps(bad, ensure_ascii=False)
            )
            with self.assertRaises(ValueError) as ctx:
                load_association_table(Path(tmp))
        message = str(ctx.exception)
        for key in ("sin_glosa", "glosa_larga", "trampa_ancla"):
            self.assertIn(key, message)
        self.assertNotIn("bien", message)


class PackMWUCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table = load_association_table(PACK_DIR)
        cls.pack_text = "\n".join(
            p.read_text() for p in sorted(PACK_DIR.glob("*.md"))
        ).lower()

    def test_hand_list_matches_pack(self) -> None:
        # Honesty check: every hand-listed MWU actually appears in the pack.
        for mwu in PACK_MWUS:
            self.assertIn(mwu, self.pack_text, f"{mwu!r} not found in pack text")

    def test_every_pack_mwu_has_table_entry(self) -> None:
        missing = [m for m in PACK_MWUS if m not in self.table]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
