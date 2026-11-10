#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
. "$ROOT/scripts/lib/config.sh"

DRY=0
BACKUP=''
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    *) [ -z "$BACKUP" ] || fail "Usage: $0 [--dry-run] [BACKUP_DIR]"; BACKUP="$arg" ;;
  esac
done
if [ -z "$BACKUP" ]; then
  state="$HOME/.agents/contextrivet/last-backup"
  if [ ! -e "$state" ] && [ ! -L "$state" ]; then state="$HOME/.agents/dev-agent-config/last-backup"; fi
  validate_target "$state"
  [ -f "$state" ] && [ ! -L "$state" ] || fail 'No safe last-backup record found'
  BACKUP="$(sed -n '1p' "$state")"
fi
case "$BACKUP" in "$HOME/.agents/contextrivet/backups/"*|"$HOME/.agents/dev-agent-config/backups/"*) ;; *) fail "Invalid backup path: $BACKUP" ;; esac
validate_target "$BACKUP/manifest.tsv"
[ -f "$BACKUP/manifest.tsv" ] && [ ! -L "$BACKUP/manifest.tsv" ] || fail "Missing/unsafe backup manifest: $BACKUP"
[ "$(head -n 1 "$BACKUP/manifest.tsv")" = "$(printf 'type\ttarget\tbackup')" ] || fail 'Invalid backup manifest header'

SAFETY="$HOME/.agents/contextrivet/backups/rollback-$(date +%Y%m%d-%H%M%S)-$$"
validate_target "$SAFETY/manifest.tsv"
[ ! -e "$SAFETY" ] && [ ! -L "$SAFETY" ] || fail "Recovery backup already exists: $SAFETY"
ORIGINAL_BACKUP="$BACKUP"

# Validate the complete plan and saved objects before changing any target.
seen=$'\n'
while IFS="$(printf '\t')" read -r type target saved; do
  validate_target "$target"
  case "$target" in
    "$HOME/AGENTS.md"|"$HOME/.agents/AGENTS.md"|"$HOME/.codex/AGENTS.md"|"$HOME/.claude/CLAUDE.md"|"$HOME/.gemini/GEMINI.md"|"$HOME/.config/opencode/AGENTS.md"|"$HOME/.agents/instructions/code-intelligence.md"|"$HOME/.agents/contextrivet/links.json"|"$HOME/.agents/skills/ponytail"|"$HOME/.claude/skills/ponytail"|"$HOME/.gemini/skills/ponytail"|"$HOME/.gemini/config/skills/ponytail"|"$HOME/.config/opencode/skills/ponytail"|"$HOME/.cline/data/settings/skills/ponytail") ;;
    *) fail "Unexpected rollback target: $target" ;;
  esac
  case "$seen" in *$'\n'"$target"$'\n'*) fail "Duplicate rollback target: $target" ;; esac
  seen="$seen$target"$'\n'
  case "$type" in missing|file|directory|symlink) ;; *) fail "Invalid rollback type: $type" ;; esac
  [ "$saved" = "$BACKUP/original/${target#"$HOME"/}" ] || fail "Unexpected saved path: $saved"
  validate_target "$saved"
  [ "$(path_type "$saved")" = "$type" ] || fail "Missing or changed backup object: $saved"
  if [ "$target" = "$HOME/.agents/contextrivet/links.json" ] && [ "$type" != missing ]; then
    [ "$type" = file ] || fail 'Invalid saved link ownership metadata type'
    python3 "$ROOT/scripts/managed_links.py" validate "$saved" || fail 'Invalid saved link ownership metadata'
  fi
  [ "$(path_type "$target")" != other ] || fail "Unexpected current path type: $target"
done < <(tail -n +2 "$BACKUP/manifest.tsv")
[ "$seen" != $'\n' ] || fail 'Backup manifest has no targets'

if [ "$DRY" -eq 1 ]; then
  while IFS="$(printf '\t')" read -r type target saved; do say "WOULD_RESTORE $target ($type)"; done < <(tail -n +2 "$BACKUP/manifest.tsv")
  exit 0
fi

# Snapshot every current object, including missing ones, before the first restore.
BACKUP="$SAFETY"
MANIFEST="$SAFETY/manifest.tsv"
while IFS="$(printf '\t')" read -r type target saved; do
  record_and_prepare "$target"
done < <(tail -n +2 "$ORIGINAL_BACKUP/manifest.tsv")
BACKUP="$ORIGINAL_BACKUP"

restore_record() {
  local type="$1" target="$2" saved="$3"
  validate_target "$target"
  if [ "$(path_type "$target")" != missing ]; then rm -rf "$target" || return 1; fi
  if [ "$type" != missing ]; then
    mkdir -p "$(dirname "$target")" || return 1
    cp -a "$saved" "$target" || return 1
  fi
}

recover_failure() {
  local failed=0
  trap - ERR
  while IFS="$(printf '\t')" read -r type target saved; do
    restore_record "$type" "$target" "$saved" || failed=1
  done < <(tail -n +2 "$SAFETY/manifest.tsv")
  if [ "$failed" -eq 0 ]; then say 'ERROR: Rollback failed; pre-rollback configuration and ownership restored.' >&2
  else say "ERROR: Rollback and recovery failed; recover manually from $SAFETY" >&2; fi
  exit 1
}
trap recover_failure ERR
while IFS="$(printf '\t')" read -r type target saved; do
  restore_record "$type" "$target" "$saved"
  say "RESTORED $target ($type)"
done < <(tail -n +2 "$BACKUP/manifest.tsv")
say "Rollback complete: $BACKUP"
if [ -d "$SAFETY" ]; then say "Pre-rollback recovery backup: $SAFETY"; fi
