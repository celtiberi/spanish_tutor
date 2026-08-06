"""XP engine (docs/design-xp-progression.md): evidence-backed, monotone,
once-per-crossing, epoch-scoped; skills pay only via can_do_known."""

import unittest

from tutor.xp import compute_xp, level_thresholds


def g(item, frm, to, section="lexicon", ts="2026-08-05T10:00:00",
      evidence=None):
    # Default evidence SHOWS the item (the audit demands it; tests that
    # probe the audit pass their own evidence).
    ev = evidence if evidence is not None else item.replace("_", " ")
    return {"kind": "grade", "field_id": item, "section": section,
            "from_status": frm, "to_status": to, "ts": ts, "evidence": ev}


def m(kind, key, **extra):
    return {"kind": kind, "key": key, "ts": "2026-08-05T10:00:00", **extra}


class TestBandCrossings(unittest.TestCase):
    def test_single_and_path_pay(self):
        r = compute_xp([g("hola", "unknown", "emerging")], [])
        self.assertEqual(r["total"], 10)
        # A jump pays the whole path crossed
        r = compute_xp([g("bien", "unknown", "known")], [])
        self.assertEqual(r["total"], 10 + 15 + 25)

    def test_once_per_band_no_remilk(self):
        rows = [g("hola", "unknown", "emerging"),
                g("hola", "unknown", "emerging"),
                g("hola", "emerging", "fragile")]
        self.assertEqual(compute_xp(rows, [])["total"], 10 + 15)

    def test_down_then_up_pays_delta_only(self):
        rows = [g("hola", "unknown", "fragile"),      # 10+15
                g("hola", "fragile", "emerging"),     # down: 0
                g("hola", "emerging", "fragile"),     # re-cross: 0 (paid)
                g("hola", "fragile", "known")]        # +25
        self.assertEqual(compute_xp(rows, [])["total"], 10 + 15 + 25)

    def test_skills_section_pays_nothing_via_bands(self):
        rows = [g("IP-01", "unknown", "known", section="skills")]
        self.assertEqual(compute_xp(rows, [])["total"], 0)

    def test_monotone_never_negative(self):
        rows = [g("hola", "emerging", "unknown")]  # pure down
        self.assertEqual(compute_xp(rows, [])["total"], 0)


class TestEvidenceAudit(unittest.TestCase):
    """XP pays only when the quoted evidence shows the item (the sam
    inflation forensics, 2026-08-05: 'esta bein' minted bien+estar)."""

    def test_garble_evidence_pays_nothing(self):
        rows = [g("bien", "unknown", "emerging", evidence="esta bein"),
                g("estar", "unknown", "emerging", evidence="esta bein")]
        self.assertEqual(compute_xp(rows, [])["total"], 0)

    def test_real_evidence_pays(self):
        rows = [g("bien", "unknown", "emerging", evidence="estoy bien hoy")]
        self.assertEqual(compute_xp(rows, [])["total"], 10)

    def test_no_evidence_no_pay(self):
        rows = [g("hola", "unknown", "emerging", evidence="")]
        self.assertEqual(compute_xp(rows, [])["total"], 0)

    def test_grammar_audited_against_paradigm(self):
        ok = [g("present_estar_person", "unknown", "emerging",
                section="grammar", evidence="yo estoy bien")]
        bad = [g("present_estar_person", "unknown", "emerging",
                 section="grammar", evidence="me te name es Sam")]
        self.assertEqual(compute_xp(ok, [])["total"], 10)
        self.assertEqual(compute_xp(bad, [])["total"], 0)


class TestMilestones(unittest.TestCase):
    def test_weights_and_dedupe(self):
        rows = [m("planted", "hola"),          # exposure: 0
                m("taking_root", "hola"),      # 25
                m("taking_root", "hola"),      # dup: 0
                m("rooted", "hola"),           # 40
                m("error_recovered", "yo_esta"),  # 30
                m("can_do_known", "IP-01"),    # 50
                m("can_do_emerging", "IP-02")]  # 0 by design
        self.assertEqual(compute_xp([], rows)["total"], 25 + 40 + 30 + 50)

    def test_retraction_subtracts_voided_payment(self):
        rows = [m("taking_root", "hola"),
                m("retracted", "hola", retracts="taking_root")]
        self.assertEqual(compute_xp([], rows)["total"], 0)

    def test_epoch_scopes_both_ledgers(self):
        grades = [g("hola", "unknown", "known"),
                  {"kind": "epoch", "ts": "t"},
                  g("bien", "unknown", "emerging")]
        prog = [m("rooted", "hola"), {"kind": "epoch", "key": "learner"},
                m("taking_root", "bien")]
        r = compute_xp(grades, prog)
        self.assertEqual(r["total"], 10 + 25)  # only post-epoch rows


class TestLevels(unittest.TestCase):
    def test_thresholds_shape(self):
        t = level_thresholds()
        self.assertEqual(t[:5], [0, 100, 250, 500, 900])
        self.assertTrue(all(b > a for a, b in zip(t, t[1:])))

    def test_level_and_to_next(self):
        r = compute_xp([g(w, "unknown", "known") for w in ("casa", "perro", "gato")], [])
        # 3 x 50 = 150 -> level 2 (>=100), 100 to next (250)
        self.assertEqual(r["total"], 150)
        self.assertEqual(r["level"], 2)
        self.assertEqual(r["to_next"], 100)

    def test_gated_name_requires_sheet_evidence(self):
        rows = [g(w, "unknown", "known") for w in ("casa", "perro", "gato")]  # level 2
        bare = compute_xp(rows, [], sheet={"skills": {}})
        self.assertEqual(bare["level_name"], "Nivel 2")
        gated = compute_xp(rows, [], sheet={
            "skills": {"IP-03": {"status": "emerging"}}})
        self.assertIn("Me llamo", gated["level_name"])


if __name__ == "__main__":
    unittest.main()


class TestSkillIdNormalization(unittest.TestCase):
    def test_underscore_ids_canonicalized(self):
        from tutor.character_sheet import apply_delta, default_sheet

        sheet = default_sheet()
        out = apply_delta(sheet, {
            "reason": "test grade normalization path",
            "skills": {"ip_03": {"status": "emerging"}},
        })
        self.assertIn("IP-03", out.get("skills") or {})
        self.assertNotIn("ip_03", out.get("skills") or {})
        self.assertNotIn("IP_03", out.get("skills") or {})


class TestTextFacts(unittest.TestCase):
    """learner_text_facts (ENGINEERING §1.1 fact-surface clause)."""

    def test_garble_gets_multi_cands_quiero_first(self):
        from tutor.text_facts import build_text_facts

        b = build_text_facts("yo kiero trabajar")
        [tok] = b["tokens"]
        self.assertEqual(tok["w"], "kiero")
        self.assertFalse(tok["es"])
        self.assertEqual(tok["cands"][0], "quiero")
        self.assertNotIn("nearest", tok)

    def test_verb_forms_multi_parse_and_accent(self):
        from tutor.text_facts import build_text_facts

        b = build_text_facts("esta bein")
        self.assertEqual(b["verb_forms"][0]["w"], "esta")
        self.assertEqual(b["verb_forms"][0]["matches"][0]["lemma"], "estar")
        self.assertEqual(b["tokens"][0]["cands"][0], "bien")

    def test_all_valid_returns_none_or_sparse(self):
        from tutor.text_facts import build_text_facts

        b = build_text_facts("muy bien gracias")
        # no invalid tokens, no verb forms -> omit entirely
        self.assertIsNone(b)

    def test_nearest_mode_is_arm_c_only_shape(self):
        from tutor.text_facts import build_text_facts

        b = build_text_facts("esta bein", mode="nearest")
        [tok] = b["tokens"]
        self.assertEqual(tok.get("nearest"), "bien")
        self.assertNotIn("cands", tok)

    def test_cap_holds(self):
        import json as J

        from tutor.text_facts import TOKEN_CAP, build_text_facts

        msg = " ".join(f"zzq{i}xw" for i in range(30))  # 30 garble tokens
        b = build_text_facts(msg)
        self.assertLessEqual(len(J.dumps(b, ensure_ascii=False)) // 4,
                             TOKEN_CAP)
