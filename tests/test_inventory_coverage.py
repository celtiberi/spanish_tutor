"""Phase 5 (docs/reviews-architecture-refactor.md): the §1.1a single-
inventory law as an executable gate.

Batch 2 (the flip) landed: the four legacy concept lists are TABLE-DERIVED —
session_memory.TOPIC_CONCEPT_NOUNS / SPANISH_CONCEPT_PAIRS, modes.
NOUN_TEXT_PAIRS / NEW_CONCRETE_NOUNS, observe's topic_vocab regex — and
teach_assets' in-code CONCEPT_LEXICON is DELETED (the pack asset sidecar is
the sole metadata source; ASSOCIATION_NOUNS, zero readers, deleted too).

The gate therefore no longer chases hand-listed inventories toward the
table; it pins the DERIVATION LAWS instead:

- every derived concept id folds to an association-table key (single
  inventory; the deprecation escape hatch stays available but is EMPTY);
- guard-6 / association / topic_vocab selection members are imageable:true
  table entries (imageable-vs-sidecar ruling: the table's `imageable`
  answers "can this concept be dual-coded for meaning"; the sidecar answers
  "do we have an asset" and never widens selection — the placement-open
  «hola» image is the one adjudicated decision.image_concept exemption);
- the topic palette excludes STRUCTURAL themes/keys (CHAR-BUG-007 fix) and
  the module default equals the production palette (one derivation);
- the sidecar never mints concepts and keeps resolving the legacy asset ids
  (cache filenames are pinned byte-exact via fold_asset_key).

Key space: fold_asset_key on both sides — derived ids use asset-normalized
form (rio, musica, estoy_bien) while the table uses natural Spanish (río,
música).  Needle strings inside needle→concept pairs are learner-surface
detection text (§1.1a allowed class iv), not inventory — the gate covers
the CONCEPT side.
"""

import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from tutor.association_table import (
    STRUCTURAL_KEYS,
    STRUCTURAL_THEMES,
    content_topic_keys,
    load_association_table,
)
from tutor.modes import NEW_CONCRETE_NOUNS, NOUN_TEXT_PAIRS
from tutor.observe import _TOPIC_VOCAB_TABLE_KEYS, probe_signals
from tutor.session_memory import (
    _TOPIC_PRIORITY_KEYS,
    SPANISH_CONCEPT_PAIRS,
    TOPIC_CONCEPT_NOUNS,
    topic_palette,
)
from tutor.teach_assets import (
    _lexicon,
    load_asset_sidecar,
    load_migration_deprecations,
    sidecar_lexicon,
)
from tutor.textnorm import fold_asset_key

ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "domain" / "spanish_a1"

# The 10 legacy asset ids (the deleted CONCEPT_LEXICON's keys) — cached
# image filenames derive from them, so the sidecar must keep resolving them.
LEGACY_ASSET_IDS = frozenset({
    "hola", "estoy_bien", "me_llamo", "soy_de", "cafe", "bote", "musica",
    "comida", "me_gusta", "rio",
})


class CoverageGate(unittest.TestCase):
    """§1.1a single-inventory law, executable (batch-2 shape)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = load_association_table(PACK_DIR)
        cls.deprecated = load_migration_deprecations(PACK_DIR)
        cls.allowed = {fold_asset_key(k) for k in cls.table} | {
            fold_asset_key(k) for k in cls.deprecated
        }
        cls.imageable_ids = {
            fold_asset_key(k)
            for k, e in cls.table.items()
            if e.get("imageable")
        }

    def _assert_covered(self, concepts, source: str) -> None:
        missing = sorted(
            {c for c in concepts if fold_asset_key(c) not in self.allowed}
        )
        self.assertEqual(
            missing,
            [],
            f"{source}: concepts neither association-table keys nor on "
            f"migration_deprecations.json: {missing}",
        )

    # -- derived-list coverage (now a law of the derivation, still pinned) --

    def test_topic_concept_nouns_covered(self) -> None:
        self._assert_covered(
            TOPIC_CONCEPT_NOUNS, "session_memory.TOPIC_CONCEPT_NOUNS"
        )

    def test_noun_text_pairs_concepts_covered_and_imageable(self) -> None:
        concepts = {concept for _needle, concept in NOUN_TEXT_PAIRS}
        self._assert_covered(concepts, "modes.NOUN_TEXT_PAIRS (concept side)")
        self.assertEqual(
            sorted(concepts - self.imageable_ids),
            [],
            "guard-6 selection must derive from imageable:true entries",
        )

    def test_new_concrete_nouns_covered_and_imageable(self) -> None:
        self._assert_covered(NEW_CONCRETE_NOUNS, "modes.NEW_CONCRETE_NOUNS")
        self.assertEqual(
            sorted(set(NEW_CONCRETE_NOUNS) - self.imageable_ids), []
        )

    def test_spanish_concept_pairs_covered(self) -> None:
        self._assert_covered(
            {concept for _needle, concept in SPANISH_CONCEPT_PAIRS},
            "session_memory.SPANISH_CONCEPT_PAIRS (concept side)",
        )

    def test_observe_topic_vocab_covered_and_imageable(self) -> None:
        self._assert_covered(
            _TOPIC_VOCAB_TABLE_KEYS, "observe topic_vocab members"
        )
        self.assertEqual(
            sorted(
                {fold_asset_key(k) for k in _TOPIC_VOCAB_TABLE_KEYS}
                - self.imageable_ids
            ),
            [],
        )

    def test_observe_vocab_drift_guard(self) -> None:
        # Honesty check: every member (and its accent-folded surface) really
        # fires topic_vocab.
        from tutor.textnorm import fold_lexical

        for word in _TOPIC_VOCAB_TABLE_KEYS:
            for surface in (word, fold_lexical(word)):
                self.assertIn(
                    "topic_vocab",
                    probe_signals(surface),
                    f"{surface!r} no longer fires",
                )

    # -- topic palette derivation laws (CHAR-BUG-007 fix) -------------------

    def test_topic_palette_excludes_structural(self) -> None:
        palette = set(TOPIC_CONCEPT_NOUNS)
        self.assertFalse(palette & STRUCTURAL_KEYS)
        for key in palette:
            entry = self.table.get(key)
            if entry is not None:
                self.assertNotIn(
                    str(entry.get("theme") or ""),
                    STRUCTURAL_THEMES,
                    key,
                )

    def test_topic_palette_module_default_equals_production(self) -> None:
        # ONE derivation: the module constant IS topic_palette(default table)
        # (conv_session._topic_nouns applies the same function to the
        # session's table).
        self.assertEqual(list(TOPIC_CONCEPT_NOUNS), topic_palette(self.table))

    def test_topic_palette_priority_tier_leads(self) -> None:
        # Order is behavior-bearing (first-present wins): the recorded
        # legacy priority tier — incident nouns ciudad/casa first — stays
        # ahead of the table tail.
        self.assertEqual(TOPIC_CONCEPT_NOUNS[:2], ("ciudad", "casa"))
        for key in _TOPIC_PRIORITY_KEYS:
            self.assertIn(key, self.table, f"priority key {key!r} left table")

    def test_content_topic_keys_no_table_degrades_to_priority_only(
        self,
    ) -> None:
        self.assertEqual(content_topic_keys(None), [])
        # Session without a table (missing/invalid pack) keeps the legacy
        # 21-surface fallback via the priority tier.
        self.assertEqual(len(topic_palette(None)), 21)

    # -- derivation validation raises loudly --------------------------------

    def test_guard6_derivation_rejects_non_imageable(self) -> None:
        from tutor.modes import _imageable_concept_id

        with self.assertRaises(ValueError):
            _imageable_concept_id(self.table, "hola", "test")  # imageable:false
        with self.assertRaises(ValueError):
            _imageable_concept_id(self.table, "not_a_key", "test")

    # -- deprecation escape hatch: EMPTY since batch 2 ----------------------

    def test_deprecation_list_empty_since_batch_2(self) -> None:
        # estoy bien graduated to a real in-pack table key (batch 2); the
        # hatch stays available (≤3, documented, disjoint) but is empty.
        self.assertEqual(dict(self.deprecated), {})
        self.assertLessEqual(len(self.deprecated), 3)
        for key, entry in self.deprecated.items():
            self.assertTrue(
                str(entry.get("reason") or "").strip(), f"{key}: no reason"
            )
            self.assertNotIn(key, self.table, f"{key}: deprecated AND in table")

    def test_estoy_bien_is_a_real_table_entry(self) -> None:
        entry = self.table.get("estoy bien")
        self.assertIsInstance(entry, dict)
        self.assertNotEqual(entry.get("in_pack"), False)  # pack content (U2)
        self.assertEqual(entry.get("theme"), "how_are_you")
        self.assertFalse(entry.get("imageable"))  # asset lives in the sidecar

    # -- scenes -------------------------------------------------------------

    def test_scenes_dir_stays_deleted(self) -> None:
        # Scenes DELETED 2026-08-03 (full-code-audit S9; ENGINEERING §4.6 —
        # git history is the archive): the pack ships no scenes dir and no
        # scene image concepts exist to cover.
        self.assertFalse((PACK_DIR / "scenes").exists())


class SidecarLoader(unittest.TestCase):
    def test_real_sidecar_loads_ten_entries(self) -> None:
        raw = load_asset_sidecar(PACK_DIR)
        self.assertEqual(len(raw), 10, sorted(raw))

    def test_sidecar_never_mints_concepts(self) -> None:
        table = load_association_table(PACK_DIR)
        deprecated = load_migration_deprecations(PACK_DIR)
        for key in load_asset_sidecar(PACK_DIR):
            self.assertTrue(
                key in table or key in deprecated,
                f"sidecar key {key!r} is neither a table key nor deprecated",
            )

    def test_minted_key_and_schema_errors_rejected(self) -> None:
        table = {
            "hola": {
                "gloss_en": "hi",
                "cognate_en": None,
                "false_friend": None,
                "keyword_en": None,
                "imageable": False,
                "theme": "greetings",
            }
        }
        sidecar = {
            "inventado": {  # not a table key, not deprecated
                "form": "Inventado",
                "caption": "minted",
                "visual": 0.9,
                "kind": "object",
                "aliases": ["inventado"],
                "image_prompt": "x",
            },
            "hola": {  # bad visual + missing image_prompt + unknown field
                "form": "Hola",
                "caption": "hello",
                "visual": 1.5,
                "kind": "gesture",
                "aliases": ["hola"],
                "extra": True,
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "association_table.json").write_text(
                json.dumps(table, ensure_ascii=False)
            )
            (Path(tmp) / "asset_sidecar.json").write_text(
                json.dumps(sidecar, ensure_ascii=False)
            )
            with self.assertRaises(ValueError) as ctx:
                load_asset_sidecar(Path(tmp))
        message = str(ctx.exception)
        self.assertIn("inventado", message)
        self.assertIn("visual", message)
        self.assertIn("image_prompt", message)
        self.assertIn("extra", message)


class SidecarSoleSource(unittest.TestCase):
    """Batch-2 law: the sidecar IS the asset lexicon (CONCEPT_LEXICON
    deleted); legacy asset ids and cached filenames keep resolving."""

    def test_effective_lexicon_is_the_sidecar(self) -> None:
        self.assertEqual(_lexicon(), sidecar_lexicon(PACK_DIR))

    def test_sidecar_keys_fold_to_legacy_asset_ids(self) -> None:
        folded = set(sidecar_lexicon(PACK_DIR))
        self.assertEqual(folded, set(LEGACY_ASSET_IDS))

    def test_cached_file_names_preserved(self) -> None:
        # The three bundled cache files must keep their historical names —
        # changing them orphans the on-disk images.
        lex = sidecar_lexicon(PACK_DIR)
        self.assertEqual(lex["hola"].get("file"), "hola.jpg")
        self.assertEqual(lex["estoy_bien"].get("file"), "estoy_bien.jpg")
        self.assertEqual(lex["me_llamo"].get("file"), "me_llamo.jpg")

    def test_schema_shape_per_entry(self) -> None:
        for key, meta in sidecar_lexicon(PACK_DIR).items():
            self.assertTrue(meta.get("form"), key)
            self.assertTrue(meta.get("caption"), key)
            self.assertTrue(meta.get("kind"), key)
            self.assertTrue(meta.get("prompt"), key)
            self.assertIsInstance(meta.get("aliases"), tuple, key)
            self.assertTrue(0.0 <= float(meta.get("visual")) <= 1.0, key)

    def test_missing_sidecar_degrades_to_empty_never_crashes(self) -> None:
        import tutor.teach_assets as ta

        saved = ta._sidecar_overlay
        try:
            with tempfile.TemporaryDirectory() as tmp, unittest.mock.patch(
                "tutor.config.DEFAULT_PACK_DIR", Path(tmp)
            ):
                ta._sidecar_overlay = None
                self.assertEqual(ta._lexicon(), {})
        finally:
            ta._sidecar_overlay = saved


if __name__ == "__main__":
    unittest.main()
