
_contextrivet() {
  emulate -L zsh
  setopt local_options nonomatch
  local _CR_VALUES='' _CR_KIND='' _CR_PREFIX='' _CR_CURRENT='' candidate=''
  local -a before candidates matches
  before=()
  if (( CURRENT > 2 )); then before=("${(@)words[2,$((CURRENT - 1))]}"); fi
  _contextrivet_context "${words[CURRENT]}" "${before[@]}"
  candidates=("${(@s: :)_CR_VALUES}")
  matches=()
  for candidate in "${candidates[@]}"; do
    [[ -n "$candidate" && "$candidate" == "$_CR_CURRENT"* ]] && matches+=("$_CR_PREFIX$candidate")
  done
  (( ${#matches} )) && compadd -- "${matches[@]}"
  case "$_CR_KIND" in
    directories|files)
      [[ "$_CR_PREFIX" == --*= ]] && compset -P '*='
      if [[ "$_CR_KIND" == directories ]]; then _files -/; else _files; fi
      ;;
  esac
  return 0
}
if (( ! $+functions[compdef] )); then
  autoload -Uz compinit
  compinit
fi
compdef _contextrivet contextrivet
