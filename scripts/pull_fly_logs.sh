#!/bin/bash
# Pull ALL tester data from the Fly volume for local inspection
# (sessions incl. .requests.jsonl traffic, per-visitor sheets, grade
# ledgers, cost ledger). Usage: scripts/pull_fly_logs.sh [outdir]
set -euo pipefail
OUT="${1:-fly-data-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT"
echo "pulling /data from ml-teacher-tutor → $OUT/"
fly ssh console --app ml-teacher-tutor -q -C "tar czf - -C /data ." > "$OUT/data.tgz"
tar xzf "$OUT/data.tgz" -C "$OUT" && rm "$OUT/data.tgz"
echo "── sessions:"; ls "$OUT/sessions/" 2>/dev/null | tail -5
echo "── sheets:";  ls "$OUT/sheets/" 2>/dev/null | tail -5
echo "done → $OUT/ (traffic logs: $OUT/sessions/<date>/*.requests.jsonl)"
