#!/usr/bin/env bash

# Keep help readable in logs and pipes; color is presentation only.
help_palette() {
  HELP_RESET='' HELP_BOLD='' HELP_CYAN='' HELP_PURPLE='' HELP_GREEN='' HELP_DIM=''
  local enabled=0
  if [ -z "${NO_COLOR+x}" ] && [ "${FORCE_COLOR:-}" != 0 ]; then
    case "${FORCE_COLOR:-}" in
      1|2|3) enabled=1 ;;
      *) if [ -t 1 ] && [ "${TERM:-}" != dumb ]; then enabled=1; fi ;;
    esac
  fi
  if [ "$enabled" -eq 1 ]; then
    HELP_RESET=$'\033[0m' HELP_BOLD=$'\033[1m' HELP_CYAN=$'\033[96m'
    HELP_PURPLE=$'\033[95m' HELP_GREEN=$'\033[92m' HELP_DIM=$'\033[2m'
  fi
  HELP_WIDTH="${COLUMNS:-80}"
  case "$HELP_WIDTH" in ''|*[!0-9]*) HELP_WIDTH=80 ;; esac
}

help_section() {
  printf '\n  %s%s%s\n' "$HELP_BOLD$HELP_PURPLE" "$1" "$HELP_RESET"
}

help_row() {
  if [ "$HELP_WIDTH" -ge 80 ]; then
    printf '    %s%-38s%s %s\n' "$HELP_CYAN" "$1" "$HELP_RESET" "$2"
  else
    printf '    %s%s%s\n      %s\n' "$HELP_CYAN" "$1" "$HELP_RESET" "$2"
  fi
}
