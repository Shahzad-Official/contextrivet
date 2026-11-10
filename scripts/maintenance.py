#!/usr/bin/env python3
"""Read-only health checks and explicitly requested mechanical maintenance."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
sys.dont_write_bytecode = True
from urllib.parse import unquote, urlsplit

import project as p


def finding(scope, identifier, state, path, message):
    return dict(scope=scope, id=identifier, state=state, path=str(path), message=message)


def result(findings):
    return "fail" if any(f["state"] == "failure" for f in findings) else "warn" if any(f["state"] == "warning" for f in findings) else "pass"


def visible_lines(text):
    """Only prose outside Markdown fenced examples participates in link checks."""
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            yield line


def references(text, index=False, canonical=False):
    for line in visible_lines(text):
        # Index entries and canonical routes use project-root-relative backticks.
        pattern = r"`(\.agents/[^`]+)`" if canonical else r"^\s*- `([^`]+)`\s+[—–-]" if index else None
        if pattern:
            for target in re.findall(pattern, line):
                if not any(c in target for c in "<>{}*"):
                    yield target, True
        prose = re.sub(r"(`+).*?\1", "", line)
        for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^\s)]+)\)", prose):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path or any(c in target for c in "<>{}*"):
                continue
            yield unquote(parsed.path), False


def reference_findings(project, config):
    findings = []
    paths = set(p.instruction_files(config))
    instruction_dir = p.safe_path(project, ".agents/instructions", directory=True)
    if instruction_dir.exists():
        paths.update(path.relative_to(project).as_posix() for path in instruction_dir.glob("*.md"))
    paths.add(".agents/knowledge/INDEX.md")
    for relative in sorted(paths):
        path = p.safe_path(project, relative)
        if not path.exists():
            continue
        text = path.read_text()
        canonical = relative == config["canonical"]
        if canonical:
            text = p.managed_block(text, relative) or ""
        for target, root_relative in references(text, relative.endswith("knowledge/INDEX.md"), canonical):
            candidate = project / target if root_relative else path.parent / target
            normalized = Path(os.path.abspath(candidate))
            if normalized != project and project not in normalized.parents:
                findings.append(finding("project", "reference.unsafe", "failure", relative, "Reference escapes project: " + target))
                continue
            # References can name directories, but must not traverse symlinks.
            destination = p.safe_path(project, normalized.relative_to(project).as_posix(), directory=normalized.is_dir())
            if not destination.exists():
                findings.append(finding("project", "reference.missing", "failure", relative, "Missing reference: " + target))
    return findings


def note_path(project, relative):
    if not isinstance(relative, str) or relative not in (".agents/PROJECT.md", ".agents/ARCHITECTURE.md") and not (
        relative.startswith(".agents/knowledge/") and relative.endswith(".md")):
        raise ValueError("Evidence notes must be project context, architecture, or .agents/knowledge/*.md")
    return p.safe_path(project, relative)


def sources(project, relative):
    text = note_path(project, relative).read_text()
    paths = set()
    for line in visible_lines(text):
        match = re.fullmatch(r"Source: `([^`]+)`\s*", line)
        if match:
            paths.add(match[1])
    values = {}
    for path in sorted(paths):
        source = p.safe_path(project, path)
        values[path] = p.digest(source.read_bytes()) if source.exists() else None
    return values


def evidence_path():
    return str(Path(p.STATE).parent / "evidence.json")


def evidence(project):
    path = p.safe_path(project, evidence_path())
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("notes"), dict):
        raise ValueError("Invalid evidence baseline")
    for note, records in data["notes"].items():
        note_path(project, note)
        if not isinstance(records, dict):
            raise ValueError("Invalid evidence note record")
        for source, value in records.items():
            p.safe_path(project, source)
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("Invalid evidence fingerprint")
    return data["notes"]


def drift_findings(project):
    notes = evidence(project)
    findings = []
    directory = p.safe_path(project, ".agents/knowledge", directory=True)
    candidates = set(notes) | {".agents/PROJECT.md", ".agents/ARCHITECTURE.md"}
    if directory.exists():
        candidates.update(path.relative_to(project).as_posix() for path in directory.rglob("*.md"))
    for note in sorted(candidates):
        path = note_path(project, note)
        if not path.exists():
            if note in notes:
                findings.append(finding("project", "knowledge.note_missing", "warning", note, "Baselined note is missing; review its evidence registration"))
            continue
        current = sources(project, note)
        recorded = notes.get(note, {})
        for source in sorted(set(current) | set(recorded)):
            if source not in current:
                state, identifier, message = "warning", "knowledge.reference_removed", "Source citation removed: "
            elif current[source] is None:
                state, identifier, message = "warning", "knowledge.source_missing", "Cited source missing: "
            elif source not in recorded:
                state, identifier, message = "unknown", "knowledge.unbaselined", "Source state has not been recorded: "
            elif current[source] != recorded[source]:
                state, identifier, message = "warning", "knowledge.stale", "Potentially stale note; cited source changed: "
            else:
                continue
            findings.append(finding("project", identifier, state, note, message + source))
    return findings


def global_findings():
    if not os.environ.get("HOME"):
        raise ValueError("Global checks require HOME; use --project-only for portable validation")
    import managed_links as shared
    findings = []
    records = shared.load()
    instructions = [("AGENTS.md", True), (".codex/AGENTS.md", (shared.HOME / ".codex").exists()),
                    (".claude/CLAUDE.md", (shared.HOME / ".claude").exists()),
                    (".gemini/GEMINI.md", (shared.HOME / ".gemini").exists()),
                    (".config/opencode/AGENTS.md", (shared.HOME / ".config/opencode").exists())]
    for relative, configured in instructions:
        path = shared.safe(shared.HOME / relative)
        if not configured:
            findings.append(finding("global", "agent.unconfigured", "optional", path, "Agent configuration is absent"))
            continue
        if path.is_symlink() or not path.is_file():
            findings.append(finding("global", "instructions.missing", "failure", path, "Missing or unsafe shared instructions; review install --dry-run"))
            continue
        text = path.read_text()
        pairs = (("# >>> contextrivet managed >>>", "# <<< contextrivet managed <<<"),
                 ("# >>> dev-agent-config managed >>>", "# <<< dev-agent-config managed <<<"))
        present = [(start, end) for start, end in pairs if start in text.splitlines() or end in text.splitlines()]
        valid = len(present) == 1 and all(text.splitlines().count(marker) == 1 for marker in present[0]) and text.index(present[0][0]) < text.index(present[0][1])
        if not valid:
            findings.append(finding("global", "instructions.unmanaged", "warning", path, "No valid ContextRivet block; custom instructions preserved"))
        elif text.partition(present[0][0])[2].partition(present[0][1])[0].strip() != (p.ROOT / "AGENTS.md").read_text().strip():
            findings.append(finding("global", "instructions.drift", "warning", path, "Shared engineering guidance differs; review install --dry-run"))
    for target, origin in shared.destinations().items():
        path = shared.safe(target)
        relative = path.relative_to(shared.HOME).as_posix()
        adapter = next((name for name in (".claude", ".gemini", ".config/opencode", ".cline") if relative.startswith(name + "/")), None)
        cline = (shared.HOME / ".cline").is_dir() or (shared.HOME / "Documents/Cline").is_dir()
        required = (target in records or adapter is not None and (shared.HOME / adapter).is_dir()
                    or relative in (".agents/skills/ponytail", ".agents/instructions/code-intelligence.md")
                    or relative == ".agents/AGENTS.md" and cline)
        if not path.exists() and not path.is_symlink() and not required:
            continue
        if path.is_symlink() and not path.exists():
            state, identifier, message = "failure", "asset.broken_link", "Dangling link; run repair --dry-run"
        elif not path.exists():
            state, identifier, message = "failure", "asset.missing", "Missing managed integration asset; run repair --dry-run"
        elif path.is_file() and not path.stat().st_size or path.is_dir() and (not (path / "SKILL.md").is_file() or not (path / "SKILL.md").stat().st_size):
            state, identifier, message = "failure", "asset.incomplete", "Integration asset is empty or lacks SKILL.md; restore its source or review custom content"
        elif not shared.owned(target, records):
            state, identifier, message = "warning", "asset.unmanaged", "Custom asset or unproven ownership; preserved"
        elif os.readlink(path) != origin:
            state, identifier, message = "warning", "asset.obsolete", "Owned link targets an older checkout; run repair --dry-run"
        else:
            continue
        findings.append(finding("global", identifier, state, path, message))
    # Only observe configuration files; never invoke an agent, indexer, or service.
    state_home = Path(os.environ.get("XDG_STATE_HOME", str(shared.HOME / ".local/state")))
    for namespace in ("contextrivet", "dev-agent-config"):
        cbm = state_home / namespace / "tools/codebase-memory-mcp"
        # Metadata presence is observable; it cannot establish a running MCP or
        # a current index. Avoid reading credentials or invoking optional tools.
        findings.append(finding("global", "intelligence.runtime", "unknown" if cbm.exists() else "optional", cbm,
                                "Integration metadata present; runtime/index freshness unverified" if cbm.exists() else "Optional intelligence integration is unconfigured"))
        for name in ("codex-mcp.tsv", "opencode-mcp.tsv", "antigravity-mcp.tsv"):
            if (cbm / name).is_file():
                findings.append(finding("global", "intelligence.configured", "unknown", cbm / name,
                                        "Integration ownership record present; actual agent connection is unverified"))
    return findings


def project_findings(project, portable=False):
    p.select_namespace(project, "status")
    config, issues = p.readiness_issues(project)
    findings = []
    for issue in issues:
        identifier = "project.route" if "route:" in issue else "project.readiness" if any(value in issue for value in ("Status:", "placeholder", "section")) else "project.asset"
        findings.append(finding("project", identifier, "failure", project, issue))
    findings.extend(reference_findings(project, config))
    for relative, record in p.load_ownership(project).items():
        if portable and relative == ".git/hooks/pre-commit":
            findings.append(finding("project", "automation.local", "unknown", relative, "Developer-local hook installation is not checked in portable mode"))
            continue
        path = p.safe_path(project, relative)
        if not path.exists():
            if relative in p.automation_paths():
                findings.append(finding("project", "automation.disabled", "optional", relative, "Optional generated integration file was removed; regenerate explicitly to enable it"))
            else:
                findings.append(finding("project", "ownership.missing", "failure", relative, "Missing owned file; review project repair --dry-run"))
        elif p.digest(path.read_bytes()) != record["after_sha256"]:
            findings.append(finding("project", "ownership.modified", "warning", relative, "File differs from installed bytes; project customization may be intentional"))
    findings.extend(drift_findings(project))
    findings.append(finding("project", "intelligence.index", "unknown", project,
                            "Optional index availability/freshness is unverified; absence does not fail project health"))
    return findings


def health(args):
    findings = []
    for scope, enabled, check in (("global", not args.project_only, global_findings),
                                  ("project", not args.global_only, lambda: project_findings(Path(args.project).resolve(strict=True), portable=args.project_only))):
        if enabled:
            try:
                findings.extend(check())
            except (OSError, ValueError) as error:
                findings.append(finding(scope, scope + ".invalid", "failure", args.project if scope == "project" else os.environ.get("HOME", ""), str(error)))
    findings.append(finding("runtime", "activation.unverified", "unknown", "", "Agent loading, skill activation, and semantic accuracy require direct review"))
    overall = result(findings)
    report = {"schema_version": 1, "overall": overall, "scopes": {
        scope: {"result": result([f for f in findings if f["scope"] == scope]) if enabled else "skipped"}
        for scope, enabled in (("global", not args.project_only), ("project", not args.global_only))}, "findings": findings}
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for scope in ("global", "project", "runtime"):
            print(scope.capitalize() + ": " + report["scopes"].get(scope, {"result": "unverified"})["result"])
            for item in findings:
                if item["scope"] == scope:
                    print("  {} [{}] {}{}".format(item["state"].upper(), item["id"], item["path"] + ": " if item["path"] else "", item["message"]))
        print("Overall: " + overall + " (structure only)")
    return 1 if overall == "fail" else 0


def apply_changes(project, changes, action, identifier=None):
    identifier = identifier or p.backup_id()
    p.save_transaction(project, identifier, changes, action)
    originals = {relative: (p.safe_path(project, relative).read_bytes(), stat.S_IMODE(p.safe_path(project, relative).stat().st_mode))
                 if p.safe_path(project, relative).exists() else (None, None) for relative in changes}
    try:
        for relative, (content, mode) in changes.items():
            p.atomic_write(p.safe_path(project, relative), content, mode)
    except OSError:
        for relative, (content, mode) in originals.items():
            path = p.safe_path(project, relative)
            if content is None:
                if path.exists():
                    path.unlink()
            else:
                p.atomic_write(path, content, mode)
        raise
    print("Recovery: contextrivet project restore --backup " + identifier + " --dry-run")


def repair(project, args):
    config = p.load_config(project)
    if config is None:
        raise ValueError("Project not initialized; repair requires saved configuration and ownership")
    owned = p.load_ownership(project)
    intended = dict(p.scaffold(config), **p.instruction_files(config))
    changes = {}
    ambiguous = []
    for relative, record in owned.items():
        if relative in p.automation_paths():
            continue
        path = p.safe_path(project, relative)
        if path.exists():
            continue
        content = intended.get(relative)
        if relative in p.instruction_files(config) and content is not None:
            content = p.START + "\n" + content.rstrip() + "\n" + p.END + "\n"
        if content is None or p.digest(content.encode()) != record["after_sha256"]:
            ambiguous.append(relative)
            continue
        changes[relative] = (content.encode(), None)
    for relative in ambiguous:
        print("AMBIGUOUS missing owned file: {}. Installed bytes are unavailable locally; recover from a reviewed backup/version. No guessed content will be written.".format(relative))
    for relative in changes:
        print("WOULD_RESTORE " + relative)
    if changes and args.apply:
        apply_changes(project, changes, "repair")
        print("Repaired owned missing scaffold assets.")
    elif not changes:
        print("UNCHANGED: no safe mechanical repairs.")
    else:
        print("Dry run: no files changed. Pass --apply to repair.")
    return 1 if ambiguous else 0


def baseline(project, args):
    if p.load_config(project) is None:
        raise ValueError("Initialize the project before recording evidence")
    notes = evidence(project)
    current = sources(project, args.note)
    if not current or any(value is None for value in current.values()):
        raise ValueError("Note requires existing project-relative sources, one per line: Source: `path`")
    notes[args.note] = current
    relative = evidence_path()
    content = (json.dumps({"version": 1, "notes": notes}, indent=2, sort_keys=True) + "\n").encode()
    path = p.safe_path(project, relative)
    if path.exists() and path.read_bytes() == content:
        print("UNCHANGED: recorded source bytes match. Factual accuracy remains unverified.")
        return 0
    owned = p.load_ownership(project)
    identifier = p.backup_id()
    if relative not in owned:
        owned[relative] = {"before_sha256": p.digest(path.read_bytes()) if path.exists() else None,
                           "before_mode": stat.S_IMODE(path.stat().st_mode) if path.exists() else None,
                           "backup": identifier if path.exists() else None}
    owned[relative]["after_sha256"] = p.digest(content)
    changes = {relative: (content, None), p.OWNERSHIP: ((json.dumps({"version": 1, "files": owned}, indent=2, sort_keys=True) + "\n").encode(), None)}
    # Use the same ID for ownership's original backup and the actual transaction.
    for target in changes:
        p.safe_path(project, target)
    print("WOULD_RECORD source fingerprints for " + args.note + "; this does not confirm factual accuracy.")
    if args.dry_run:
        return 0
    if not p.confirm_action("Record the displayed source state?", args.yes):
        return 1
    apply_changes(project, changes, "baseline", identifier=identifier)
    return 0


def git(project, *args):
    completed = subprocess.run(["git", "-C", str(project), *args], text=True, capture_output=True)
    if completed.returncode:
        raise ValueError("Git metadata unavailable: " + completed.stderr.strip())
    return completed.stdout.strip()


def automate(project, args):
    if not (args.hook or args.ci) or args.local and not args.hook:
        raise ValueError("Choose --hook and/or --ci; --local only applies to the local hook")
    if p.load_config(project) is None:
        raise ValueError("Initialize the project before enabling automatic checks")
    owned = p.load_ownership(project)
    changes = {}
    if args.hook:
        configured = subprocess.run(["git", "-C", str(project), "config", "--get", "core.hooksPath"], capture_output=True, text=True)
        if configured.returncode not in (0, 1):
            raise ValueError("Cannot inspect core.hooksPath")
        if configured.returncode == 0:
            raise ValueError("core.hooksPath is configured ({}). Integrate `contextrivet health --project-only` into that hook manually; no hook is overwritten.".format(configured.stdout.strip()))
        hook = Path(git(project, "rev-parse", "--git-path", "hooks/pre-commit"))
        hook = hook if hook.is_absolute() else project / hook
        # Linked worktrees can have hooks outside the selected root; require manual integration.
        hook = Path(os.path.abspath(hook))
        if project not in hook.parents:
            raise ValueError("Hook lives outside project (linked worktree); integrate health manually: " + str(hook))
        relative = hook.relative_to(project).as_posix()
        if relative != ".git/hooks/pre-commit":
            raise ValueError("Nonstandard Git hook path; integrate health manually: " + str(hook))
        p.safe_path(project, relative)
        scope = "" if args.local else " --project-only"
        changes[hook] = ("#!/bin/sh\n# ContextRivet opt-in checks; remove this file to disable.\n"
                         "[ \"${CONTEXTRIVET_SKIP_CHECKS:-0}\" = 1 ] && exit 0\n"
                         "exec " + shlex.quote(str(p.ROOT / "contextrivet")) + " health" + scope + "\n").encode(), 0o755
    if args.ci:
        path = p.safe_path(project, ".github/workflows/contextrivet.yml")
        # Vendor the current validator so CI works before a release and without a
        # developer checkout/HOME or a network install of ContextRivet.
        checker = Path(p.STATE).parent / "checker"
        for relative in p.checker_sources():
            source = p.ROOT / relative
            destination = p.safe_path(project, (checker / source.relative_to(p.ROOT)).as_posix())
            changes[destination] = source.read_bytes(), 0o644
        changes[path] = ("# ContextRivet opt-in checks; remove this file to disable.\n"
                         "name: ContextRivet health\non: [push, pull_request, workflow_dispatch]\n"
                         "permissions:\n  contents: read\n"
                         "jobs:\n  health:\n    runs-on: ubuntu-latest\n    steps:\n"
                         "      - uses: actions/checkout@v4\n"
                         "      - run: python3 " + (checker / "scripts/maintenance.py").as_posix() + " --project-only --json\n").encode(), 0o644
    for path, (content, _mode) in list(changes.items()):
        if path.exists():
            if path.read_bytes() == content:
                del changes[path]
                continue
            raise ValueError("Existing hook/workflow preserved. Integrate health manually: " + str(path))
    for path in changes:
        print("WOULD_CREATE " + str(path))
    if not changes:
        print("UNCHANGED: requested automation files already match; existing hooks were preserved.")
        return 0
    identifier = p.backup_id()
    for path, (content, _mode) in changes.items():
        relative = path.relative_to(project).as_posix()
        if relative not in owned:
            owned[relative] = {"before_sha256": None, "before_mode": None, "backup": None}
        owned[relative]["after_sha256"] = p.digest(content)
        p.backup_path(project, identifier, relative)
    ownership = p.safe_path(project, p.OWNERSHIP)
    previous = ownership.read_bytes() if ownership.exists() else None
    previous_mode = stat.S_IMODE(ownership.stat().st_mode) if ownership.exists() else None
    metadata = (json.dumps({"version": 1, "files": owned}, indent=2, sort_keys=True) + "\n").encode()
    transaction = {path.relative_to(project).as_posix(): value for path, value in changes.items()}
    transaction[p.OWNERSHIP] = (metadata, None)
    p.validate_records(owned, p.allowed_paths() - {p.OWNERSHIP})
    p.backup_path(project, identifier, p.OWNERSHIP)
    if args.apply:
        p.save_transaction(project, identifier, transaction, "automate")
        created = []
        try:
            for path, (content, mode) in changes.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as stream:
                    created.append(path)
                    stream.write(content)
                path.chmod(mode)
            p.atomic_write(ownership, metadata)
        except OSError:
            for path in created:
                path.unlink()
            if previous is None:
                if ownership.exists():
                    ownership.unlink()
            elif not ownership.exists() or ownership.read_bytes() != previous or stat.S_IMODE(ownership.stat().st_mode) != previous_mode:
                p.atomic_write(ownership, previous, previous_mode)
            raise
        print("Automatic checks enabled. Bypass local checks with CONTEXTRIVET_SKIP_CHECKS=1 or git commit --no-verify; remove generated files to disable.")
        print("Recovery: contextrivet project restore --backup " + identifier + " --dry-run")
    else:
        print("Dry run: no files changed. Pass --apply to enable checks.")
    return 0


def main():
    parser = argparse.ArgumentParser(prog="contextrivet health", description="Read-only structural health. Never runs project scripts, agents, services, or network requests. Exit 0: no failures (warnings allowed); 1: failures; 2: invalid CLI usage.")
    parser.add_argument("--project", default=".")
    parser.add_argument("--json", action="store_true", help="versioned JSON (schema_version: 1)")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--project-only", action="store_true", help="portable checks without developer HOME configuration")
    scope.add_argument("--global-only", action="store_true", help="local developer setup checks only")
    return health(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
