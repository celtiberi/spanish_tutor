"""Domain-model data validation (S10, full-code-audit 2026-08-03).

domain/spanish_a1/ is the single source of truth for the level slice:
can-dos, grammar forms + paradigms, scope, misconception catalog. These
tests pin (1) the files parse and cross-reference cleanly, (2) the
module-level symbols consumers import are EXACTLY the JSON content (the
migration equality-of-shape check, kept forever), (3) malformed data
raises loudly — a broken domain file is a startup error, never a silent
default (no-hide).
"""

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from tutor import config
from tutor.domain_data import (
    CAN_DOS_FILENAME,
    DOMAIN_FILENAMES,
    DOMAIN_SCOPE_FILENAME,
    FORM_INVENTORY_FIELDS,
    GRAMMAR_FORMS_FILENAME,
    MISCONCEPTIONS_FILENAME,
    MORPHOLOGY_FIELDS,
    cached_default_domain,
    load_domain,
)

PACK = config.DEFAULT_PACK_DIR


def _read(name: str) -> dict:
    return json.loads((PACK / name).read_text())


class TestFilesParse(unittest.TestCase):
    def test_all_domain_files_exist_and_parse(self):
        for name in DOMAIN_FILENAMES:
            with self.subTest(file=name):
                doc = _read(name)
                self.assertIsInstance(doc, dict)
                self.assertTrue(doc)

    def test_load_domain_accepts_the_shipped_pack(self):
        d = load_domain(PACK)
        self.assertTrue(d.can_dos)
        self.assertTrue(d.form_inventory)
        self.assertTrue(d.misconceptions)
        self.assertTrue(d.domain_scope.get("level"))


class TestLoadedSymbolsEqualJson(unittest.TestCase):
    """The migration equality-of-shape validation (S10 discipline): what
    consumers import IS the JSON content, per the documented mapping."""

    def test_can_dos_sections(self):
        from tutor.can_dos import (
            CAN_DOS,
            CAN_DO_THEMES,
            MORPHOLOGY_BY_CANDO,
            STRETCH_ACTIVITIES,
        )

        doc = _read(CAN_DOS_FILENAME)
        self.assertEqual(CAN_DOS, doc["can_dos"])
        # tuples are the historical in-memory shape; arrays on disk
        self.assertEqual(
            {k: list(v) for k, v in CAN_DO_THEMES.items()},
            doc["can_do_themes"],
        )
        for themes in CAN_DO_THEMES.values():
            self.assertIsInstance(themes, tuple)
        self.assertEqual(MORPHOLOGY_BY_CANDO, doc["morphology_by_can_do"])
        self.assertEqual(STRETCH_ACTIVITIES, doc["stretch_activities"])

    def test_theme_to_can_do_is_the_pure_inversion(self):
        from tutor.can_dos import CAN_DO_THEMES, THEME_TO_CAN_DO

        self.assertEqual(
            THEME_TO_CAN_DO,
            {t: cid for cid, ts in CAN_DO_THEMES.items() for t in ts},
        )
        n_pairs = sum(len(ts) for ts in CAN_DO_THEMES.values())
        self.assertEqual(len(THEME_TO_CAN_DO), n_pairs)  # no silent overwrite

    def test_grammar_forms_split(self):
        from tutor.can_dos import FORM_INVENTORY, MORPHOLOGY_BY_FORM

        doc = _read(GRAMMAR_FORMS_FILENAME)
        self.assertEqual(set(FORM_INVENTORY), set(doc))
        for fid, rec in doc.items():
            self.assertEqual(
                FORM_INVENTORY[fid],
                {f: rec[f] for f in FORM_INVENTORY_FIELDS},
            )
            if any(f in rec for f in MORPHOLOGY_FIELDS):
                self.assertIn(fid, MORPHOLOGY_BY_FORM)
                self.assertEqual(
                    MORPHOLOGY_BY_FORM[fid],
                    {f: rec[f] for f in MORPHOLOGY_FIELDS},
                )
            else:
                self.assertNotIn(fid, MORPHOLOGY_BY_FORM)

    def test_domain_scope_verbatim(self):
        from tutor.character_sheet import DOMAIN_SCOPE

        self.assertEqual(DOMAIN_SCOPE, _read(DOMAIN_SCOPE_FILENAME))

    def test_misconceptions_with_detect_tuples(self):
        from tutor.character_sheet import ERROR_PATTERN_CATALOG

        doc = _read(MISCONCEPTIONS_FILENAME)
        self.assertEqual(list(ERROR_PATTERN_CATALOG), list(doc))  # order too
        for pid, rec in doc.items():
            cat = ERROR_PATTERN_CATALOG[pid]
            expected = {**rec, "detect": [tuple(p) for p in rec["detect"]]}
            self.assertEqual(cat, expected)
            for pair in cat["detect"]:
                self.assertIsInstance(pair, tuple)
                self.assertEqual(len(pair), 2)

    def test_detect_resolve_compiled_at_load(self):
        d = cached_default_domain()
        self.assertEqual(set(d.detect_compiled), set(d.misconceptions))
        self.assertEqual(set(d.resolve_compiled), set(d.misconceptions))
        for pid, cat in d.misconceptions.items():
            self.assertEqual(len(d.detect_compiled[pid]), len(cat["detect"]))
            self.assertEqual(len(d.resolve_compiled[pid]), len(cat["resolve"]))
            for (rx, note), (pat, note_raw) in zip(
                d.detect_compiled[pid], cat["detect"]
            ):
                self.assertIsInstance(rx, re.Pattern)
                self.assertEqual(rx.pattern, pat)
                self.assertTrue(rx.flags & re.IGNORECASE)
                self.assertEqual(note, note_raw)


class TestCrossReferences(unittest.TestCase):
    def test_misconception_form_ids_exist(self):
        forms = set(_read(GRAMMAR_FORMS_FILENAME))
        for pid, rec in _read(MISCONCEPTIONS_FILENAME).items():
            fid = rec.get("form_id")
            if fid is not None:
                self.assertIn(fid, forms, f"misconceptions[{pid}]")

    def test_all_can_do_references_exist(self):
        doc = _read(CAN_DOS_FILENAME)
        ids = set(doc["can_dos"])
        for pid, rec in _read(MISCONCEPTIONS_FILENAME).items():
            for cid in rec.get("can_dos") or []:
                self.assertIn(cid, ids, f"misconceptions[{pid}]")
        for fid, rec in _read(GRAMMAR_FORMS_FILENAME).items():
            for cid in rec["supports"]:
                self.assertIn(cid, ids, f"grammar_forms[{fid}].supports")
        for cid in doc["can_do_themes"]:
            self.assertIn(cid, ids, "can_do_themes")
        for cid in doc["morphology_by_can_do"]:
            self.assertIn(cid, ids, "morphology_by_can_do")

    def test_form_hooks_exist_in_grammar_forms(self):
        forms = set(_read(GRAMMAR_FORMS_FILENAME))
        for cid, meta in _read(CAN_DOS_FILENAME)["can_dos"].items():
            for fid in meta.get("form_hooks") or []:
                self.assertIn(fid, forms, f"can_dos[{cid}].form_hooks")

    def test_misconception_sources_unique(self):
        seen = {}
        for pid, rec in _read(MISCONCEPTIONS_FILENAME).items():
            src = rec.get("source")
            if src is None:
                continue
            self.assertNotIn(src, seen, f"{pid} duplicates {seen.get(src)}")
            seen[src] = pid
        self.assertTrue(seen)  # the mined pack provenance is present

    def test_can_do_themes_exist_in_association_table(self):
        from tutor.association_table import cached_default_table

        table_themes = {v["theme"] for v in cached_default_table().values()}
        for cid, themes in _read(CAN_DOS_FILENAME)["can_do_themes"].items():
            for theme in themes:
                self.assertIn(
                    theme, table_themes,
                    f"can_do_themes[{cid}]: {theme!r} routes no table items",
                )

    def test_scope_lists_disjoint_and_nonempty(self):
        doc = _read(DOMAIN_SCOPE_FILENAME)
        lists = {
            f: doc[f]
            for f in (
                "deferred_do_not_introduce",
                "out_of_scope_decline_briefly",
                "recognition_only",
            )
        }
        for name, items in lists.items():
            self.assertTrue(items, name)
            self.assertEqual(len(items), len(set(items)), f"{name} has dupes")
        names = list(lists)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                overlap = set(lists[a]) & set(lists[b])
                self.assertFalse(overlap, f"{a} ∩ {b}: {overlap}")


class TestMalformedDataRaisesLoudly(unittest.TestCase):
    """A broken domain file must be a loud load error (no-hide), never a
    silent default."""

    def _pack_copy(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for name in DOMAIN_FILENAMES:
            shutil.copy(PACK / name, tmp / name)
        return tmp

    def _mutate(self, pack: Path, name: str, fn):
        doc = json.loads((pack / name).read_text())
        fn(doc)
        (pack / name).write_text(json.dumps(doc, ensure_ascii=False))

    def test_copy_of_shipped_pack_loads(self):
        load_domain(self._pack_copy())

    def test_missing_file_raises(self):
        pack = self._pack_copy()
        (pack / MISCONCEPTIONS_FILENAME).unlink()
        with self.assertRaises(FileNotFoundError):
            load_domain(pack)

    def test_invalid_json_raises_with_filename(self):
        pack = self._pack_copy()
        (pack / CAN_DOS_FILENAME).write_text("{not json")
        with self.assertRaisesRegex(ValueError, CAN_DOS_FILENAME):
            load_domain(pack)

    def test_bad_detect_regex_raises(self):
        pack = self._pack_copy()
        self._mutate(
            pack, MISCONCEPTIONS_FILENAME,
            lambda d: d["tengo_not_tango"]["detect"].append(["(unclosed", "x"]),
        )
        with self.assertRaisesRegex(ValueError, "does not compile"):
            load_domain(pack)

    def test_dangling_misconception_form_id_raises(self):
        pack = self._pack_copy()
        self._mutate(
            pack, MISCONCEPTIONS_FILENAME,
            lambda d: d["tengo_not_tango"].__setitem__("form_id", "no_such_form"),
        )
        with self.assertRaisesRegex(ValueError, "no_such_form"):
            load_domain(pack)

    def test_duplicate_source_raises(self):
        pack = self._pack_copy()

        def dup(d):
            d["age_with_ser"]["source"] = d["tener_regularized"]["source"]

        self._mutate(pack, MISCONCEPTIONS_FILENAME, dup)
        with self.assertRaisesRegex(ValueError, "duplicate source"):
            load_domain(pack)

    def test_theme_routed_to_two_can_dos_raises(self):
        pack = self._pack_copy()
        self._mutate(
            pack, CAN_DOS_FILENAME,
            lambda d: d["can_do_themes"]["IP-06"].append("greetings"),
        )
        with self.assertRaisesRegex(ValueError, "at most ONE can-do"):
            load_domain(pack)

    def test_unknown_supports_can_do_raises(self):
        pack = self._pack_copy()
        self._mutate(
            pack, GRAMMAR_FORMS_FILENAME,
            lambda d: d["present_ser"]["supports"].append("IP-99"),
        )
        with self.assertRaisesRegex(ValueError, "IP-99"):
            load_domain(pack)

    def test_partial_morphology_raises(self):
        pack = self._pack_copy()

        def strip_paradigm(d):
            del d["present_ser"]["paradigm"]

        self._mutate(pack, GRAMMAR_FORMS_FILENAME, strip_paradigm)
        with self.assertRaisesRegex(ValueError, "partial morphology"):
            load_domain(pack)

    def test_missing_stretch_fallback_raises(self):
        pack = self._pack_copy()
        self._mutate(
            pack, CAN_DOS_FILENAME,
            lambda d: d["stretch_activities"].pop("open_chat_and_notice"),
        )
        with self.assertRaisesRegex(ValueError, "open_chat_and_notice"):
            load_domain(pack)

    def test_error_lists_every_problem_not_just_first(self):
        pack = self._pack_copy()

        def two_bugs(d):
            d["tengo_not_tango"]["form_id"] = "no_such_form"
            d["age_with_ser"]["detect"] = [["(unclosed", "x"]]

        self._mutate(pack, MISCONCEPTIONS_FILENAME, two_bugs)
        with self.assertRaises(ValueError) as ctx:
            load_domain(pack)
        msg = str(ctx.exception)
        self.assertIn("no_such_form", msg)
        self.assertIn("does not compile", msg)


class TestMechanicsReadTheData(unittest.TestCase):
    """The default sheet blocks are pure projections of the datasets."""

    def test_default_blocks_cover_the_inventories(self):
        from tutor.can_dos import (
            CAN_DOS,
            FORM_INVENTORY,
            default_grammar_block,
            default_skills_block,
        )

        self.assertEqual(set(default_skills_block()), set(CAN_DOS))
        self.assertEqual(set(default_grammar_block()), set(FORM_INVENTORY))

    def test_detection_still_works_from_data(self):
        from tutor.character_sheet import (
            detect_error_pattern_hits,
            detect_error_pattern_resolves,
        )

        hits = detect_error_pattern_hits("Yo está en mi bote.")
        self.assertIn("estar_yo_estoy_vs_esta", [p for p, _ in hits])
        self.assertIn(
            "estar_yo_estoy_vs_esta",
            detect_error_pattern_resolves("Estoy bien, gracias."),
        )
        self.assertEqual(detect_error_pattern_hits(""), [])


if __name__ == "__main__":
    unittest.main()
