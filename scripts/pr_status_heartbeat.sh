#!/usr/bin/env bash
# pr_status_heartbeat.sh — Outbound PR status heartbeat
#
# Wraps `prgenius status` for daily cron. Outputs human-readable summary
# and saves JSON snapshot to data/snapshots/.
#
# Usage:
#   bash scripts/pr_status_heartbeat.sh                    # default: zsxh1990
#   bash scripts/pr_status_heartbeat.sh --author zsxh1990  # explicit author
#   bash scripts/pr_status_heartbeat.sh --author Ikalus1988
#   bash scripts/pr_status_heartbeat.sh --all              # both accounts
#
# Exit codes:
#   0 = no action needed (all green)
#   1 = actionable items found (rebase/CI/ping)
#   2 = script error
#
# Cron example (daily 10:00 Asia/Shanghai):
#   0 10 * * * cd /path/to/pr-genius && bash scripts/pr_status_heartbeat.sh --all
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
# Use prgenius status's default snapshot dir so transition detection works
# across cron runs. Previously this script wrote to data/snapshots/ which
# prgenius never read, so the snapshot was dead data.
SNAPSHOT_DIR="${REPO_ROOT}/data/status-snapshots"
PRGENIUS_SRC="${REPO_ROOT}/prgenius/src"
mkdir -p "$SNAPSHOT_DIR"

# Use local source, not installed PyPI package
export PYTHONPATH="${PRGENIUS_SRC}:${PYTHONPATH:-}"

DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

AUTHORS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --author) AUTHORS+=("$2"); shift 2 ;;
        --all)    AUTHORS=("zsxh1990" "Ikalus1988"); shift ;;
        *)        echo "Unknown arg: $1"; exit 2 ;;
    esac
done
[[ ${#AUTHORS[@]} -eq 0 ]] && AUTHORS=("zsxh1990")

HAS_ACTION=0

for AUTHOR in "${AUTHORS[@]}"; do
    echo "═══════════════════════════════════════════════════"
    echo "  PR Genius Status — ${AUTHOR} (${DATE})"
    echo "═══════════════════════════════════════════════════"
    echo ""

    # Human-readable table output (display only — the JSON call below is the
    # one that records, so we do not write two snapshots per heartbeat).
    # --snapshot-dir is passed explicitly: prgenius defaults to a path relative
    # to the caller's cwd, which under cron is not this repo.
    python3 -m prgenius status --author "$AUTHOR" --format table \
        --no-save-snapshot --snapshot-dir "$SNAPSHOT_DIR" 2>&1 || {
        echo "ERROR: prgenius status failed for ${AUTHOR}" >&2
        continue
    }
    echo ""

    # JSON snapshot — prgenius records into SNAPSHOT_DIR
    # (YYYY-MM-DD-HHMM.json) and reports the file it wrote in
    # transition_summary.saved_to. We do not write a separate
    # heartbeat-side snapshot anymore — it was dead data prgenius never read.
    JSON_OUTPUT=$(python3 -m prgenius status --author "$AUTHOR" --format json \
        --snapshot-dir "$SNAPSHOT_DIR" 2>&1) || true

    if [[ -n "$JSON_OUTPUT" ]]; then
        # Check for actionable items + locate the snapshot prgenius just wrote
        read -r ACTION_COUNT SAVED_TO <<<"$(echo "$JSON_OUTPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    actionable = sum(1 for p in data.get('prs', [])
                     if p.get('status') in ('NEEDS_REBASE', 'CI_FAILING', 'STALE_REVIEW', 'STALE_NO_REVIEW'))
    saved = (data.get('transition_summary') or {}).get('saved_to') or '-'
    print(actionable, saved)
except Exception:
    print(0, '-')
" 2>/dev/null || echo "0 -")"

        if [[ "$ACTION_COUNT" -gt 0 ]]; then
            HAS_ACTION=1
            echo "⚡ ${ACTION_COUNT} actionable item(s) for ${AUTHOR}"
        fi

        if [[ "$SAVED_TO" != "-" && -f "${SNAPSHOT_DIR}/${SAVED_TO}" ]]; then
            echo "📸 Snapshot: ${SNAPSHOT_DIR}/${SAVED_TO}"
        else
            echo "📸 Snapshot: none written (state unchanged since the previous one)"
        fi
    fi
    echo ""
done

echo "───────────────────────────────────────────────────"
echo "  Heartbeat complete at ${TIMESTAMP}"
echo "───────────────────────────────────────────────────"

exit $HAS_ACTION
