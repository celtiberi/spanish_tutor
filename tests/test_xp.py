"""XP engine (docs/design-xp-progression.md): evidence-backed, monotone,
once-per-crossing, epoch-scoped; skills pay only via can_do_known."""

import unittest

from tutor.xp import compute_xp, level_thresholds


def g(item, frm, to, section="lexicon", ts="2026-08-05T10:00:00"):
    return {"kind": "grade", "field_id": item, "section": section,
            "from_status": frm, "to_status": to, "ts": ts}


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
        r = compute_xp([g(f"w{i}", "unknown", "known") for i in range(3)], [])
        # 3 x 50 = 150 -> level 2 (>=100), 100 to next (250)
        self.assertEqual(r["total"], 150)
        self.assertEqual(r["level"], 2)
        self.assertEqual(r["to_next"], 100)

    def test_gated_name_requires_sheet_evidence(self):
        rows = [g(f"w{i}", "unknown", "known") for i in range(3)]  # level 2
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
