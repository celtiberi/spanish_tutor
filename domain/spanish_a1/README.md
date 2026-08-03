# domain/spanish_a1 — the level's domain model (data, not code)

This directory IS the Spanish A1 domain model — the single source of truth
for what the teacher teaches and grades. Edits here change teacher behavior;
no code edit needed. Loaded + validated at startup by `tutor/domain_data.py`
(these four) and `tutor/association_table.py` / `tutor/teach_assets.py`
(the original three); malformed data fails loudly, never defaults.

- `can_dos.json` — can-do inventory (skills the sheet measures), theme→can-do
  journey routing, per-can-do phrase-chunk morphology, stretch-activity labels
- `grammar_forms.json` — supporting grammar forms: supports/priority/
  error_example merged with the teaching paradigm (label/lemma/pos/paradigm/
  note/watch) where one exists
- `domain_scope.json` — level definition + deferred / out-of-scope /
  recognition-only lists (rides in the sheet payload; stops scope drift)
- `misconceptions.json` — error-pattern catalog: label, form_id, can_dos,
  teach_hint, provenance `source` (deleted pack's M-ID), and detect/resolve
  regex lists (detect entries are `[pattern, note]` pairs; compiled at load)
- `association_table.json` — target vocabulary inventory (themes, anchors,
  false friends, imageable flags)
- `asset_sidecar.json` — teach-image metadata keyed by table keys
- `migration_deprecations.json` — retired-key escape hatch for sidecar validation

A new level slice = a new sibling directory with these files.
