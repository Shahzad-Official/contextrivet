#!/usr/bin/env bash

START='# >>> contextrivet managed >>>'
END='# <<< contextrivet managed <<<'
LEGACY_START='# >>> dev-agent-config managed >>>'
LEGACY_END='# <<< dev-agent-config managed <<<'
CHANGES=0
BACKUP=''
MANIFEST=''
DRY=0
REGISTRY_SAVED=0

say() { printf '%s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

path_type() {
  if [ -L "$1" ]; then printf symlink
  elif [ -f "$1" ]; then printf file
  elif [ -d "$1" ]; then printf directory
  elif [ -e "$1" ]; then printf other
  else printf missing; fi
}

validate_target() {
  local target="$1" parent current rest part
  case "$target" in "$HOME"/*) ;; *) fail "Target is outside HOME: $target" ;; esac
  case "$target" in */../*|*/..|*/./*|*/.) fail "Unexpected traversal in target: $target" ;; esac
  parent="$(dirname "$target")"
  current="$HOME"
  rest="${parent#"$HOME"/}"
  [ "$parent" = "$HOME" ] && return
  while [ -n "$rest" ]; do
    part="${rest%%/*}"
    current="$current/$part"
    [ ! -L "$current" ] || fail "Refusing symlinked parent: $current"
    [ ! -e "$current" ] || [ -d "$current" ] || fail "Parent is not a directory: $current"
    [ "$rest" = "$part" ] && break
    rest="${rest#*/}"
  done
}

init_transaction() {
  DRY="$2"
  BACKUP="$HOME/.agents/contextrivet/backups/$(date +%Y%m%d-%H%M%S)-$$"
  MANIFEST="$BACKUP/manifest.tsv"
  validate_target "$MANIFEST"
  [ ! -e "$BACKUP" ] && [ ! -L "$BACKUP" ] || fail "Backup already exists: $BACKUP"
  say "Mode: $1"
  [ "$DRY" -eq 0 ] || say 'Dry run: no files will change'
}

backup_target() {
  local target="$1" type rel saved
  type="$(path_type "$target")"
  rel="${target#"$HOME"/}"
  saved="$BACKUP/original/$rel"
  mkdir -p "$(dirname "$saved")"
  if [ "$type" != missing ]; then cp -a "$target" "$saved"; fi
  printf '%s\t%s\t%s\n' "$type" "$target" "$saved" >> "$MANIFEST"
}

record_and_prepare() {
  local target="$1"
  validate_target "$target"
  [ "$DRY" -eq 0 ] || return
  mkdir -p "$BACKUP" "$(dirname "$target")"
  [ -f "$MANIFEST" ] || printf 'type\ttarget\tbackup\n' > "$MANIFEST"
  backup_target "$target"
}

strip_managed() {
  awk -v start="$START" -v end="$END" -v legacy_start="$LEGACY_START" -v legacy_end="$LEGACY_END" '
    $0 == start || $0 == legacy_start { inside=1; next }
    ($0 == end || $0 == legacy_end) && inside { inside=0; next }
    !inside { lines[++n]=$0 }
    END { while (n > 0 && lines[n] == "") n--; for (i=1; i<=n; i++) print lines[i] }
  ' "$1"
}

build_instruction_file() {
  local target="$1" mode="$2" output="$3"
  if [ "$mode" = merge ] && [ -f "$target" ]; then strip_managed "$target" > "$output"; fi
  if [ -s "$output" ]; then printf '\n' >> "$output"; fi
  printf '%s\n' "$START" >> "$output"
  cat "$ROOT/AGENTS.md" >> "$output"
  printf '%s\n' "$END" >> "$output"
}

stat_mode() {
  if stat -f '%Lp' "$1" >/dev/null 2>&1; then stat -f '%Lp' "$1"; else stat -c '%a' "$1"; fi
}

check_instruction_target() {
  local target="$1" type
  validate_target "$target"
  type="$(path_type "$target")"
  [ "$type" != symlink ] || fail "Refusing instruction symlink: $target"
  [ "$type" = missing ] || [ "$type" = file ] || fail "Unsupported instruction target: $target ($type)"
}

check_skill_target() {
  local target="$1" type
  validate_target "$target"
  type="$(path_type "$target")"
  [ "$type" != other ] || fail "Unsupported skill target: $target ($type)"
}

check_state_target() {
  local target="$HOME/.agents/contextrivet/last-backup" type
  validate_target "$target"
  type="$(path_type "$target")"
  [ "$type" != symlink ] || fail "Refusing symlinked state file: $target"
  [ "$type" = missing ] || [ "$type" = file ] || fail "Unsupported state target: $target ($type)"
}

check_link_registry() {
  command -v python3 >/dev/null 2>&1 || fail 'Shared link ownership requires Python 3'
  python3 "$ROOT/scripts/managed_links.py" validate || fail 'Unsafe link ownership registry'
}

record_link() {
  [ "$REGISTRY_SAVED" -eq 1 ] || record_and_prepare "$HOME/.agents/contextrivet/links.json"
  REGISTRY_SAVED=1
  python3 "$ROOT/scripts/managed_links.py" record "$1" "$2"
}

adopt_link() {
  if ! python3 "$ROOT/scripts/managed_links.py" tracked "$1" && python3 "$ROOT/scripts/managed_links.py" owned "$1"; then
    say "$( [ "$DRY" -eq 1 ] && printf WOULD_RECORD || printf RECORDED ) legacy link ownership: $1"
    if [ "$DRY" -eq 0 ]; then record_link "$1" "$2"; fi
    CHANGES=$((CHANGES + 1))
  fi
}

install_instructions() {
  local target="$1" mode="$2" type tmp write_tmp
  check_instruction_target "$target"
  type="$(path_type "$target")"
  tmp="$(mktemp)"
  build_instruction_file "$target" "$mode" "$tmp"
  if [ "$type" = file ] && cmp -s "$target" "$tmp"; then
    say "UNCHANGED instructions: $target"
    rm -f "$tmp"
    return
  fi
  say "$( [ "$DRY" -eq 1 ] && printf WOULD_UPDATE || printf UPDATED ) instructions: $target"
  if [ "$DRY" -eq 0 ]; then
    record_and_prepare "$target"
    write_tmp="$(mktemp "$(dirname "$target")/.contextrivet.XXXXXX")"
    cat "$tmp" > "$write_tmp"
    if [ "$type" = file ]; then chmod "$(stat_mode "$target")" "$write_tmp"; else chmod 644 "$write_tmp"; fi
    mv "$write_tmp" "$target"
  fi
  rm -f "$tmp"
  CHANGES=$((CHANGES + 1))
}

install_skill() {
  local destination="$1" origin="$2" mode="$3" type
  check_skill_target "$destination"
  type="$(path_type "$destination")"
  if [ "$type" = symlink ] && [ "$(readlink "$destination")" = "$origin" ]; then
    adopt_link "$destination" "$origin"
    say "UNCHANGED skill: $destination"
    return
  fi
  if [ "$type" != missing ] && [ "$mode" = merge ] && ! python3 "$ROOT/scripts/managed_links.py" owned "$destination"; then
    say "PRESERVED existing skill: $destination"
    return
  fi
  say "$( [ "$DRY" -eq 1 ] && printf WOULD_LINK || printf LINKED ) skill: $destination"
  if [ "$DRY" -eq 0 ]; then
    record_and_prepare "$destination"
    if [ "$type" != missing ]; then rm -rf "$destination"; fi
    ln -s "$origin" "$destination"
    record_link "$destination" "$origin"
  fi
  CHANGES=$((CHANGES + 1))
}

install_instruction_link() {
  local destination="$1" origin="$2" mode="$3" label="${4:-code-intelligence instructions}" type
  check_skill_target "$destination"
  type="$(path_type "$destination")"
  if [ "$type" = symlink ] && [ "$(readlink "$destination")" = "$origin" ]; then
    adopt_link "$destination" "$origin"
    say "UNCHANGED $label: $destination"
    return
  fi
  if [ "$type" != missing ] && [ "$mode" = merge ] && ! python3 "$ROOT/scripts/managed_links.py" owned "$destination"; then
    say "PRESERVED existing instruction link path: $destination"
    return
  fi
  say "$( [ "$DRY" -eq 1 ] && printf WOULD_LINK || printf LINKED ) $label: $destination"
  if [ "$DRY" -eq 0 ]; then
    record_and_prepare "$destination"
    if [ "$type" != missing ]; then rm -rf "$destination"; fi
    ln -s "$origin" "$destination"
    record_link "$destination" "$origin"
  fi
  CHANGES=$((CHANGES + 1))
}

finish_transaction() {
  local state="$HOME/.agents/contextrivet/last-backup"
  say "Changes: $CHANGES"
  if [ "$DRY" -eq 0 ] && [ "$CHANGES" -gt 0 ]; then
    printf '%s\n' "$BACKUP" > "$state"
    say "Backup: $BACKUP"
    say "Rollback: $ROOT/scripts/rollback.sh '$BACKUP'"
  fi
  say 'Installed skills are discoverable; activation must be verified in an agent session.'
}
