
_contextrivet() {
  local _CR_VALUES='' _CR_KIND='' _CR_PREFIX='' _CR_CURRENT=''
  local current='' candidate='' strip='' word='' i=0 last=0
  local -a normalized
  normalized=() COMPREPLY=()
  [ "$COMP_CWORD" -ge 1 ] || return 0
  # Readline can split --option=value at '='. Reassemble only that separator.
  for ((i=1; i<=COMP_CWORD; i++)); do
    word="${COMP_WORDS[i]}"
    last=$((${#normalized[@]} - 1))
    if [ "$word" = = ] && [ "$last" -ge 0 ]; then
      normalized[last]="${normalized[last]}="
    elif [ "$last" -ge 0 ] && [[ "${normalized[last]}" == --*= ]]; then
      normalized[last]="${normalized[last]}$word"
    else
      normalized[${#normalized[@]}]="$word"
    fi
  done
  last=$((${#normalized[@]} - 1))
  current="${normalized[last]:-}"
  if [[ "$current" == --*=* ]] && [[ "${COMP_WORDS[COMP_CWORD]}" != --*=* ]]; then strip="${current%%=*}="; fi
  _contextrivet_context "$current" "${normalized[@]:0:last}"
  while IFS= read -r candidate; do
    candidate="$_CR_PREFIX$candidate"
    COMPREPLY[${#COMPREPLY[@]}]="${candidate#"$strip"}"
  done < <(compgen -W "$_CR_VALUES" -- "$_CR_CURRENT")
  case "$_CR_KIND" in
    directories|files)
      while IFS= read -r candidate; do
        [ "$_CR_KIND" != directories ] || candidate="$candidate/"
        candidate="$_CR_PREFIX$candidate"
        COMPREPLY[${#COMPREPLY[@]}]="${candidate#"$strip"}"
      done < <(if [ "$_CR_KIND" = directories ]; then compgen -d -- "$_CR_CURRENT"; else compgen -f -- "$_CR_CURRENT"; fi)
      ;;
  esac
  return 0
}
complete -o filenames -F _contextrivet contextrivet
