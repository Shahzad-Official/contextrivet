# Shared context rules for Contextrivet completion. No project code is run.
_contextrivet_context() {
  local current="$1" word='' waiting='' command='' action='' sub='' detail='' target=''
  local project="$PWD" key='' prefix='' agent='' values='' directory='' entry='' identifier='' shortcut=0 count=0
  shift
  count=$#
  _CR_VALUES='' _CR_KIND='' _CR_PREFIX='' _CR_CURRENT="$current"
  for word in "$@"; do
    if [ -n "$waiting" ]; then
      [ "$waiting" != --project ] || project="$word"
      waiting=''
      continue
    fi
    case "$word" in
      --project=*) project="${word#*=}" ;;
      --project|--stack|--agents|--agent|--skills|--names|--note|--canonical|--backup|--output|--bin-dir|--port|--budget) waiting="$word" ;;
      -*) ;;
      *)
        if [ -z "$command" ]; then command="$word"
        elif [ -z "$action" ]; then action="$word"
        elif [ -z "$sub" ]; then sub="$word"
        elif [ -z "$detail" ]; then detail="$word"
        elif [ -z "$target" ]; then target="$word"; fi
        ;;
    esac
  done
  if [ "$command" = tools ]; then
    if [ -z "$action" ]; then _CR_VALUES='graphify codebase-memory-mcp --help -h'; return; fi
    command="$action"; action="$sub"; sub="$detail"; detail="$target"
  elif [ "$command" = cbm ]; then
    command=codebase-memory-mcp
    if [ -z "$action" ]; then action=run; shortcut=1
    elif [ "$action" != run ]; then return; fi
  fi
  key="$waiting"
  case "$current" in --*=*) key="${current%%=*}"; prefix="$key="; current="${current#*=}" ;; esac
  _CR_CURRENT="$current" _CR_PREFIX="$prefix"
  case "$key" in
    --stack) _CR_VALUES='none nestjs nextjs flutter'; [ "$action" != init ] || _CR_VALUES="$_CR_VALUES auto"; return ;;
    --skills) _CR_VALUES='none ponytail'; return ;;
    --canonical) _CR_VALUES='AGENTS.md CLAUDE.md GEMINI.md .agents/AGENTS.md'; return ;;
    --agent) _CR_VALUES='codex opencode antigravity'; return ;;
    --agents)
      case "$current" in *,*) prefix="$prefix${current%,*},"; current="${current##*,}" ;; esac
      for agent in codex claude gemini opencode cline antigravity none; do
        case ",${prefix#--agents=}" in *",$agent,"*) continue ;; esac
        [ "$agent" != none ] || [ -z "${prefix#--agents=}" ] || continue
        values="$values $agent"
      done
      _CR_VALUES="$values" _CR_PREFIX="$prefix" _CR_CURRENT="$current"
      return
      ;;
    --mode) _CR_VALUES='merge replace'; return ;;
    --project|--output|--bin-dir) _CR_KIND=directories; return ;;
    --note) _CR_KIND=files; return ;;
    --backup)
      for directory in "$project/.agents/contextrivet/backups" "$project/.agents/dev-agent-config/backups"; do
        [ -d "$directory" ] && [ ! -L "$directory" ] || continue
        for entry in "$directory"/*; do
          [ -d "$entry" ] && [ ! -L "$entry" ] || continue
          identifier="${entry##*/}"
          [[ "$identifier" =~ ^[0-9]{8}-[0-9]{6}(-[0-9]{6})?-[0-9]+$ ]] || continue
          _CR_VALUES="$_CR_VALUES $identifier"
        done
      done
      return
      ;;
    --names|--port|--budget) return ;;
  esac
  case "$command:$action:$sub" in
    ::) _CR_VALUES='project install verify health repair rollback uninstall benchmark tools cbm graphify cli completion help' ;;
    project::) _CR_VALUES='init status skills backups restore uninstall repair baseline automate' ;;
    project:init:*) _CR_VALUES='--project --canonical --agents --stack --skills --dry-run --yes' ;;
    project:status:*|project:backups:*) _CR_VALUES='--project' ;;
    project:repair:*) _CR_VALUES='--project --apply --dry-run' ;;
    project:baseline:*) _CR_VALUES='--project --note --yes --dry-run' ;;
    project:automate:*) _CR_VALUES='--project --hook --ci --local --apply --dry-run' ;;
    project:skills:) _CR_VALUES='install --stack' ;;
    project:skills:install) _CR_VALUES='--project --stack --names --all --dry-run --yes' ;;
    project:restore:*) _CR_VALUES='--project --backup --dry-run --yes --force' ;;
    project:uninstall:*) _CR_VALUES='--project --dry-run --yes --force' ;;
    cli::) _CR_VALUES='install uninstall' ;;
    cli:install:*|cli:uninstall:*) _CR_VALUES='--bin-dir --dry-run' ;;
    completion::) _CR_VALUES='zsh bash' ;;
    install:*) _CR_VALUES='--mode=merge --mode=replace --dry-run' ;;
    verify:*) _CR_VALUES='--json' ;;
    health:*) _CR_VALUES='--project --json --project-only --global-only' ;;
    repair:*) _CR_VALUES='--apply --dry-run' ;;
    uninstall:*) _CR_VALUES='--apply' ;;
    rollback:*) _CR_VALUES='--dry-run'; _CR_KIND=files ;;
    benchmark:*) _CR_KIND=directories ;;
    graphify::) _CR_VALUES='install repair check-update upgrade verify remove rollback index query report visualize serve clean run' ;;
    graphify:install:*|graphify:repair:*|graphify:upgrade:*) _CR_VALUES='--dry-run --verbose' ;;
    graphify:remove:*|graphify:rollback:*) _CR_VALUES='--dry-run' ;;
    graphify:index:*|graphify:clean:*) _CR_VALUES='--project --output --dry-run' ;;
    graphify:query:*) _CR_VALUES='--project --output --budget' ;;
    graphify:report:*) _CR_VALUES='--project --output' ;;
    graphify:visualize:*) _CR_VALUES='--project --output --open' ;;
    graphify:serve:*) _CR_VALUES='--project --output --port' ;;
    graphify:run:*) _CR_VALUES='--project --output --port --no-serve --force --dry-run' ;;
    codebase-memory-mcp::) _CR_VALUES='run status verify install check-update upgrade rollback remove adopt mcp index project refresh clean dashboard watcher service' ;;
    codebase-memory-mcp:run:*) _CR_VALUES='--dry-run --no-dashboard --no-mcp --agent --refresh --port' ;;
    codebase-memory-mcp:status:*|codebase-memory-mcp:index:*) _CR_VALUES='--project' ;;
    codebase-memory-mcp:refresh:*|codebase-memory-mcp:clean:*) _CR_VALUES='--project --dry-run' ;;
    codebase-memory-mcp:install:*|codebase-memory-mcp:check-update:*|codebase-memory-mcp:upgrade:*|codebase-memory-mcp:rollback:*|codebase-memory-mcp:remove:*|codebase-memory-mcp:adopt:*) _CR_VALUES='--dry-run' ;;
    codebase-memory-mcp:mcp:) _CR_VALUES='status enable disable' ;;
    codebase-memory-mcp:mcp:*)
      if [ -z "$detail" ]; then _CR_VALUES='codex opencode antigravity'
      elif [ "$sub" != status ]; then _CR_VALUES='--dry-run'; fi
      ;;
    codebase-memory-mcp:project:) _CR_VALUES='status' ;;
    codebase-memory-mcp:project:status) _CR_VALUES='--project' ;;
    codebase-memory-mcp:dashboard:) _CR_VALUES='start stop status' ;;
    codebase-memory-mcp:dashboard:start) _CR_VALUES='--project --port --dry-run' ;;
    codebase-memory-mcp:dashboard:stop) _CR_VALUES='--dry-run' ;;
    codebase-memory-mcp:watcher:) _CR_VALUES='status set' ;;
    codebase-memory-mcp:watcher:set)
      if [ -z "$detail" ]; then _CR_VALUES='enabled disabled'; else _CR_VALUES='--dry-run'; fi
      ;;
    codebase-memory-mcp:service:) _CR_VALUES='install enable disable verify remove' ;;
    codebase-memory-mcp:service:install) _CR_VALUES='--port --dry-run' ;;
    codebase-memory-mcp:service:enable|codebase-memory-mcp:service:disable|codebase-memory-mcp:service:remove) _CR_VALUES='--dry-run' ;;
  esac
  [ "$shortcut" -eq 0 ] || _CR_VALUES="run $_CR_VALUES"
  case "$command:$action:$sub" in
    ::|project:*|graphify:*|completion::|cli::|codebase-memory-mcp::|codebase-memory-mcp:run:*|codebase-memory-mcp:mcp:|codebase-memory-mcp:dashboard:|codebase-memory-mcp:service:)
      _CR_VALUES="$_CR_VALUES --help -h"
      ;;
    *) [ "$count" -ne 1 ] || _CR_VALUES="$_CR_VALUES --help -h" ;;
  esac
  return 0
}
