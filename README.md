# contextrivet

A small, portable configuration manager for shared coding-agent instructions and
Agent Skills on macOS and Linux. `AGENTS.md` is the canonical global instruction
source. An opt-in project setup command adds local rules, architecture, onboarding,
and durable knowledge with a selectable canonical file and agent entry points.

> **The instruction defaults and architecture presets reflect my personal
> engineering preferences. Read them before applying them. If the approach fits
> your project, use the relevant parts and adapt them to your team's conventions.**

Different apps and teams need different architectures. A preset is guidance for
an agreed workflow, not a reason to restructure a working project. Contributions,
corrections, and alternative approaches are welcome; see [Contributing](CONTRIBUTING.md).

## Contents

- [Project quick start](#project-quick-start)
- [Upgrade compatibility](#upgrade-compatibility)
- [Shared configuration installation](#install)
- [Command-line interface](#command-line-interface)
- [Shell completion](#shell-completion)
- [Agent compatibility](#compatibility)
- [Project-local setup](#project-local-setup)
- [Stack skills](#stack-specific-coding-skills)
- [Install selected skills](#install-selected-project-skills)
- [Backups, restore, and uninstall](#project-backups-restore-and-uninstall)
- [Optional Graphify](#optional-tools-graphify)
- [Optional Codebase Memory MCP](#optional-codebase-memory-mcp)
- [Development and tests](#development-and-tests)
- [Contributing](#contributing)
- [License](#license)

## Project quick start

Clone the repository and install the command link after reviewing its preview:

```bash
git clone https://github.com/Shahzad-Official/contextrivet.git
cd contextrivet
./contextrivet cli install --dry-run
./contextrivet cli install
```

The CLI directory must be in your `PATH`; see [command-line setup](#command-line-interface).
Then, from the root of your Flutter app:

```bash
contextrivet project init --stack flutter --agents codex --dry-run
contextrivet project init --stack flutter --agents codex
contextrivet project skills --stack flutter
contextrivet project skills install --names flutter-architecture,flutter-async-state-safety --dry-run
contextrivet project skills install --names flutter-architecture,flutter-async-state-safety
```

Choose your supported agent and stack; `--agents` is optional. Project commands
require Python 3. Existing agent setup requires consent. Complete the generated
project/architecture context with your agent, then run `contextrivet project status`.
Project setup is separate from installing global shared instructions.

Flutter currently has eight catalog skills. NestJS and Next.js project profiles
are supported, with remote skill catalogs awaiting contributions. Installing a
skill places its files in the project; verify discovery in your selected agent
and ask it to use the relevant skill for a focused task.

## Upgrade compatibility

The project and CLI are now named `contextrivet`. From this checkout, install the
new command link after reviewing its preview:

```bash
./contextrivet cli install --dry-run
./contextrivet cli install
contextrivet --help
```

This creates `~/.local/bin/contextrivet` and removes an old `dev-agent-config` link
only when it points to this checkout. Unrelated commands/links are preserved.
`CONTEXTRIVET_BIN` replaces `DEV_AGENT_CONFIG_BIN`; the older environment variable
is accepted for migration. The obsolete root executable alias has been removed;
use `contextrivet` for every command. Old-name references remaining in source are
compatibility readers and migration tests for saved configurations and backups.

New global backups use `~/.agents/contextrivet/`; new project metadata and backups
use `.agents/contextrivet/`, project rule markers say `contextrivet`, and Cline's
new entry is `.clinerules/00-contextrivet.md`. Global merge installation replaces
the old managed block with the new one while preserving user instructions and
backing up the previous file. Global verification, uninstall, and rollback also
recognize old managed blocks and original backup locations.

Existing project installations continue using their original metadata/backup
namespace. `contextrivet project status`, `backups`, `restore`, and `uninstall`
recognize it, including older original-only backups. Repeated init preserves
customized rules rather than silently rebranding them or generating a duplicate
setup. To create a new branded setup, review and uninstall the old one first,
then initialize again; retained edited/untracked documents still require review.
Two active project namespaces are refused rather than guessing which to change.

Optional tools use `contextrivet` paths/ownership for fresh installs. When only
an existing old-name installation is present, they retain its original paths,
ownership markers, indexes, and service names. Virtual environments, binary
links, and registered service definitions are not relocated automatically.
Do not rename this checkout directory while links or service definitions refer
to its current location. The on-disk checkout folder does not need to match the
CLI name.

## Install

Always preview first:

```bash
./scripts/install.sh --dry-run
./scripts/install.sh --mode=merge
```

`merge` is the default. It replaces only this project's marked instruction block,
preserves all other instructions, and preserves a conflicting same-name skill.

To replace agent instruction files and the Ponytail skill:

```bash
./scripts/install.sh --mode=replace --dry-run
./scripts/install.sh --mode=replace
```

Replace mode affects only documented instruction files and the `ponytail` skill
entry. It does not edit credentials, authentication, model choices, MCP settings,
session history, JSON/TOML settings, or project-level instructions.

Agent-specific targets are installed only when their known configuration
directory or supported CLI is present. The shared `~/AGENTS.md` and
`~/.agents/skills/ponytail` entries are always installed.
Unexpected instruction symlinks and symlinked parent directories are refused.

## Command-line interface

From a checkout, use the executable at the repository root:

```bash
./contextrivet --help
./contextrivet verify
./contextrivet graphify --help
./contextrivet cbm --help
```

The main help panel groups project setup, shared configuration, code intelligence,
and CLI utilities, with stack labels and quick-start commands. Project/subcommand
help uses the same cyan and magenta palette. Color is enabled for capable terminals
and omitted from redirected output. Set `NO_COLOR=1` or `FORCE_COLOR=0` for plain
output, or `FORCE_COLOR=1` to retain ANSI colors when capturing a preview. Narrow
terminal layouts stack descriptions below commands. Help is read-only and does
not launch an agent, index a project, or start a server.

To make `contextrivet` available without the checkout's full path, create a
user-local symlink (no sudo and no shell-profile edits):

```bash
./contextrivet cli install --dry-run
./contextrivet cli install
```

The link defaults to `~/.local/bin/contextrivet`. If that directory is not
already in `PATH`, add `export PATH="$HOME/.local/bin:$PATH"` to your shell
profile yourself. Remove only this checkout's link with
`./contextrivet cli uninstall`. The command resolves the checkout through
the link, so the repository must stay in its current location.

## Shell completion

First verify that `contextrivet --help` works from your terminal. Installing the
CLI command does not automatically activate shell completion.

Enable Tab completion in your **current zsh session**:

```zsh
eval "$(contextrivet completion zsh)"
```

To keep completion enabled in **future sessions**, add the same `eval` line once
to `~/.zshrc`, after your shell framework or completion initialization and after
the CLI directory is added to `PATH`. Then save the file and open a new terminal.
Running `eval` only in the terminal enables it for that session, not future ones.

For **Oh My Zsh**, add the `eval` line immediately after the existing framework
loader; do not add a second copy of the `source` line:

```zsh
source $ZSH/oh-my-zsh.sh
eval "$(contextrivet completion zsh)"
```

If completion is not initialized, the generated zsh script initializes the
standard completion system with its normal security checks.

For **Bash**, enable the current session with:

```bash
eval "$(contextrivet completion bash)"
```

Add that line to the interactive startup file your shell loads (`~/.bashrc`, or
`~/.bash_profile` on macOS if it does not source `.bashrc`). Contextrivet prints
the scripts and does not edit either profile or install a shell plugin.

Commands, nested subcommands, supported flags, stacks, canonical filenames, skill
choices, and agent names are completed according to the current command. The
`init --skills` values are `none` and `ponytail`; remote `skills install --names`
values are entered manually. The installer flags, including `--names` and `--all`,
are suggested by Tab.
Agent lists support commas without repeating selected agents. Directory flags use
native path completion, including paths with spaces. `project restore --backup`
suggests IDs from the selected project's local new/legacy backup directories;
specify `--project PATH` before `--backup` to target another project.

Try these in your terminal, pressing Tab where indicated (do not type `<Tab>`):

```text
contextrivet <Tab>
contextrivet project <Tab>
contextrivet project init --<Tab>
contextrivet project init --stack <Tab>
contextrivet project init --stack fl<Tab>
contextrivet project skills install --<Tab>
contextrivet project init --agents codex,cl<Tab>
```

After `--stack`, Tab offers `nestjs`, `nextjs`, and `flutter`; `fl` completes to
`flutter`.

For example, type `contextrivet project ` with a trailing space and press **Tab**
to see `init`, `status`, `skills`, `backups`, `restore`, and `uninstall`. Press
**Enter** to execute a command: `contextrivet --help` followed by Enter displays
the help panel; Tab requests suggestions instead.

If Tab lists current-directory files such as `AGENTS.md`, `README.md`, or
`scripts/` instead of these subcommands, the expected completion may not be loaded
in that shell session. Run the matching `eval` command above and try again. If
it works until you open another terminal, check the persistent startup-file
entry and its position after Oh My Zsh/other completion initialization.

Some shells display all alternatives on a second Tab. This provides shell
completion like Git's option lists; inline history/ghost-text suggestions remain
part of your shell configuration. Tab completion never runs project code,
downloads a tool, indexes a repository, or starts a service. Backup suggestions
only read local directory names; no backup or project-status command is executed.

## Compatibility

| Agent | Global instructions | Portable skill location | Status |
| --- | --- | --- | --- |
| Codex | `~/.codex/AGENTS.md` | `~/.agents/skills/ponytail` | Supported |
| Claude Code | `~/.claude/CLAUDE.md` | `~/.claude/skills/ponytail` | Supported |
| Gemini CLI | `~/.gemini/GEMINI.md` | `~/.gemini/skills/ponytail` | Supported |
| OpenCode | `~/.config/opencode/AGENTS.md` | `~/.config/opencode/skills/ponytail` | Supported |
| Cline | `~/.agents/AGENTS.md` | `~/.cline/data/settings/skills/ponytail` | Supported (global rules and skills) |
| Antigravity | `~/.gemini/GEMINI.md` | `~/.gemini/config/skills/ponytail` | Supported (global rules and skills) |
| Cursor | — | — | Not implemented |

Global `install` and `cbm run` leave project instruction files alone. Project-local
files are created by explicit `project init` and `project skills install` commands
below. Agent precedence remains native: more specific project instructions can supplement or
override these global defaults.

The conditional shared code-intelligence guidance has one canonical source at
`instructions/code-intelligence.md`. Installation links it to
`~/.agents/instructions/code-intelligence.md`, and the shared `AGENTS.md` asks
agents to read that stable path only when structural code exploration is useful.
The same reference is delivered through each supported agent's existing global
instruction mechanism; it is not copied into agent-specific files or project
repositories. A Markdown reference is not treated as automatic loading: the
instruction explicitly tells the agent to open the shared file when relevant.
Project-specific `AGENTS.md` precedence remains unchanged; project extensions
are opt-in and are never created by this installer.

Antigravity reads global rules from `~/.gemini/GEMINI.md`, skills from
`~/.gemini/config/skills/`, and MCP servers from
`~/.gemini/config/mcp_config.json`. The installer reuses the Gemini-compatible
rules target and links the existing Ponytail skill source into Antigravity's
global skill directory. Cline reads shared rules via `~/.agents/AGENTS.md` and
global skills from `~/.cline/data/settings/skills/`. Neither adapter creates
project-level files.

## Project-local setup

Use this independently of global installation, from an existing project directory
or with an explicit path. Python 3 is required. Always preview first:

```bash
contextrivet project init --project /path/to/project \
  --agents codex,claude --stack flutter --dry-run
contextrivet project init --project /path/to/project \
  --agents codex,claude --stack flutter
contextrivet project status --project /path/to/project
```

Without the user-local CLI link, use `/path/to/contextrivet/contextrivet`.
When `--project` is omitted, the caller's current directory is used; it need not
be a Git repository. The target directory must already exist. These commands do
not execute project scripts, install dependencies, configure MCP, index code,
launch agents, or start an app/server.

If agent files are already present, a changing `project init` requires consent
before it creates directories, backups, metadata, or other files. It displays
`WOULD_CREATE`, `WOULD_APPEND`, and `WOULD_UPDATE` actions and identifies existing
agent entries or configuration directories, including `.agents/` even when its
filenames differ from this scaffold. In an interactive terminal it asks:

```text
Apply this plan to the existing agent setup? [y/N]
```

Only `y` or `yes` proceeds. Enter, any other response, EOF, or Ctrl+C cancels
without writing. Noninteractive runs exit 1 without writing unless consent is
explicitly supplied with `--yes` after reviewing the plan:

```bash
contextrivet project init --project /path/to/project --dry-run
contextrivet project init --project /path/to/project --yes
```

Keep the same canonical, agent, stack, and skill options in both commands.
`--yes` authorizes only the displayed additive setup; it does not replace existing
documents, reconcile an existing router/knowledge layout, or clean up files from
earlier runs. Consent is not stored for future changing invocations. Fresh
projects, dry runs (even with `--yes`), and unchanged repeated init do not prompt.
Successful writes are reported as `CREATED`, `APPENDED`, or `UPDATED` only after
the corresponding file has been written.

Choose the canonical file independently from the agents:

```bash
# Claude-only entry, with CLAUDE.md holding the actual rules.
contextrivet project init --canonical CLAUDE.md --agents claude --stack nextjs

# Central rules under .agents/, with selected agents routed to that file.
contextrivet project init --canonical .agents/AGENTS.md \
  --agents codex,opencode,cline --stack nestjs

# Just canonical rules and documentation; do not copy the optional skill.
contextrivet project init --canonical .agents/AGENTS.md --agents none --stack nextjs --skills none
```

`--canonical` supports `AGENTS.md` (default), `CLAUDE.md`, `GEMINI.md`, and
`.agents/AGENTS.md`. `--agents` is a comma-separated selection of `codex`, `claude`,
`gemini`, `opencode`, `cline`, and `antigravity`; the default creates only the
canonical file. There is no CLI auto-detection or all-agent installation during
project initialization. Entry filenames are shared by some agents, so selection
controls generated files, not which other installed agents can read them.

| Selected agent | Project entry file |
| --- | --- |
| Codex, OpenCode | `AGENTS.md` |
| Claude Code | `CLAUDE.md` |
| Gemini CLI, Antigravity | `GEMINI.md` |
| Cline | `.clinerules/00-contextrivet.md` |

Each entry instructs the agent to read the canonical file before work; if it is
already canonical, no forwarding file is needed. This uses documented native
entry locations ([Codex](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[Claude Code](https://code.claude.com/docs/en/memory),
[Gemini CLI](https://geminicli.com/docs/cli/gemini-md/),
[OpenCode](https://opencode.ai/docs/rules/),
[Cline](https://docs.cline.bot/customization/cline-rules),
[Antigravity](https://www.antigravity.google/docs/rules/)). Forwarding is an explicit
read instruction, not a promise that Markdown links are automatically imported.
Codex selection refuses a nonempty root `AGENTS.override.md`, which would shadow
`AGENTS.md`; reconcile that existing override manually first. Other native
configuration, exclusions, disabled rules, and directory-specific overrides can
also affect runtime loading and must be checked in the selected agent.

The scaffold contains:

```text
<canonical file>                       short rules and context routing
<selected agent entry files>           read the canonical file first
.agents/
  PROJECT.md                           purpose, scope, stack, constraints, checks
  ARCHITECTURE.md                       boundaries, dependencies, flow, evidence
  instructions/
    bootstrap.md                       complete required setup before implementation
    engineering.md                     SOLID, feature-first guidance, shared rules
    stack.md                           selected stack's conventions
    workflow.md                        task workflow and knowledge maintenance
    code-intelligence.md               conditional code exploration guidance
  knowledge/
    INDEX.md                           navigation to relevant feature notes
    decisions.md                       established decisions and rationale
  templates/feature.md                  starting point for actual feature notes
  skills/README.md                     selected stack skill references
  skills/ponytail/                      optional local skill and provenance
  contextrivet/project.json         remembers canonical, agents, stack, skills
  contextrivet/installed.json       tracks files actually created or changed
  contextrivet/backups/             saved originals and recovery transactions
```

New projects support exactly three stack profiles: `nestjs`, `nextjs`, and
`flutter`. Use `--stack` explicitly, or let init identify a single supported stack
from root `package.json` dependencies (`@nestjs/core` or `next`) or Flutter's SDK
entry in `pubspec.yaml`. Missing or ambiguous manifests require an explicit choice
before any project files are written. No project code is executed for detection.
It selects guidance, not app code, packages, or an architectural rewrite. Existing
projects retain their saved settings. Older generic/backend/react profiles remain
readable through compatibility templates for status, restore, and removal; they
are not offered for new initialization.

SOLID is applied proportionally; feature-first is a preference for new projects
within framework conventions. Existing projects document and preserve their
architecture rather than being automatically restructured.

### Stack-specific coding skills

`skills/stacks.json` is the shared catalog for your published coding conventions,
separation of concerns, and implementation-method skills. NestJS, Next.js, and
Flutter have independent lists. Flutter includes eight reviewed skills from
[`Shahzad-Official/flutter-skills`](https://github.com/Shahzad-Official/flutter-skills);
NestJS and Next.js lists remain empty.
Each configured entry contains `name`, `description`, and `github_url`; use a
lowercase hyphenated name, a short single-line purpose, and an HTTPS GitHub URL
pointing to the published skill. Prefer a source link pinned to a reviewed commit.
Keep these project-specific coding methods in the skills rather than duplicating
all their text into the canonical rules or forcing one stack's patterns on another.

Preview a stack's configured skill references with:

```bash
contextrivet project skills --stack nestjs
contextrivet project skills --stack nextjs
contextrivet project skills --stack flutter
```

With skills enabled, init writes `.agents/skills/README.md` alongside the bundled
optional Ponytail skill. The canonical instructions route to that index, which
lists only the selected profile's references. `--skills none` skips both the index
and the bundled skill. Catalog entries are references: this command does not
fetch GitHub repositories, install remote skills, execute code, or assert native
activation. Use the explicit installation command below for remote skill content.
Existing project skill indexes remain preserved by init; updating the shared
catalog does not silently rewrite a project's custom index.

Choose skills by the work involved; a booking, ecommerce, or admin Flutter app
uses the same catalog with a different task selection:

| Task | Skill |
| --- | --- |
| New feature/project structure | `flutter-architecture` |
| Evidence-based review and scoped fixes | `flutter-codebase-audit` |
| Stale state, races, overlapping requests | `flutter-async-state-safety` |
| APIs, login, token refresh, session isolation | `flutter-api-auth` |
| Forms, responsive layouts, accessibility | `flutter-ui-quality` |
| Firebase Auth, Firestore, Storage | `flutter-firebase-workflows` |
| Explicitly selected test-first development | `flutter-tdd-workflow` |
| Android/iOS release preparation | `flutter-release-readiness` |

Installing all skills does not mean applying all of them to every task. For
example, ask your agent: "Read the installed flutter-api-auth skill and implement
this login flow using existing project conventions. Do not launch the app; report
focused checks and manual verification steps."

### Install selected project skills

Initialize the project first, then review its stack catalog and choose skill names:

```bash
contextrivet project init --stack flutter
contextrivet project skills --stack flutter
contextrivet project skills install --names flutter-architecture,flutter-async-state-safety --dry-run
contextrivet project skills install --names flutter-architecture,flutter-async-state-safety
```

Use `--project /path/to/app` to target another initialized project. Installation
uses its saved stack; `--stack` cannot switch it. Use `--all` instead of `--names`
to select the full stack catalog. `--yes` explicitly approves the displayed plan
for noninteractive use. To install every skill for a Flutter project, run
`contextrivet project skills install --all` (or preview it with `--all --dry-run`).
Installation is separate from `init --skills`, which continues to control the bundled Ponytail scaffold. If you chose `--skills none`,
invoke installed skills explicitly using your agent's supported mechanism.

Installable catalog URLs must point to a skill directory under a full reviewed
40-character GitHub commit (`https://github.com/owner/repo/tree/<commit>/<skill>`).
The catalog pin is updated deliberately after reviewing upstream changes. It
does not follow the repository's latest branch automatically, and existing project
copies change only when you explicitly rerun installation with an updated catalog.

The installer downloads each selected repository archive once per command over
HTTPS, copies the complete selected folders into `.agents/skills/<name>/`, and
includes the upstream license. It records the pinned source in each folder's
`.contextrivet-source.json`. It never executes downloaded scripts or installs app
packages. Native agent discovery and activation still need verification; a
successful file installation does not guarantee activation in every agent.

`--dry-run` performs no downloads and creates no project files. It lists sources;
archive contents and file conflicts are checked during actual installation.
Actual installs download and validate all selected content before project writes,
then ask for consent. Missing sources/licenses, malformed archives, unsafe paths,
symlinks, or content limits fail before applying the plan. Archives are limited
to 32 MiB, selected skills to 1,000 files/32 MiB, and individual files to 4 MiB.

Repeated installation of identical content leaves project files unchanged.
An explicit rerun can update unchanged files previously installed by Contextrivet
when the catalog pin changes. Existing different files and locally edited skill
files are preserved and reported as conflicts; `--yes` does not override them.
Compare those files manually before retrying. Obsolete unchanged managed files
are removed on update, with their originals restored where available.

Skill files participate in the existing ownership, backup, restore, and uninstall
flows. Use `project backups` and `project restore --backup <id> --dry-run` to
inspect recovery options. `project uninstall` removes unchanged managed skills
alongside the project setup; later-edited files are retained under the existing
uninstall policy. Updating the shared catalog alone does not modify any project.

On the first agent task, required `[REQUIRED: ...]` placeholders and `Status:
pending` trigger onboarding. The agent should inspect the existing source, fill
verified context, and ask a concise batch of questions for unknown business goals
or architectural choices. If it cannot interact, it reports missing fields and
stops before product-code changes. New projects need agreement on the proposed
architecture. Once both documents are complete, the agent marks them `Status:
ready` and resumes the authorized task. Read-only tasks can inspect and propose
documentation without writing it. No additional first-run skill activation is
required for this gate; it is routed from the canonical rules.

`project status` returns 1 for missing resources, broken routes, unresolved
placeholders, pending status, or missing/empty required sections; it returns 0
when those structural checks pass. It is read-only and does not certify factual
accuracy or enforce an agent's behavior. Initialize successfully even when setup
is pending, then use status to check readiness. To verify manually, start a fresh
session in your selected agent and ask it to list its canonical rules, setup
status, missing details, and relevant instruction paths before editing code.
With pending docs it should ask for missing information instead of implementing.
After setup, try a small task and check that durable findings cite current source
in a feature note linked from the knowledge index. Loading and skill activation
remain unverified until observed in that agent.

Knowledge is maintained by the agent's instructed workflow, not a background
memory service. It loads the index and relevant notes rather than the whole tree,
verifies source citations, and updates durable findings during authorized work.
It avoids transcripts, secrets, personal data, and contradictory stale entries.
This can reduce repeated exploration; token or productivity savings are not
guaranteed and should be measured with comparable tasks.

Initialization is additive: existing documents/skills and already marked project
instruction blocks are preserved exactly. Existing unmarked entry files retain
their text and receive one separate project block. Changed existing files are
backed up beneath `.agents/contextrivet/backups/`, with original file contents
and restrictive backup permissions; the command prints the path. Each changing
init also records a transaction manifest and file ownership so local restore and
uninstall can distinguish preexisting files from generated files. The global
`rollback`, `uninstall`, and `verify` commands do not manage this local scaffold;
use the project subcommands below. Preview output can list preserved files before reporting a conflict,
but all destination paths are validated before writes begin. Unexpected symlinks
and path types are refused. Files are copied locally, with no links back to this
checkout, so project guidance can be committed and shared independently.

Repeated init reuses saved settings. `--agents` adds entries without removing
previous selections; `--skills ponytail` can add the local skill. `none` does not
remove existing files or selections. Edit customized local rules/docs directly;
init never resets them or upgrades their content. Switching an initialized
project's canonical filename or stack profile requires a manual migration to
avoid overwriting project-specific content. Default local skills are copied to
`.agents/skills/`; native automatic discovery varies by agent, so guidance also
provides an explicit path and does not claim that the skill is automatically active.

### Project backups, restore, and uninstall

List backups and their on-disk locations, preview removal, then explicitly approve:

```bash
contextrivet project backups --project /path/to/project
contextrivet project uninstall --project /path/to/project --dry-run
contextrivet project uninstall --project /path/to/project --yes
```

Uninstall restores original files when the installed versions are unchanged,
removes unchanged files created by this CLI, and removes this tool's marked
instruction blocks while preserving unrelated rules added later. It retains
modified generated documents/skills and untracked files, including new feature
memory. `--force` additionally restores/removes later-edited **owned** files;
review `--force --dry-run` first. Files with malformed rule markers, symlinked
paths, invalid ownership metadata, or damaged required originals are refused
before removal. `--force` does not bypass these validations or claim ownership
of preexisting/untracked documents.

Restore a selected transaction using its ID from `project backups`:

```bash
contextrivet project restore --project /path/to/project \
  --backup BACKUP_ID --dry-run
contextrivet project restore --project /path/to/project \
  --backup BACKUP_ID --yes
```

Restore reverses the files recorded by that transaction, including removing files
that did not exist beforehand and restoring original permissions. It is not a
whole-project snapshot: files introduced by other transactions are outside that
restore. Later edits that differ from the recorded result block restore by
default; review `--force --dry-run` and approve with `--force --yes` only when you
want those files replaced or removed too.

Every changing restore/uninstall first saves the current affected files and a
manifest as a new recovery transaction, then prints its recovery command. Backups
are never deleted by these commands, remain listable after uninstall, and can be
copied directly from their printed directory. Restoring the recovery transaction
can undo removal. Individual writes are atomic, but the multi-file operation is
not an atomic filesystem transaction; if interrupted, inspect the saved recovery
backup before retrying. Empty directories may remain. No recursive `.agents/`
deletion or automatic backup pruning is performed.

Older installations (including those created before ownership manifests existed)
are supported conservatively. Their timestamped original-file backups are listed
as `legacy` and can restore the saved originals with consent and a recovery copy.
These older backups did not record original permissions; restoration uses the
saved copy's permissions.
Legacy uninstall removes managed rule blocks and manager metadata, retaining
untracked documents/skills because the CLI cannot prove which it created.
Neither `--yes` nor `--force` guesses that ownership. Use the listed originals
for exact restoration and review any remaining documents manually.

Dry runs never create backups or mutate files, even with `--yes` or `--force`.
Applying a removal/restore prompts `[y/N]` in a terminal and requires `--yes` in
noninteractive use. Unchanged operations do not prompt. To verify manually in a
disposable project, initialize over an existing rule, edit a generated document,
and preview uninstall: it should restore the original rule and retain that edited
document. Approve uninstall, list its recovery backup, and restore it to recover
the previous configuration. No app/server/device launch is needed for this check.

Focused verification for this command:

```bash
python3 tests/test_project.py
bash tests/test_cli.sh
python3 tests/test_rename.py
```

## Backups and rollback

Every changing install creates a timestamped backup and TSV manifest under:

```text
~/.agents/contextrivet/backups/
```

The installer prints its exact rollback command. Restore the latest transaction or
a selected transaction with:

```bash
./scripts/rollback.sh --dry-run
./scripts/rollback.sh
./scripts/rollback.sh ~/.agents/contextrivet/backups/TIMESTAMP-PID
```

Rollback restores original files, directories, and symbolic links, or removes paths
that did not exist before the transaction. Keep the repository at the same location
while installed because skill links point into it.

## Verify and uninstall

```bash
./scripts/verify.sh
./scripts/verify.sh --json       # machine-readable discovery and health report
./scripts/uninstall.sh            # preview
./scripts/uninstall.sh --apply
```

Verification reports the operating system, CLI installation and safe `--version`
result, VS Code extension discovery, configuration presence, instruction and skill
health, and unsupported adapters. CLI, VS Code extension, and configuration presence
are independent. When a VS Code CLI is available, verification uses its read-only
extension list; known extension directories are a presence-only fallback and never
proof that an extension is active. The fallback covers local VS Code, Insiders,
VSCodium, Flatpak/XDG data, VS Code Server and Server Insiders used by Remote SSH,
WSL, and Dev Containers, plus an explicitly configured `VSCODE_AGENT_FOLDER`.
Symlinked, invalid, and unreadable extension roots are ignored. Filesystem
verification does not prove that an agent activated Ponytail, so runtime activation
remains `unverified`.

## Ponytail provenance

Ponytail is a reviewed local adaptation, version `1.0.2-contextrivet`, of the
MIT-licensed [Ponytail project](https://github.com/dietrichgebert/ponytail). Full
provenance is recorded in `skills/ponytail/SOURCE.md`. Installing the bundled
Ponytail adaptation requires no downloads and executes no upstream code.

## Optional tools: Graphify

Graphify is separate from instructions and skills. Managing it never runs
`graphify install`, edits `AGENTS.md`, registers hooks or MCP, or starts a service.
Preview and install the latest stable compatible release in a private virtual
environment:

```bash
./scripts/tools.sh graphify install --dry-run
./scripts/tools.sh graphify install
./scripts/tools.sh graphify verify
```

Add `--verbose` to a fresh `install` command to stream pip's download and
installation details.

Fresh installation resolves the latest non-prerelease release and universal wheel
from the authoritative PyPI JSON API. If metadata lookup is unavailable, it falls
back safely to the retained `graphifyy==0.9.88` pin under
`${XDG_DATA_HOME:-$HOME/.local/share}/contextrivet/tools/graphify/VERSION`.
It downloads the selected official wheel and verifies its PyPI SHA-256 before
installation. The retained 0.9.88 wheel SHA-256 is
`04e5a44c0ff94554315e03d39d8eccfddb2850b77837ede23d75f0f63dc4e66d`
and remains the trusted fallback. Package source and license metadata live in
`tools/graphify/tool.conf`.

Installation preflight requires Python 3.10+ and tests `venv` before any download
or target change. System pip is not required: the new environment's pip is used,
and `ensurepip` is attempted inside that environment when necessary. If the OS
Python lacks venv/ensurepip, the manager detects common macOS/Linux package
managers and prints an appropriate prerequisite command. It never runs `sudo`,
`apt`, `dnf`, `apk`, `pacman`, or Homebrew itself.

The environment's resolved versions are recorded in `dependencies.txt` after
installation. The Graphify wheel is exactly pinned and hash-verified, but its
transitive dependencies are resolved from Graphify's declared constraints and
are not fully hash-locked. Review `dependencies.txt` when reproducibility or
supply-chain policy requires a complete dependency lock.

Routine install and verify operations never upgrade a healthy installation.
Local operations use the version in validated manager metadata and do not
contact PyPI. A healthy install is unchanged by routine install. Successful
install output is concise; failures point to a retained log under the Graphify
manager state directory, and `--verbose` streams pip details.
Update checking is read-only, and upgrades must be explicit:

```bash
./scripts/tools.sh graphify check-update
./scripts/tools.sh graphify upgrade --dry-run
./scripts/tools.sh graphify upgrade
```

The manager reports current and latest stable versions, rejects prereleases and
yanked/unsupported wheel artifacts, verifies the selected wheel, and records its
release URL, digest, and resolved dependencies. A new release is staged and
verified before it becomes current. Failed upgrades leave the working version
selected, while successful upgrades can be rolled back with the printed command.

The verified wheel and download helper use a temporary staging directory, but the
Graphify virtual environment is created directly at its permanent versioned path.
Python console scripts embed the environment's absolute interpreter path in their
shebang, so verification checks that the installed `graphify` interpreter exists.
For an older install with a stale staging-path shebang, verify and explicitly
repair it with:

```bash
./scripts/tools.sh graphify verify
./scripts/tools.sh graphify repair --dry-run
./scripts/tools.sh graphify repair
./scripts/tools.sh graphify verify
```

Repair is limited to a directory with valid manager ownership metadata. It backs
up that exact version before rebuilding it; the printed rollback command can
restore the prior directory. Unexpected files and symlinks are not overwritten.

Indexing is explicit and code-only:

```bash
./scripts/tools.sh graphify index --project /absolute/path/to/project --dry-run
./scripts/tools.sh graphify index --project /absolute/path/to/project
./scripts/tools.sh graphify index \
  --project /absolute/path/to/project \
  --output /absolute/path/to/output-root
```

Graphify interprets `--out OUTPUT_ROOT` as a parent and writes the graph
to `OUTPUT_ROOT/graphify-out/`. The manager treats extraction as successful when
`graph.json` contains node-link `nodes` and `links` arrays. If extraction does not
create `GRAPH_REPORT.md`, it separately attempts `cluster-only --no-label --no-viz`
to generate a report without AI labeling or visualization; report failure is
reported as a warning and does not invalidate the graph. The default output root
is an XDG data path derived from the canonical project path and is outside the
source tree. Outputs inside the selected project are refused. Project paths
(including a symlinked project directory) are resolved to their physical
directory before mapping; this keeps the same project associated with the same
isolated index.
For rollback and symlink safety, a custom output root must remain beneath `HOME`,
`XDG_DATA_HOME`, or `XDG_STATE_HOME`.

Every run forces `graphify extract PROJECT --out OUTPUT_ROOT --code-only`, removes
known AI-provider credentials from the child environment, disables query logging
and cloud tips, and does not enable document/media extraction. It does not scan
projects automatically. The selected project's canonical physical directory is
used so symlink aliases resolve to one project index.

Project operations use the same default project-specific location, so there is no
need to locate `graph.json` yourself. `--project` is optional; from inside a
repository, the commands below use that current working directory:

```bash
cd ~/retail-pos-api
contextrivet graphify index
contextrivet graphify query "CreateUserHandler dependencies" --budget 1200
contextrivet graphify report
contextrivet graphify visualize
contextrivet graphify serve --port 8080
contextrivet graphify clean --dry-run
```

An explicit project always takes precedence, including when the CLI is invoked
from another directory:

```bash
./scripts/tools.sh graphify query --project /path/to/project "where is auth configured?" --budget 1200
./scripts/tools.sh graphify report --project /path/to/project
./scripts/tools.sh graphify visualize --project /path/to/project
./scripts/tools.sh graphify visualize --project /path/to/project --open
./scripts/tools.sh graphify serve --project /path/to/project --port 8080
./scripts/tools.sh graphify clean --project /path/to/project --dry-run
./scripts/tools.sh graphify clean --project /path/to/project
```

For a graph created with a custom `index --output /path/to/output-root`, pass that
same output root with `--output` to `query`, `report`, `visualize`, `serve`, or
`clean`.

For `index`, `query`, `report`, `visualize`, `serve`, `clean`, and `run`, the calling
shell's current working directory is used when `--project` is omitted. The CLI
does not switch to the contextrivet installation directory. Paths containing
spaces and symlinked project directories are normalized before lookup. An
explicit invalid project path is an error and never falls back to the caller's
directory.

These commands require a prior successful index and never re-index. Query uses
Graphify's native traversal against the existing graph; report runs native
`cluster-only --no-label --no-viz`; visualization uses native `export html` and
does not recluster or modify source files. Query logging is disabled and known
provider credentials are removed from each Graphify process. `--open` is opt-in;
headless Linux and SSH/VS Code Remote sessions print the HTML path without trying
to launch a remote browser. In VS Code Remote SSH, open the printed absolute path
from the remote workspace's File > Open File dialog (or the Remote Explorer); the
HTML is stored under the remote user's XDG data directory, not inside the source
repository. Supply `--output` when the graph was indexed to a custom output root.

`serve` requires an existing graph and generated `graph.html`; it never indexes
or generates HTML automatically. It serves that directory in the foreground on
`127.0.0.1` (default port 8080), with Python's standard-library HTTP server, and
stops with Ctrl+C. For Remote SSH, forward the printed port from VS Code's Ports
panel and open `http://localhost:8080/graph.html` on your local Mac. No public
interface or background service is started.

For the complete local workflow, run this from any project directory:

```bash
cd ~/retail-pos-api
contextrivet graphify run
```

`run` reuses a healthy managed Graphify installation (installing the latest
verified stable release only when missing), indexes code-only when the graph is
missing or stale, generates a local architecture report and native HTML, then
serves it on `127.0.0.1:8080` in the foreground. Use `--project PATH` to select
another project, `--output PATH` for an index created with a custom output root,
`--port 9090` to select a port, `--no-serve` to stop after generating artifacts,
`--force` to rebuild, or `--dry-run` to preview the plan. Dry-run does not install,
index, generate files, or start a server. It may perform the installer's
temporary prerequisite probe when Graphify is absent; the probe is cleaned up.
The manager does not repair a corrupted installation automatically; run the
explicit `graphify repair` command after reviewing its dry-run.

For Git projects, unchanged detection uses the checked-out commit plus tracked
and untracked Git status; for non-Git folders it uses file-content checksums.
The non-Git check skips common dependency/build directories (`node_modules`,
virtual environments, `build`, and `dist`), so changes limited to those ignored
trees do not trigger a rebuild. The first `run` against an existing index with
no saved run fingerprint rebuilds it once to establish a baseline. Failed
rebuilds preserve the prior manager-owned graph and retain failed output for
inspection. Successful run fingerprints are stored outside the project beneath
`XDG_STATE_HOME` (or `~/.local/state`). No project app, scripts, tests, hooks,
MCP servers, or cloud/AI processing are started.

`clean` removes only recognized Graphify-generated files from the selected
project's `graphify-out` tree (or the explicitly supplied custom output's
generated index). This includes the standard graph/report/dashboard files,
Graphify's named `*-callflow.html` visualization, known manifest/cost and
`.graphify_*` metadata, and hash-named cache files in Graphify's known cache
namespaces. It validates the complete tree before
deletion; symlinks, unknown files/directories, and changed ownership metadata
make the operation fail without starting cleanup. Cleanup removes files
individually rather than recursively deleting arbitrary content, and can resume
if interrupted while the manager ownership marker remains. Dry-run prints the
resolved project and exact index target. If a dashboard server is active for
that index, clean refuses and asks you to stop it with Ctrl+C. Clean does not
remove Graphify itself; `remove` does not clean indexes.

Removal is limited to an installation carrying unchanged manager ownership
metadata:

```bash
./scripts/tools.sh graphify remove --dry-run
./scripts/tools.sh graphify remove
./scripts/tools.sh graphify rollback --dry-run
./scripts/tools.sh graphify rollback
```

Tool backups are stored under
`${XDG_STATE_HOME:-$HOME/.local/state}/contextrivet/tools/graphify/backups`.
Rollback refuses mismatched manifests, changed install ownership, symlinked paths,
or an occupied restore destination. Tool rollback is intentionally separate from
the instruction installer's rollback.

On Debian and Ubuntu, the distribution's `python3-venv` package may be needed.
The dry run performs the same preflight and reports whether installation can
proceed; if not, it prints the suggested command for the user to review and run.

## Simple benchmark procedure

Prepare three isolated copies of a disposable test repository:

```bash
./scripts/benchmark.sh /path/to/test-repository /tmp/agent-benchmark
```

The command creates `default`, `rules`, and `rules-ponytail` variants with separate
HOME and workspace directories. It never copies credentials. For a fair comparison:

1. Use the same agent release, exact model version, prompt, permissions, repository
   snapshot, and test command in every variant.
2. Explicitly request Ponytail in the `rules-ponytail` run so activation is observable.
3. Record elapsed duration, final diff, and test result.
4. Record tokens, cost, and tool calls only when the agent exposes them; otherwise
   mark those fields unavailable.
5. Repeat runs to reduce one-off model variation, and never use a production project.

The helper prepares environments only. It deliberately does not launch agents,
authenticate them, execute paid requests, or claim unsupported telemetry.

## Optional Codebase Memory MCP

CBM remains optional and independent of Graphify. Binary files installed by this
manager live under
`${XDG_DATA_HOME:-$HOME/.local/share}/contextrivet/tools/codebase-memory-mcp/versions/`;
the active version is exposed through `~/.local/bin/codebase-memory-mcp`.
Fresh installation is pinned to the v0.11.0 release in
`tools/codebase-memory-mcp/tool.conf`. Each install downloads the official
platform archive (macOS canonical assets; Linux portable assets) and its release
`checksums.txt` over HTTPS, verifies SHA-256, streams only the exact executable
member without extracting arbitrary archive paths, checks its version in staging
and at the final destination, then activates it. Installation shows live archive
download progress and names each verification/activation stage. The selected
archive hash and platform are recorded in local manager metadata. New
Codex/OpenCode integrations use the stable manager executable link so explicit
upgrades continue using the active version. `curl` or `wget`, `tar`, a SHA-256 utility
(`sha256sum` or macOS `shasum`), and Python 3 for JSON/OpenCode and project
mapping features are used; no privileged package manager is called.

```bash
contextrivet tools codebase-memory-mcp status
contextrivet tools codebase-memory-mcp verify
contextrivet tools codebase-memory-mcp install --dry-run
contextrivet tools codebase-memory-mcp install
contextrivet tools codebase-memory-mcp check-update
contextrivet tools codebase-memory-mcp upgrade --dry-run
contextrivet tools codebase-memory-mcp upgrade
contextrivet tools codebase-memory-mcp rollback --dry-run
contextrivet tools codebase-memory-mcp rollback
contextrivet tools codebase-memory-mcp remove --dry-run
contextrivet tools codebase-memory-mcp remove
```

Routine `install` keeps a healthy active manager-owned version; it never
downgrades or checks for updates. Only `check-update` and explicit `upgrade`
query GitHub for the latest stable release. Previous manager-owned versions are
retained for rollback. Removal affects only versions with intact ownership
metadata and matching binary hashes, plus this manager's executable symlink.
It preserves external binaries, CBM caches, indexes, MCP configuration, and
dashboard settings. An external binary is never overwritten or removed.
`adopt` only records an existing executable as external and does not transfer
ownership; use it to make the existing installation available to the adapter:

```bash
contextrivet tools codebase-memory-mcp adopt --dry-run
contextrivet tools codebase-memory-mcp adopt
```

### One-command project bootstrap

From any Git repository, bootstrap its CBM setup with:

```bash
cd /path/to/your-git-project
contextrivet cbm run --dry-run
contextrivet cbm run
```

The run command verifies an existing binary (including an external one), or
installs the verified pinned release if no binary exists. It merges the global
shared instructions without touching the project's `AGENTS.md`; configures MCP
only for detected Codex/OpenCode/Antigravity installations, preserving any external CBM
entry; indexes only when the project is missing; and refreshes only when CBM
reports a stale state or `--refresh` is explicitly passed. Repeated runs do not
reinstall or re-index a healthy project. `--agent codex`, `--agent opencode`, or
`--agent antigravity`
limits MCP setup to that available agent; unsupported/missing agents are never
configured. Use `--no-mcp` or `--no-dashboard` to skip either action, and
`--port 8080` to choose a dashboard port.

```bash
contextrivet cbm run --dry-run --no-mcp --no-dashboard
contextrivet cbm run --agent codex --refresh
contextrivet cbm run --agent antigravity
contextrivet cbm run --no-dashboard
```

Dry-run plans installation and global configuration changes but does not
download files, call CBM project/status commands, alter indexes, or start a
dashboard. It therefore reports index state as unchecked. A real run reports
watcher settings separately from CBM's project registration strategy; neither
is proof that future file changes are detected and reindexed. An occupied port
is never taken over: use `--no-dashboard`, choose another port, or inspect the
existing listener. Incompatible CBM runtime/cache conflicts are left to CBM's
admission checks; the manager does not stop or kill daemons and directs you to
`codebase-memory-mcp daemon status` for diagnosis.

Codex MCP management respects `CODEX_HOME` (default `~/.codex`). When the
Codex CLI is present, the manager uses its documented MCP commands; without the
CLI it can add a marked TOML block so the Codex VS Code extension can use the
same config. OpenCode uses its global JSON config (or `OPENCODE_CONFIG`).
Antigravity uses `~/.gemini/config/mcp_config.json` and can be enabled only with
a verified manager-owned CBM binary. All these changes preserve unrelated
servers/settings, back up the config, report external entries without taking
ownership, and disable only unchanged manager-owned entries. OpenCode JSONC and
invalid JSON configs are left untouched. Cline's shared rules and skill are
managed, but its separate MCP settings are not yet managed by this CLI.

```bash
contextrivet tools codebase-memory-mcp mcp status codex
contextrivet tools codebase-memory-mcp mcp enable codex --dry-run
contextrivet tools codebase-memory-mcp mcp enable codex
contextrivet tools codebase-memory-mcp mcp disable codex --dry-run
contextrivet tools codebase-memory-mcp mcp disable codex
contextrivet tools codebase-memory-mcp mcp status opencode
contextrivet tools codebase-memory-mcp mcp enable opencode --dry-run
contextrivet tools codebase-memory-mcp mcp enable opencode
contextrivet tools codebase-memory-mcp mcp disable opencode --dry-run
contextrivet tools codebase-memory-mcp mcp disable opencode
contextrivet tools codebase-memory-mcp mcp status antigravity
contextrivet tools codebase-memory-mcp mcp enable antigravity --dry-run
contextrivet tools codebase-memory-mcp mcp enable antigravity
contextrivet tools codebase-memory-mcp mcp disable antigravity --dry-run
contextrivet tools codebase-memory-mcp mcp disable antigravity
```

Project indexes remain in CBM's own cache, outside the source tree. The manager
records project mappings only when it can confirm that the index did not exist
before its explicit `index` command and CBM subsequently reports the exact
canonical repository path. `clean` refuses external/unmapped projects, changed
names, unparseable project lists, symlinks, and active dashboards for that
project; it calls CBM's documented `delete_project` command and verifies the
result. Project commands default to the current directory only when it is a Git
repository; otherwise pass `--project PATH`. Explicit paths always win.

```bash
cd ~/retail-pos-api
contextrivet tools codebase-memory-mcp index
contextrivet tools codebase-memory-mcp status --project "$PWD"
contextrivet tools codebase-memory-mcp refresh --project "$PWD" --dry-run
contextrivet tools codebase-memory-mcp refresh --project "$PWD"
contextrivet tools codebase-memory-mcp clean --project "$PWD" --dry-run
contextrivet tools codebase-memory-mcp clean --project "$PWD"
contextrivet tools codebase-memory-mcp dashboard start --project "$PWD" --port 9749
contextrivet tools codebase-memory-mcp dashboard status
contextrivet tools codebase-memory-mcp dashboard stop --dry-run
contextrivet tools codebase-memory-mcp dashboard stop
contextrivet tools codebase-memory-mcp watcher status
contextrivet tools codebase-memory-mcp watcher set disabled --dry-run
contextrivet tools codebase-memory-mcp watcher set disabled
```

The dashboard binds to loopback and prints a project-specific URL. Its managed
runner keeps CBM's stdio open and runs in the background on macOS and Linux.
`dashboard stop` stops only that manager-owned runner. CBM shares its UI through
its coordination daemon, so the UI can remain available while another CBM/MCP
session is connected; the manager will report this and will not kill a shared
daemon. After indexing, a short-lived CBM daemon can briefly own the port before
its UI is ready or the port is released. When the listener is confirmed as the
selected CBM binary's internal daemon but HTTP is not ready, the manager starts
its persistent `--ui=true` CBM session so it can join or establish the shared
daemon; it does not wait for or terminate the short-lived CLI process. Startup
succeeds only after a healthy HTTP HTML response from a verified CBM listener,
with a 30-second bound. An unrelated or unverifiable listener is refused.
Failed startup reports both the manager runner log and CBM's daemon log path.
Stop the runner before cleaning that project's index or removing the binary.

Persistent dashboard services are optional and require explicit actions. The
manager creates only its own service definition and refuses pre-existing or
modified content:

```bash
contextrivet tools codebase-memory-mcp service install --port 9749 --dry-run
contextrivet tools codebase-memory-mcp service install --port 9749
contextrivet tools codebase-memory-mcp service verify
contextrivet tools codebase-memory-mcp service enable --dry-run
contextrivet tools codebase-memory-mcp service enable
contextrivet tools codebase-memory-mcp service disable --dry-run
contextrivet tools codebase-memory-mcp service disable
contextrivet tools codebase-memory-mcp service remove --dry-run
contextrivet tools codebase-memory-mcp service remove
```

Linux uses a user systemd unit. `service verify` reports whether lingering is
enabled; surviving logout requires the explicit host-admin action
`loginctl enable-linger`, which this manager never performs. macOS uses a
user LaunchAgent, active in the logged-in GUI session and stopped at logout.
Services bind through CBM's documented loopback UI. Service management requires
a manager-owned CBM binary and available `systemctl --user` or `launchctl`;
other operating systems and unavailable user service managers are unsupported.
The generated service references this checkout's dashboard runner, so keep the
checkout at the same path while the service definition is installed.

Watcher controls only read or set CBM's global `watcher_enabled` setting.
Current upstream documentation distinguishes this from `auto_watch`: an open
MCP session registers its own project with the background watcher. The manager's
CLI `index`/`refresh` operation does not prove that registration. Project
`status` reports CBM's `watch.strategy` when the installed version exposes it;
this is registration evidence, not proof the poller is healthy. Source-change
detection and successful reindex after changes remain unverified unless checked
against live CBM state. The watcher subsystem master setting is read when the
daemon starts; this manager does not stop or restart CBM's shared daemon.

### Debian clean-room test procedure (documentation only)

This procedure is for a later, separately approved Debian Remote SSH run. It
first inventories the manually installed executable, Codex registration, and
service files without printing credentials. Do not reset or remove any of these
external resources as part of this test. Use a temporary HOME, cache, Codex
config, and disposable Git repository; never point the test at a real project.
Do not run it with `HOME`, `CODEX_HOME`, or cache variables pointing at a real
user home.

```bash
cd /path/to/contextrivet
REAL_HOME="$HOME"
REAL_CODEX_HOME="${CODEX_HOME:-$REAL_HOME/.codex}"
REAL_CBMCACHE_DIR="${CBM_CACHE_DIR:-$REAL_HOME/.cache/codebase-memory-mcp}"
REAL_XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$REAL_HOME/.config}"
# Read-only inventory: capture paths and ownership/state, not config contents.
command -v codebase-memory-mcp || true
codebase-memory-mcp --version 2>/dev/null || true
contextrivet tools codebase-memory-mcp status
contextrivet tools codebase-memory-mcp mcp status codex
systemctl --user list-unit-files 'contextrivet-cbm-dashboard.service' 2>/dev/null || true
ls -ld "$HOME/.local/bin/codebase-memory-mcp" "$HOME/.local/share/codebase-memory-mcp" 2>/dev/null || true

CBM_TEST_HOME="$(mktemp -d /tmp/contextrivet-cbm.XXXXXX)"
export HOME="$CBM_TEST_HOME"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_STATE_HOME="$HOME/.local/state"
export XDG_CONFIG_HOME="$HOME/.config"
export CBM_CACHE_DIR="$HOME/.cache/codebase-memory-mcp"
export CODEX_HOME="$HOME/.codex"
mkdir -p "$CODEX_HOME" "$HOME/.config/opencode"
HOME="$HOME" ./scripts/install.sh --dry-run
HOME="$HOME" ./scripts/install.sh
HOME="$HOME" ./scripts/verify.sh
mkdir -p "$HOME/cbm-fixture"
git -C "$HOME/cbm-fixture" init
printf 'export function demo() { return 1; }\n' > "$HOME/cbm-fixture/demo.ts"

./contextrivet tools codebase-memory-mcp install --dry-run
./contextrivet tools codebase-memory-mcp install
./contextrivet tools codebase-memory-mcp verify
./contextrivet tools codebase-memory-mcp index --project "$HOME/cbm-fixture"
./contextrivet tools codebase-memory-mcp status --project "$HOME/cbm-fixture"
CBM_PROJECT_NAME="$(./contextrivet tools codebase-memory-mcp status --project "$HOME/cbm-fixture" | sed -n 's/^CBM project: //p')"
"$HOME/.local/bin/codebase-memory-mcp" cli search_graph --project "$CBM_PROJECT_NAME" --label Function --name-pattern demo --limit 5
./contextrivet tools codebase-memory-mcp mcp enable codex --dry-run
./contextrivet tools codebase-memory-mcp mcp enable codex
# If an isolated Codex CLI/client is available, connect using this CODEX_HOME
# and test MCP; do not borrow the real user's credentials or config.
./contextrivet tools codebase-memory-mcp mcp disable codex
./contextrivet tools codebase-memory-mcp dashboard start --project "$HOME/cbm-fixture" --port 19749
# Open the printed loopback URL or forward port 19749 in VS Code Remote SSH.
# In a separate terminal, verify the HTTP endpoint:
curl --fail --silent --show-error http://127.0.0.1:19749/ >/dev/null
./contextrivet tools codebase-memory-mcp dashboard stop
./contextrivet tools codebase-memory-mcp clean --project "$HOME/cbm-fixture" --dry-run
./contextrivet tools codebase-memory-mcp clean --project "$HOME/cbm-fixture"
./contextrivet tools codebase-memory-mcp remove --dry-run
./contextrivet tools codebase-memory-mcp remove
```

For synchronization, keep an isolated Codex MCP session open for the fixture
project and inspect `status --project` before and after a harmless fixture-only
source edit. Record separately the `watch.strategy` registration evidence,
whether CBM reports source changes, and whether index status changes afterward.
Do not infer these outcomes from `watcher_enabled` alone.

Only after the clean-room test is reviewed should a separate, explicitly
approved stage consider the existing installation. Run this backup block in a
new shell with the normal HOME (not the isolated HOME exported above). It copies
only configuration files, never project indexes or the full cache:

```bash
umask 077
REAL_HOME="$HOME"
REAL_CODEX_HOME="${CODEX_HOME:-$REAL_HOME/.codex}"
REAL_CBMCACHE_DIR="${CBM_CACHE_DIR:-$REAL_HOME/.cache/codebase-memory-mcp}"
REAL_XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$REAL_HOME/.config}"
PARENT="$REAL_HOME/.local/state/contextrivet"
[ ! -L "$REAL_HOME" ] && [ ! -L "$REAL_HOME/.local" ] && [ ! -L "$REAL_HOME/.local/state" ] && [ ! -L "$PARENT" ]
mkdir -p "$PARENT"
BACKUP="$(mktemp -d "$PARENT/cbm-preflight.XXXXXX")"
chmod 700 "$BACKUP"
for file in "$REAL_CODEX_HOME/config.toml" \
  "$REAL_CBMCACHE_DIR/_config.db" \
  "$REAL_CBMCACHE_DIR/config.json" \
  "$REAL_XDG_CONFIG_HOME/systemd/user/contextrivet-cbm-dashboard.service" \
  "$REAL_HOME/Library/LaunchAgents/org.contextrivet.cbm-dashboard.plist"; do
  if [ -f "$file" ] && [ ! -L "$file" ]; then
    relative="${file#"$REAL_HOME"/}"
    case "$relative" in /*) relative="external/${file#/}" ;; esac
    mkdir -p "$BACKUP/$(dirname "$relative")"
    cp -p "$file" "$BACKUP/$relative"
    printf '%s\t%s\n' "$file" "$BACKUP/$relative" >> "$BACKUP/manifest.tsv"
  fi
done
```

Record which binary, MCP entry, cache/index, and service definition is external
versus manager-owned. Do not use this prototype's `remove` or `clean` on any
external resource. Roll back only by disabling an unchanged manager-owned MCP
entry or service, removing the disposable test index, and removing
manager-owned test binaries; restore user-owned files only from the matching
backup. A real reset of the prior installation requires separate explicit
approval.

After verifying that `CBM_TEST_HOME` still names the temporary directory
created above, delete only that directory to discard its isolated cache and
configs. Do not run the cleanup against your normal HOME:

```bash
case "$CBM_TEST_HOME" in
  /tmp/contextrivet-cbm.*) [ -d "$CBM_TEST_HOME" ] && [ ! -L "$CBM_TEST_HOME" ] && rm -rf -- "$CBM_TEST_HOME" ;;
  *) echo "Refusing unexpected test path: $CBM_TEST_HOME" >&2; exit 1 ;;
esac
```

## Development and tests

```bash
bash -n contextrivet scripts/*.sh scripts/lib/*.sh scripts/tools/*.sh tests/*.sh
bash tests/test_cli.sh
python3 tests/test_help.py
python3 tests/test_completion.py
python3 tests/test_project.py
python3 tests/test_skill_install.py
python3 tests/test_rename.py
bash tests/test_install.sh
bash tests/test_code_intelligence.sh
bash tests/test_verify.sh
bash tests/test_tools.sh
bash tests/test_cbm.sh
bash tests/test_cbm_projects.sh
bash tests/test_cbm_service.sh
bash tests/test_cbm_run.sh
bash tests/smoke.sh
```

Tests use temporary HOME directories and remove them afterward. They cover fresh
installation, merge, replace, adapters, repeated installation, symlink conflicts,
rollback, uninstall, benchmark isolation, conditional code-intelligence links,
CBM install/MCP fixtures, project mapping and cleanup, dashboard ownership and
port-conflict fixtures, watcher evidence reporting, one-command CBM bootstrap
and isolated cache fixtures, and isolated Graphify tool management.
Service-definition tests use fake service-manager commands and do not install
systemd units, launch agents, or persistent services.

## Contributing

You are most welcome to contribute if you think Contextrivet can be improved,
updated, or extended. Documentation fixes, bug reports, workflow feedback, new
stack skills, and alternative approaches with a clear use case are welcome.
You do not have to share all my coding or architecture preferences to help.

Read [CONTRIBUTING.md](CONTRIBUTING.md) for issue/PR guidance, focused checks,
and skill catalog conventions. You can [open an issue](https://github.com/Shahzad-Official/contextrivet/issues)
or [submit a pull request](https://github.com/Shahzad-Official/contextrivet/pulls).

## License

Contextrivet's own code and documentation are licensed under the [MIT License](LICENSE).
Bundled adaptations and downloaded skills/tools retain their upstream notices
and applicable licenses. Ponytail attribution is recorded in
[its provenance document](skills/ponytail/SOURCE.md); installed remote skills
include their source license and pinned-source record.
