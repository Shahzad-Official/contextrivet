#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
. "$ROOT/scripts/lib/config.sh"
DRY=1
mode=''
for arg in "$@"; do
  case "$arg" in
    --help|-h)
      printf '%s\n' 'Usage: contextrivet repair [--dry-run|--apply]' 'Preview is the default. Repairs only owned shared links; custom paths are preserved.' 'Changes have recovery backups; contextrivet rollback restores the last transaction.' 'Use project repair for missing project scaffold assets. No project prose is rewritten.'
      exit 0 ;;
    --apply|--dry-run)
      [ -z "$mode" ] || [ "$mode" = "$arg" ] || fail 'Choose --dry-run or --apply, not both'
      mode="$arg"
      if [ "$arg" = --apply ]; then DRY=0; else DRY=1; fi ;;
    *) fail 'Usage: contextrivet repair [--dry-run|--apply]' ;;
  esac
done
command -v python3 >/dev/null || fail 'Repair requires Python 3'
check_state_target
check_link_registry
plan="$(mktemp)"
trap 'rm -f "$plan"' EXIT
# Complete ownership, parent, and source validation before the first write.
python3 "$ROOT/scripts/managed_links.py" plan > "$plan"
while IFS="$(printf '\t')" read -r target origin; do
  [ -z "$target" ] || check_skill_target "$target"
done < "$plan"
init_transaction repair "$DRY"
recover_failure() {
  if [ -f "$MANIFEST" ]; then bash "$ROOT/scripts/rollback.sh" "$BACKUP" >&2 || say 'Automatic rollback failed; retain the backup for manual recovery.' >&2; fi
  say 'ERROR: Repair failed; no success is reported.' >&2
  exit 1
}
trap recover_failure ERR
while IFS="$(printf '\t')" read -r target origin; do
  [ -z "$target" ] || install_instruction_link "$target" "$origin" replace 'managed asset'
done < "$plan"
finish_transaction
[ "$DRY" -eq 0 ] || say 'Dry run only. Pass --apply to repair the displayed owned links.'
