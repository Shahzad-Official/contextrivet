#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT
home="$SANDBOX/home"
mkdir -p "$home"

"$ROOT/contextrivet" --help > "$SANDBOX/help"
"$ROOT/contextrivet" -h >/dev/null
grep -q 'graphify <action>' "$SANDBOX/help"
grep -q 'cli install|uninstall' "$SANDBOX/help"
grep -q 'codebase-memory-mcp <command>' "$SANDBOX/help"
"$ROOT/contextrivet" graphify --help > "$SANDBOX/graphify-help"
grep -q 'serve \[--project PATH\]' "$SANDBOX/graphify-help"
grep -q 'run \[--project PATH\]' "$SANDBOX/graphify-help"
"$ROOT/contextrivet" tools codebase-memory-mcp --help > "$SANDBOX/cbm-help"
grep -q 'adopt \[--dry-run\]' "$SANDBOX/cbm-help"
grep -q 'run \[--dry-run\]' "$SANDBOX/cbm-help"
"$ROOT/contextrivet" cbm --help > "$SANDBOX/cbm-run-help"
grep -q 'Bootstrap CBM for the current Git repository' "$SANDBOX/cbm-run-help"

HOME="$home" PATH=/usr/bin:/bin "$ROOT/contextrivet" cli install --dry-run --bin-dir "$home/bin" > "$SANDBOX/dry"
[ ! -e "$home/bin/contextrivet" ]
HOME="$home" PATH=/usr/bin:/bin "$ROOT/contextrivet" cli install --bin-dir "$home/bin" >/dev/null
[ -L "$home/bin/contextrivet" ]
[ "$(readlink "$home/bin/contextrivet")" = "$ROOT/contextrivet" ]
HOME="$home" PATH=/usr/bin:/bin "$home/bin/contextrivet" --help >/dev/null
HOME="$home" PATH=/usr/bin:/bin "$home/bin/contextrivet" cli install --bin-dir "$home/bin" | grep 'UNCHANGED CLI link' >/dev/null

printf 'keep\n' > "$home/bin/unrelated"
HOME="$home" PATH=/usr/bin:/bin "$home/bin/contextrivet" cli uninstall --bin-dir "$home/bin" >/dev/null
[ ! -e "$home/bin/contextrivet" ]
[ -f "$home/bin/unrelated" ]

printf 'foreign\n' > "$home/bin/contextrivet"
if HOME="$home" PATH=/usr/bin:/bin "$ROOT/contextrivet" cli uninstall --bin-dir "$home/bin" > "$SANDBOX/conflict" 2>&1; then
  echo 'CLI uninstall removed an unowned path' >&2
  exit 1
fi
grep -qFx foreign "$home/bin/contextrivet"

echo 'PASS CLI: help, user-local link, idempotence, safe removal'
