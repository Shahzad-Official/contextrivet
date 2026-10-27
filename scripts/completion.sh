#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [ "$#" -eq 1 ]; then
  case "$1" in
    zsh|bash) cat "$ROOT/completions/common.sh" "$ROOT/completions/$1.sh"; exit 0 ;;
    -h|--help|help) ;;
    *) printf 'ERROR: Supported shells are zsh and bash\n' >&2; exit 2 ;;
  esac
else
  [ "$#" -eq 0 ] || { echo 'ERROR: Choose one shell: zsh or bash' >&2; exit 2; }
fi
cat <<'EOF'
Usage: contextrivet completion <zsh|bash>

Enable completion in your current shell:
  eval "$(contextrivet completion zsh)"
  eval "$(contextrivet completion bash)"

For future sessions, add the matching line to ~/.zshrc or ~/.bashrc yourself.
This command prints shell code; it does not edit profiles or configure projects.
EOF
