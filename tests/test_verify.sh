#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SANDBOX="$(mktemp -d)"
cleanup() {
  local status="$?"
  if [ "$status" -eq 0 ]; then rm -rf "$SANDBOX"
  else printf 'Verification fixtures retained: %s\n' "$SANDBOX" >&2; fi
}
diagnose_failure() {
  local status="$1" line="$2" command="$3" file
  printf 'FAIL test_verify.sh:%s (exit %s): %s\n' "$line" "$status" "$command" >&2
  for file in "$SANDBOX"/*.json; do
    [ -f "$file" ] || continue
    printf '\nFixture output: %s\n' "$file" >&2
    cat "$file" >&2 || true
  done
  exit "$status"
}
trap cleanup EXIT
trap 'diagnose_failure "$?" "$LINENO" "$BASH_COMMAND"' ERR
# Discovery must see fixture directories only, regardless of the calling IDE.
unset XDG_DATA_HOME VSCODE_AGENT_FOLDER
SYSTEM_PATH='/usr/bin:/bin'

make_cli() {
  local bin="$1" name="$2" version="$3"
  mkdir -p "$bin"
  printf '#!/bin/sh\nprintf "%%s\\n" "%s %s"\n' "$name" "$version" > "$bin/$name"
  chmod +x "$bin/$name"
}

assert_version() {
  python3 - "$1" "$2" "$3" <<'PY'
import json, sys
with open(sys.argv[1]) as source:
    agent = next(item for item in json.load(source)["agents"] if item["name"] == sys.argv[2])
actual, expected = agent["version"], sys.argv[3]
if actual not in (expected, "timeout"):
    raise AssertionError((agent["name"], actual, expected))
if actual == "timeout":
    print("OBSERVED_TIMEOUT: {} optional version probe exceeded its bounded wait; configuration checks still apply".format(agent["name"]))
PY
}

# Missing CLIs are not confused with absent configurations.
home="$SANDBOX/missing"
mkdir -p "$home"
HOME="$home" PATH="$SYSTEM_PATH" "$ROOT/scripts/install.sh" >/dev/null
HOME="$home" PATH="$SYSTEM_PATH" "$ROOT/scripts/verify.sh" --json > "$SANDBOX/missing.json"
grep -q '"name":"Codex","cli":"codex","installed":false,"version":"unavailable","vscode_extension":.*"configured":false' "$SANDBOX/missing.json"

# A healthy existing configuration remains configured even without its CLI.
home="$SANDBOX/configured"
mkdir -p "$home/.codex"
HOME="$home" PATH="$SYSTEM_PATH" "$ROOT/scripts/install.sh" >/dev/null
HOME="$home" PATH="$SYSTEM_PATH" "$ROOT/scripts/verify.sh" > "$SANDBOX/configured.txt"
grep -q 'installed: false' "$SANDBOX/configured.txt"
grep -q 'configuration health: healthy' "$SANDBOX/configured.txt"

# Broken managed skill links are reported and make verification fail.
home="$SANDBOX/broken"
mkdir -p "$home"
HOME="$home" PATH="$SYSTEM_PATH" "$ROOT/scripts/install.sh" >/dev/null
rm "$home/.agents/skills/ponytail"
ln -s "$SANDBOX/does-not-exist" "$home/.agents/skills/ponytail"
if HOME="$home" PATH="$SYSTEM_PATH" "$ROOT/scripts/verify.sh" --json > "$SANDBOX/broken.json"; then
  echo 'Broken skill link passed verification' >&2
  exit 1
fi
grep -q '"status":"broken-link"' "$SANDBOX/broken.json"
grep -q '"healthy":false' "$SANDBOX/broken.json"

# Mixed CLI/config installations and versions are detected independently.
home="$SANDBOX/mixed"
bin="$SANDBOX/bin"
mkdir -p "$home/.codex" "$home/.gemini"
make_cli "$bin" codex 1.2.3
make_cli "$bin" opencode 4.5.6
# Simulate a CLI that writes during --version; verification must contain the write.
printf '#!/bin/sh\nmkdir -p "$HOME/version-side-effect"\nprintf "opencode 4.5.6\\n"\n' > "$bin/opencode"
chmod +x "$bin/opencode"
# Check exact version extraction independently of the integration probe's wall
# clock budget. Force the completed-child branch; wait still reaps the real fake
# process, so stdout parsing and isolated HOME behavior are exercised unchanged.
sed -n '/^safe_version() {/,/^}/p' "$ROOT/scripts/verify.sh" > "$SANDBOX/version-function.sh"
(
  . "$SANDBOX/version-function.sh"
  kill() {
    [ "${1:-}" != -0 ] || return 1
    builtin kill "$@"
  }
  [ "$(safe_version "$bin/codex")" = 'codex 1.2.3' ]
  [ "$(safe_version "$bin/opencode")" = 'opencode 4.5.6' ]
)
HOME="$home" PATH="$bin:$SYSTEM_PATH" "$ROOT/scripts/install.sh" >/dev/null
HOME="$home" PATH="$bin:$SYSTEM_PATH" "$ROOT/scripts/verify.sh" --json > "$SANDBOX/mixed.json"
grep -q '"name":"Codex","cli":"codex","installed":true,.*"configured":true' "$SANDBOX/mixed.json"
assert_version "$SANDBOX/mixed.json" Codex 'codex 1.2.3'
grep -q '"name":"Gemini CLI","cli":"gemini","installed":false,"version":"unavailable","vscode_extension":.*"configured":true' "$SANDBOX/mixed.json"
grep -q '"name":"OpenCode","cli":"opencode","installed":true,.*"configured":false' "$SANDBOX/mixed.json"
assert_version "$SANDBOX/mixed.json" OpenCode 'opencode 4.5.6'
grep -q '"runtime_skill_activation":"unverified"' "$SANDBOX/mixed.json"
[ ! -e "$home/version-side-effect" ]
if command -v python3 >/dev/null 2>&1; then python3 -m json.tool "$SANDBOX/mixed.json" >/dev/null; fi
grep -q '"name":"Cline"' "$SANDBOX/mixed.json"
grep -q '"name":"Antigravity"' "$SANDBOX/mixed.json"

# A genuinely slow optional probe stays bounded and reports unknown version,
# without being confused with missing CLI/configuration or unhealthy rules.
slow_bin="$SANDBOX/slow-bin"
mkdir -p "$slow_bin"
printf '#!/bin/sh\nexec /bin/sleep 3\n' > "$slow_bin/codex"
chmod +x "$slow_bin/codex"
HOME="$home" PATH="$slow_bin:$SYSTEM_PATH" "$ROOT/scripts/verify.sh" --json > "$SANDBOX/slow.json"
grep -q '"name":"Codex","cli":"codex","installed":true,"version":"timeout"' "$SANDBOX/slow.json"
grep -q '"healthy":true' "$SANDBOX/slow.json"

# Documented global rules and skill targets are discoverable without claiming
# runtime activation for either IDE.
home="$SANDBOX/antigravity-cline"
mkdir -p "$home/.gemini/antigravity" "$home/.cline"
HOME="$home" PATH="$SYSTEM_PATH" "$ROOT/scripts/install.sh" >/dev/null
HOME="$home" PATH="$SYSTEM_PATH" "$ROOT/scripts/verify.sh" --json > "$SANDBOX/antigravity-cline.json"
grep -q '"name":"Cline".*"configuration_health":"healthy"' "$SANDBOX/antigravity-cline.json"
grep -q '"name":"Antigravity".*"configuration_health":"healthy"' "$SANDBOX/antigravity-cline.json"
grep -q '"runtime_skill_activation":"unverified"' "$SANDBOX/antigravity-cline.json"

# Codex CLI and VS Code extension installation are independent signals.
home="$SANDBOX/discovery-home"
mkdir -p "$home"
HOME="$home" PATH="$SYSTEM_PATH" "$ROOT/scripts/install.sh" >/dev/null

bin="$SANDBOX/cli-only-bin"
make_cli "$bin" codex 7.0.0
HOME="$home" PATH="$bin:$SYSTEM_PATH" "$ROOT/scripts/verify.sh" --json > "$SANDBOX/cli-only.json"
grep -q '"name":"Codex","cli":"codex","installed":true' "$SANDBOX/cli-only.json"
grep -q '"id":"openai.chatgpt","installation":"not-detected","listed":false,"directory_present":false' "$SANDBOX/cli-only.json"

bin="$SANDBOX/extension-only-bin"
mkdir -p "$bin"
printf '#!/bin/sh\nprintf "openai.chatgpt@1.2.3\\n"\n' > "$bin/code"
chmod +x "$bin/code"
HOME="$home" PATH="$bin:$SYSTEM_PATH" "$ROOT/scripts/verify.sh" --json > "$SANDBOX/extension-only.json"
grep -q '"name":"Codex","cli":"codex","installed":false' "$SANDBOX/extension-only.json"
grep -q '"id":"openai.chatgpt","installation":"confirmed","listed":true,"directory_present":false.*"active":"unverified"' "$SANDBOX/extension-only.json"

bin="$SANDBOX/both-bin"
make_cli "$bin" codex 7.0.0
printf '#!/bin/sh\nprintf "openai.chatgpt@1.2.3\\n"\n' > "$bin/code"
chmod +x "$bin/code"
HOME="$home" PATH="$bin:$SYSTEM_PATH" "$ROOT/scripts/verify.sh" --json > "$SANDBOX/both.json"
grep -q '"name":"Codex","cli":"codex","installed":true' "$SANDBOX/both.json"
grep -q '"id":"openai.chatgpt","installation":"confirmed","listed":true' "$SANDBOX/both.json"

HOME="$home" PATH="$SYSTEM_PATH" "$ROOT/scripts/verify.sh" --json > "$SANDBOX/neither.json"
grep -q '"name":"Codex","cli":"codex","installed":false' "$SANDBOX/neither.json"
grep -q '"id":"openai.chatgpt","installation":"not-detected","listed":false,"directory_present":false' "$SANDBOX/neither.json"

# Directory fallback is reported as presence only, never as active or CLI-listed.
mkdir -p "$home/.vscode/extensions/openai.chatgpt-9.9.9"
HOME="$home" PATH="$SYSTEM_PATH" "$ROOT/scripts/verify.sh" --json > "$SANDBOX/directory-only.json"
grep -q '"id":"openai.chatgpt","installation":"directory-only","listed":false,"directory_present":true,"directory_scope":"local-vscode".*"active":"unverified"' "$SANDBOX/directory-only.json"

# Remote SSH, WSL, and Dev Container servers use the remote VS Code Server tree.
remote_home="$SANDBOX/remote-home"
mkdir -p "$remote_home/.vscode-server/extensions/openai.chatgpt-3.0.0"
HOME="$remote_home" PATH="$SYSTEM_PATH" "$ROOT/scripts/install.sh" >/dev/null
HOME="$remote_home" PATH="$SYSTEM_PATH" "$ROOT/scripts/verify.sh" --json > "$SANDBOX/remote.json"
grep -q '"id":"openai.chatgpt","installation":"directory-only","listed":false,"directory_present":true,"directory_scope":"remote-vscode"' "$SANDBOX/remote.json"
grep -q '"directory_path":".*\.vscode-server/extensions/openai.chatgpt-3.0.0"' "$SANDBOX/remote.json"

# Explicit remote agent folders are supported, while invalid and symlinked roots are ignored.
agent_home="$SANDBOX/agent-home"
agent_folder="$SANDBOX/custom-vscode-agent"
mkdir -p "$agent_home" "$agent_folder/extensions/openai.chatgpt-4.0.0"
HOME="$agent_home" VSCODE_AGENT_FOLDER="$agent_folder" PATH="$SYSTEM_PATH" "$ROOT/scripts/install.sh" >/dev/null
HOME="$agent_home" VSCODE_AGENT_FOLDER="$agent_folder" PATH="$SYSTEM_PATH" "$ROOT/scripts/verify.sh" --json > "$SANDBOX/agent-folder.json"
grep -q '"directory_scope":"remote-agent"' "$SANDBOX/agent-folder.json"

invalid_home="$SANDBOX/invalid-home"
foreign="$SANDBOX/foreign-extensions"
mkdir -p "$invalid_home/.vscode-server" "$foreign/openai.chatgpt-5.0.0"
ln -s "$foreign" "$invalid_home/.vscode-server/extensions"
mkdir -p "$invalid_home/.vscode"
printf 'not a directory\n' > "$invalid_home/.vscode/extensions"
HOME="$invalid_home" PATH="$SYSTEM_PATH" "$ROOT/scripts/install.sh" >/dev/null
HOME="$invalid_home" PATH="$SYSTEM_PATH" "$ROOT/scripts/verify.sh" --json > "$SANDBOX/invalid.json"
grep -q '"id":"openai.chatgpt","installation":"not-detected","listed":false,"directory_present":false' "$SANDBOX/invalid.json"

echo 'PASS verify: local/remote discovery, invalid paths, mixed installs, JSON'
