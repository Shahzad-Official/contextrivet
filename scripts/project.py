#!/usr/bin/env python3
"""Create portable project guidance without running project code or global setup."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import urlopen
import zipfile


ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates/project"
STATE = ".agents/contextrivet/project.json"
OWNERSHIP = ".agents/contextrivet/installed.json"
BACKUPS = ".agents/contextrivet/backups"
START = "# >>> contextrivet project >>>"
END = "# <<< contextrivet project <<<"
LEGACY_START = "# >>> dev-agent-config project >>>"
LEGACY_END = "# <<< dev-agent-config project <<<"
CANONICALS = ("AGENTS.md", "CLAUDE.md", "GEMINI.md", ".agents/AGENTS.md")
ENTRIES = {
    "codex": "AGENTS.md",
    "claude": "CLAUDE.md",
    "gemini": "GEMINI.md",
    "opencode": "AGENTS.md",
    "cline": ".clinerules/00-contextrivet.md",
    "antigravity": "GEMINI.md",
}
STACKS = ("nestjs", "nextjs", "flutter")
LEGACY_STACKS = ("generic", "backend", "react")
SECTIONS = {
    ".agents/PROJECT.md": (
        "Purpose", "Scope", "Stack", "Constraints", "Verification",
    ),
    ".agents/ARCHITECTURE.md": (
        "System overview", "Feature boundaries", "Dependency direction",
        "Data flow and contracts", "Decisions and tradeoffs", "Evidence and review",
    ),
}


class ProjectHelpParser(argparse.ArgumentParser):
    def format_help(self):
        text = super().format_help()
        force = os.environ.get("FORCE_COLOR")
        color = "NO_COLOR" not in os.environ and force != "0" and (
            force in ("1", "2", "3") or (sys.stdout.isatty() and os.environ.get("TERM") != "dumb")
        )
        title = "  contextrivet / " + self.prog.partition(" ")[2]
        if not color:
            return title + "\n\n" + text
        lines = []
        for line in text.splitlines():
            if line.startswith("usage:"):
                line = "\033[96m" + line + "\033[0m"
            elif line and not line.startswith(" ") and line.endswith(":"):
                line = "\033[1;95m" + line + "\033[0m"
            lines.append(line)
        return "\033[1;96m" + title + "\033[0m\n\n" + "\n".join(lines) + "\n"


def select_namespace(project, action, identifier=None):
    global STATE, OWNERSHIP, BACKUPS
    namespaces = ("contextrivet", "dev-agent-config")
    found = []
    for name in namespaces:
        if action == "restore":
            if not isinstance(identifier, str) or not re.fullmatch(r"\d{8}-\d{6}(?:-\d{6})?-\d+", identifier):
                raise ValueError("Invalid backup ID; use project backups to list available IDs")
            paths = [".agents/{}/backups/{}".format(name, identifier)]
        else:
            paths = [".agents/{}/{}".format(name, filename) for filename in ("project.json", "installed.json")]
        if any(safe_path(project, path, directory=action == "restore").exists() for path in paths):
            found.append(name)
    if len(found) > 1:
        raise ValueError("Both contextrivet and dev-agent-config state match; reconcile them before changing this project")
    name = found[0] if found else "contextrivet"
    STATE = ".agents/" + name + "/project.json"
    OWNERSHIP = ".agents/" + name + "/installed.json"
    BACKUPS = ".agents/" + name + "/backups"
    ENTRIES["cline"] = ".clinerules/00-" + name + ".md"


def safe_path(project, relative, directory=False):
    """Refuse links and unexpected types in every managed descendant path."""
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or ".." in parts:
        raise ValueError("Invalid project-relative path: " + relative)
    current = project
    for index, part in enumerate(parts):
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ValueError("Refusing symlinked project path: " + str(current))
        expected = stat.S_ISREG if index == len(parts) - 1 and not directory else stat.S_ISDIR
        if not expected(mode):
            raise ValueError("Unexpected project path type: " + str(current))
    return current


def load_config(project):
    path = safe_path(project, STATE)
    if not path.exists():
        return None
    config = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(config, dict)
        or config.get("version") != 1
        or config.get("canonical") not in CANONICALS
        or config.get("stack") not in STACKS + LEGACY_STACKS
        or not isinstance(config.get("skills"), bool)
        or not isinstance(config.get("agents"), list)
        or any(not isinstance(agent, str) or agent not in ENTRIES for agent in config["agents"])
    ):
        raise ValueError("Invalid project setup metadata: " + str(path))
    return config


def detect_stack(project):
    detected = set()
    package = safe_path(project, "package.json")
    if package.exists():
        manifest = json.loads(package.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("package.json must contain an object; choose --stack explicitly")
        dependencies = {}
        for field in ("dependencies", "devDependencies"):
            values = manifest.get(field, {})
            if not isinstance(values, dict):
                raise ValueError("Invalid package.json dependency map; choose --stack explicitly")
            dependencies.update(values)
        if "@nestjs/core" in dependencies:
            detected.add("nestjs")
        if "next" in dependencies:
            detected.add("nextjs")
    pubspec = safe_path(project, "pubspec.yaml")
    if pubspec.exists() and re.search(r"^\s+sdk:\s*flutter\s*(?:#.*)?$", pubspec.read_text(encoding="utf-8"), re.MULTILINE):
        detected.add("flutter")
    if len(detected) != 1:
        raise ValueError("Choose --stack nestjs, nextjs, or flutter; the project stack is missing or ambiguous")
    return detected.pop()


def stack_skills(stack):
    catalog = json.loads((ROOT / "skills/stacks.json").read_text(encoding="utf-8"))
    if not isinstance(catalog, dict) or catalog.get("version") != 1 or not isinstance(catalog.get("stacks"), dict):
        raise ValueError("Invalid skills/stacks.json catalog")
    if set(catalog["stacks"]) != set(STACKS):
        raise ValueError("Skill catalog must define nestjs, nextjs, and flutter")
    for entries in catalog["stacks"].values():
        if not isinstance(entries, list):
            raise ValueError("Each stack skill list must be an array")
        names = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"name", "description", "github_url"}:
                raise ValueError("Each skill reference needs name, description, and github_url")
            name, description, url = (entry[field] for field in ("name", "description", "github_url"))
            if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or name in names:
                raise ValueError("Skill names must be unique lowercase identifiers")
            if not isinstance(description, str) or not description.strip() or any(char in description for char in "\r\n"):
                raise ValueError("Skill descriptions must be nonempty single lines")
            if not isinstance(url, str) or any(char.isspace() or char in "<>" for char in url):
                raise ValueError("Invalid GitHub skill URL")
            parsed = urlsplit(url)
            if parsed.scheme != "https" or parsed.netloc != "github.com" or len(parsed.path.strip("/").split("/")) < 2 or parsed.query or parsed.fragment:
                raise ValueError("Skill sources must be HTTPS github.com repository URLs")
            names.add(name)
    return catalog["stacks"].get(stack, [])


def skill_index(stack):
    entries = stack_skills(stack)
    lines = ["# Project skills", "", "Bundled optional skill: `.agents/skills/ponytail/SKILL.md`.", "",
             "Stack profile: " + stack, "",
             "GitHub references below are not downloaded or installed by init.",
             "Install selected skills with `contextrivet project skills install --names <name,...>`.",
             "Use locally installed skills when relevant; a catalog entry does not prove activation.", ""]
    lines.extend("- {}: {} — <{}>".format(entry["name"], entry["description"], entry["github_url"]) for entry in entries)
    if not entries:
        lines.append("No custom GitHub skills are configured for this profile yet.")
    return "\n".join(lines) + "\n"


def skill_source(entry):
    """Only install reviewed GitHub directories pinned to a full commit hash."""
    if entry["name"] == "ponytail":
        raise ValueError("ponytail is reserved for the bundled skill")
    parts = urlsplit(entry["github_url"]).path.strip("/").split("/")
    if (len(parts) < 5 or parts[2] != "tree" or not re.fullmatch(r"[0-9a-f]{40}", parts[3])
            or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) or part in (".", "..") for part in parts)):
        raise ValueError("Install requires https://github.com/<owner>/<repo>/tree/<40-character-commit>/<skill-path>: " + entry["name"])
    return "https://codeload.github.com/{}/{}/zip/{}".format(*parts[:2], parts[3]), "/".join(parts[4:])


def remote_skill_path(relative):
    parts = relative.split("/") if isinstance(relative, str) else []
    return (len(parts) >= 4 and parts[:2] == [".agents", "skills"]
            and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", parts[2]) is not None
            and all(part not in ("", ".", "..", ".git") and "\\" not in part
                    and not any(ord(char) < 32 or ord(char) == 127 for char in part) for part in parts))


def fetch_skill(entry, archives):
    url, subdirectory = skill_source(entry)
    if url not in archives:
        print("FETCH " + url)
        with urlopen(url, timeout=30) as response:
            data = response.read(32 * 1024 * 1024 + 1)
        if len(data) > 32 * 1024 * 1024:
            raise ValueError("Skill archive exceeds 32 MiB")
        archives[url] = data
    files = {}
    try:
        with zipfile.ZipFile(io.BytesIO(archives[url])) as archive:
            members = archive.infolist()
            if not members:
                raise ValueError("Empty skill archive")
            root = members[0].filename.split("/")[0] + "/"
            prefix = root + subdirectory + "/"
            total = 0
            license_member = None
            for member in members:
                if member.filename in (root + name for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")):
                    license_member = member
                if not member.filename.startswith(prefix) or member.is_dir():
                    continue
                relative = member.filename[len(prefix):]
                target = ".agents/skills/" + entry["name"] + "/" + relative
                if not remote_skill_path(target) or relative == ".contextrivet-source.json" or target in files:
                    raise ValueError("Unsafe or duplicate skill archive path: " + member.filename)
                mode = member.external_attr >> 16
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                    raise ValueError("Non-regular file in skill archive: " + member.filename)
                total += member.file_size
                if member.file_size > 4 * 1024 * 1024 or total > 32 * 1024 * 1024 or len(files) >= 1000:
                    raise ValueError("Skill content exceeds installation limits")
                files[target] = archive.read(member)
            destination = ".agents/skills/" + entry["name"] + "/"
            if destination + "SKILL.md" not in files:
                raise ValueError("Missing SKILL.md in source: " + entry["name"])
            content = files[destination + "SKILL.md"].decode("utf-8")
            front = re.match(r"\A---\s*\n(.*?)\n---(?:\s|$)", content, re.DOTALL)
            if not front or not re.search(r"^name:\s*['\"]?" + re.escape(entry["name"]) + r"['\"]?\s*$", front[1], re.MULTILINE):
                raise ValueError("Skill metadata name does not match catalog: " + entry["name"])
            if not any(path[len(destination):] in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING") for path in files):
                if license_member is None or license_member.file_size > 1024 * 1024 or stat.S_IFMT(license_member.external_attr >> 16) not in (0, stat.S_IFREG):
                    raise ValueError("Missing or invalid source license: " + entry["name"])
                files[destination + "LICENSE"] = archive.read(license_member)
    except (zipfile.BadZipFile, RuntimeError) as error:
        raise ValueError("Invalid skill archive: " + str(error)) from error
    files[destination + ".contextrivet-source.json"] = (json.dumps({
        "name": entry["name"], "github_url": entry["github_url"],
        "commit": urlsplit(entry["github_url"]).path.split("/")[4],
    }, indent=2, sort_keys=True) + "\n").encode()
    return files


def install_skills(project, args):
    config = load_config(project)
    if config is None:
        raise ValueError("Run project init before installing project skills")
    if args.stack and args.stack != config["stack"]:
        raise ValueError("Skill stack must match this project's saved stack")
    entries = stack_skills(config["stack"])
    names = [name.strip() for name in args.names.split(",")] if args.names else []
    if args.all == bool(names) or (names and (len(set(names)) != len(names) or any(not name for name in names))):
        raise ValueError("Choose --names <name,...> or --all")
    unknown = set(names) - {entry["name"] for entry in entries}
    if unknown:
        raise ValueError("Unknown skills for this stack: " + ", ".join(sorted(unknown)))
    selected = [entry for entry in entries if args.all or entry["name"] in names]
    if not selected:
        raise ValueError("No remote skills configured for this stack")
    owned = load_ownership(project)
    for entry in selected:
        skill_source(entry)
        safe_path(project, ".agents/skills/" + entry["name"], directory=True)
        print("SELECTED {}: {}".format(entry["name"], entry["github_url"]))
    if args.dry_run:
        print("Dry run: would fetch selected skill folders into .agents/skills/. No network requests or project changes; content/conflicts unchecked.")
        return 0
    incoming = {}
    archives = {}
    for entry in selected:
        incoming.update(fetch_skill(entry, archives))
    changes = {}
    for relative, content in incoming.items():
        path = safe_path(project, relative)
        if path.exists():
            current = path.read_bytes()
            if current == content:
                continue
            if relative not in owned or digest(current) != owned[relative]["after_sha256"]:
                raise ValueError("Existing/custom skill file preserved; compare it before retrying: " + relative)
        changes[relative] = (content, None)
    # Remove obsolete files from a previously installed version, restoring any originals.
    prefixes = tuple(".agents/skills/" + entry["name"] + "/" for entry in selected)
    for relative in list(owned):
        if relative.startswith(prefixes) and relative not in incoming:
            path = safe_path(project, relative)
            if path.exists() and digest(path.read_bytes()) != owned[relative]["after_sha256"]:
                raise ValueError("Modified obsolete skill file preserved: " + relative)
            record = owned.pop(relative)
            changes[relative] = (read_original(project, record.get("backup"), relative, record), record["before_mode"])
    if not changes:
        print("UNCHANGED: selected skill files already match the pinned sources.")
        return 0
    identifier = backup_id()
    for relative, (content, _mode) in changes.items():
        path = safe_path(project, relative)
        if relative in incoming:
            if relative not in owned:
                owned[relative] = {
                    "before_sha256": digest(path.read_bytes()) if path.exists() else None,
                    "before_mode": stat.S_IMODE(path.stat().st_mode) if path.exists() else None,
                    "backup": identifier if path.exists() else None,
                }
            owned[relative]["after_sha256"] = digest(content)
        print(("WOULD_REMOVE " if content is None else "WOULD_WRITE ") + relative)
    changes[OWNERSHIP] = ((json.dumps({"version": 1, "files": owned}, indent=2, sort_keys=True) + "\n").encode(), None)
    if not confirm_action("Install/update these project skills?", args.yes):
        return 1
    save_transaction(project, identifier, changes, "skills-install")
    for relative, (content, mode) in changes.items():
        path = safe_path(project, relative)
        if content is None:
            if path.exists():
                path.unlink()
        else:
            atomic_write(path, content, mode)
    print("Installed selected skills in .agents/skills/. No skill scripts executed. Agent discovery/activation requires verification.")
    return 0


def scaffold(config, include_references=True):
    files = {}
    for source in sorted(TEMPLATES.rglob("*.md")):
        relative = source.relative_to(TEMPLATES).as_posix()
        if relative == "canonical.md" or relative.startswith(("stacks/", "legacy-stacks/")):
            continue
        target = ".agents/templates/feature.md" if relative == "feature.md" else ".agents/" + relative
        files[target] = source.read_text(encoding="utf-8").replace("{{STACK}}", config["stack"])
    files[".agents/instructions/stack.md"] = (
        TEMPLATES / ("legacy-stacks" if config["stack"] in LEGACY_STACKS else "stacks") / (config["stack"] + ".md")
    ).read_text(encoding="utf-8")
    files[".agents/instructions/code-intelligence.md"] = (
        ROOT / "instructions/code-intelligence.md"
    ).read_text(encoding="utf-8")
    if config["skills"]:
        files[".agents/skills/README.md"] = skill_index(config["stack"]) if include_references else ""
        for name in ("SKILL.md", "SOURCE.md"):
            files[".agents/skills/ponytail/" + name] = (
                ROOT / "skills/ponytail" / name
            ).read_text(encoding="utf-8")
    return files


def instruction_files(config):
    guidance = (
        "Read `.agents/skills/README.md` for the selected stack's skill references. "
        "For implementation or review, consider `.agents/skills/ponytail/SKILL.md`. "
        "Read relevant skills only; native skill discovery varies by agent. A file "
        "reference alone does not prove skill activation."
        if config["skills"] else
        "Use relevant existing project skills when available; do not assume "
        "a file reference automatically activates a skill."
    )
    canonical = config["canonical"]
    files = {canonical: (TEMPLATES / "canonical.md").read_text(encoding="utf-8").replace(
        "{{SKILL_GUIDANCE}}", guidance
    )}
    for agent in config["agents"]:
        entry = ENTRIES[agent]
        if entry != canonical:
            files[entry] = (
                "# Project instructions\n\n"
                "Before any project work, read `{}` (relative to the project root)\n"
                "and follow its setup gate and instructions. It is the canonical\n"
                "project rules file. Complete required setup before implementation.\n"
            ).format(canonical)
    return files


def check_override(project, config):
    if "codex" in config["agents"]:
        path = safe_path(project, "AGENTS.override.md")
        if path.exists() and path.read_text(encoding="utf-8").strip():
            raise ValueError(
                "AGENTS.override.md shadows Codex's AGENTS.md. Reconcile it manually "
                "with the canonical rules before selecting Codex."
            )


def managed_block(text, relative):
    lines = text.splitlines()
    pairs = [(start, end) for start, end in ((START, END), (LEGACY_START, LEGACY_END))
             if start in lines or end in lines]
    if not pairs:
        return None
    if len(pairs) != 1:
        raise ValueError("Ambiguous project instruction markers: " + relative)
    start, end = pairs[0]
    starts, ends = lines.count(start), lines.count(end)
    if starts == ends == 0:
        return None
    if starts != 1 or ends != 1 or lines.index(start) >= lines.index(end):
        raise ValueError("Malformed project instruction markers: " + relative)
    return "\n".join(lines[lines.index(start) + 1:lines.index(end)])


def atomic_write(path, content, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if mode is None:
        mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    descriptor, temporary = tempfile.mkstemp(prefix=".contextrivet-", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def digest(content):
    return hashlib.sha256(content).hexdigest() if content is not None else None


def backup_id():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + "-" + str(os.getpid())


def backup_path(project, identifier, relative):
    if not isinstance(identifier, str) or not re.fullmatch(r"\d{8}-\d{6}(?:-\d{6})?-\d+", identifier):
        raise ValueError("Invalid backup ID; use project backups to list available IDs")
    return safe_path(project, BACKUPS + "/" + identifier + "/" + relative)


def allowed_paths():
    compatible = {".agents/{}/{}".format(name, filename) for name in ("contextrivet", "dev-agent-config")
                  for filename in ("project.json", "installed.json")}
    compatible.update(".clinerules/00-" + name + ".md" for name in ("contextrivet", "dev-agent-config"))
    return set(scaffold({"stack": "nextjs", "skills": True}, include_references=False)) | set(CANONICALS) | set(ENTRIES.values()) | compatible


def validate_records(records, allowed):
    if not isinstance(records, dict) or any(path not in allowed and not remote_skill_path(path) for path in records):
        raise ValueError("Invalid managed paths in project history")
    for record in records.values():
        if not isinstance(record, dict):
            raise ValueError("Invalid project history record")
        for field in ("before_sha256", "after_sha256"):
            value = record.get(field)
            if field not in record or (value is not None and (not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value))):
                raise ValueError("Invalid project history digest")
        mode = record.get("before_mode")
        if (record["before_sha256"] is None and mode is not None) or (
            record["before_sha256"] is not None and (type(mode) is not int or not 0 <= mode <= 0o777)
        ):
            raise ValueError("Invalid project history permissions")


def load_ownership(project):
    path = safe_path(project, OWNERSHIP)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Invalid project ownership metadata")
    records = data.get("files")
    validate_records(records, allowed_paths() - {OWNERSHIP})
    for relative, record in records.items():
        if record["before_sha256"] is not None:
            backup_path(project, record.get("backup"), relative)
        if record["after_sha256"] is None:
            raise ValueError("Invalid installed-file digest")
    return records


def read_original(project, identifier, relative, record):
    if record["before_sha256"] is None:
        return None
    path = backup_path(project, identifier, relative)
    content = path.read_bytes()
    if digest(content) != record["before_sha256"]:
        raise ValueError("Backup content changed: " + str(path))
    return content


def save_transaction(project, identifier, changes, action):
    """Save originals and a complete manifest before touching project files."""
    records = {}
    originals = {}
    for relative, (content, _mode) in changes.items():
        path = safe_path(project, relative)
        before = path.read_bytes() if path.exists() else None
        mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
        records[relative] = {"before_sha256": digest(before), "before_mode": mode,
                             "after_sha256": digest(content)}
        if before is not None:
            originals[relative] = before
        backup_path(project, identifier, relative)
    manifest_path = backup_path(project, identifier, "manifest.json")
    if manifest_path.exists():
        raise ValueError("Backup already exists: " + identifier)
    validate_records(records, allowed_paths())
    for relative, content in originals.items():
        atomic_write(backup_path(project, identifier, relative), content, mode=0o600)
    manifest = {"version": 1, "action": action, "files": records}
    atomic_write(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(), mode=0o600)
    print("Recovery/original files saved under: " + str(project / BACKUPS / identifier))


def confirm_action(prompt, assume_yes):
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print("Consent required: no files changed. Review --dry-run, then rerun with --yes only if you approve.")
        return False
    try:
        answer = input(prompt + " [y/N] ")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled: no files changed.")
        return False
    if answer.strip().lower() not in ("y", "yes"):
        print("Cancelled: no files changed.")
        return False
    return True


def confirm_existing_setup(project, assume_yes, dry_run=False):
    names = {
        "agents.md", "agents.override.md", "claude.md", "gemini.md",
        ".agents", ".agent", ".claude", ".gemini", ".opencode", ".cline", ".clinerules",
    }
    existing = sorted(path.name for path in project.iterdir() if path.name.casefold() in names)
    if not existing:
        return True
    print("Existing agent setup detected: " + ", ".join(existing))
    print("This plan adds the scaffold alongside existing guidance; it does not reconcile different workflows.")
    if dry_run:
        return True
    if assume_yes:
        print("Consent supplied with --yes for the displayed additive setup.")
        return True
    return confirm_action("Apply this plan to the existing agent setup?", False)


def initialize(project, args):
    previous = load_config(project)
    owned = load_ownership(project)
    canonical = args.canonical or (previous["canonical"] if previous else "AGENTS.md")
    stack = args.stack or (previous["stack"] if previous else detect_stack(project))
    if previous and (canonical != previous["canonical"] or stack != previous["stack"]):
        raise ValueError(
            "This project is already initialized. Canonical/stack migration is manual; "
            "init will not replace customized rules or architecture."
        )
    agents = [] if args.agents in (None, "none") else [agent.strip() for agent in args.agents.split(",")]
    if any(agent not in ENTRIES for agent in agents):
        raise ValueError("Choose comma-separated agents from: " + ", ".join(ENTRIES) + "; or none")
    config = {
        "version": 1, "canonical": canonical, "stack": stack,
        "agents": sorted(set((previous["agents"] if previous else []) + agents)),
        "skills": (previous["skills"] if previous else False) or args.skills == "ponytail"
                  or (not previous and args.skills is None),
    }
    check_override(project, config)
    instructions = instruction_files(config)
    resources = scaffold(config)
    changes = {}
    actions = {}
    # Build and validate the entire plan before changing a file or creating a directory.
    for relative, content in list(resources.items()) + list(instructions.items()):
        path = safe_path(project, relative)
        existing = path.read_bytes().decode("utf-8") if path.exists() else ""
        if relative in instructions:
            if managed_block(existing, relative) is not None:
                print("PRESERVED project rules: " + relative)
                continue
            prefix = existing + ("\n\n" if existing and not existing.endswith("\n") else "\n" if existing else "")
            content = prefix + START + "\n" + content.rstrip() + "\n" + END + "\n"
        elif path.exists():
            print("PRESERVED project document: " + relative)
            continue
        changes[relative] = content.encode("utf-8")
        actions[relative] = "APPEND" if path.exists() else "CREATE"
    metadata = (json.dumps(config, indent=2, sort_keys=True) + "\n").encode("utf-8")
    state = safe_path(project, STATE)
    if not state.exists() or state.read_bytes() != metadata:
        changes[STATE] = metadata
        actions[STATE] = "UPDATE" if state.exists() else "CREATE"

    identifier = backup_id()
    for relative, content in list(changes.items()):
        path = safe_path(project, relative)
        if relative not in owned:
            owned[relative] = {
                "before_sha256": digest(path.read_bytes()) if path.exists() else None,
                "before_mode": stat.S_IMODE(path.stat().st_mode) if path.exists() else None,
                "backup": identifier if path.exists() else None,
            }
        owned[relative]["after_sha256"] = digest(content)
        backup_path(project, identifier, relative)
    if changes:
        ownership_path = safe_path(project, OWNERSHIP)
        changes[OWNERSHIP] = (json.dumps({"version": 1, "files": owned}, indent=2, sort_keys=True) + "\n").encode()
        actions[OWNERSHIP] = "UPDATE" if ownership_path.exists() else "CREATE"
        backup_path(project, identifier, OWNERSHIP)
        backup_path(project, identifier, "manifest.json")
        validate_records(owned, allowed_paths() - {OWNERSHIP})
    print("Project: {}\nCanonical: {}\nAgents: {}\nStack: {}".format(
        project, canonical, ", ".join(config["agents"]) or "canonical only", stack
    ))
    for relative in changes:
        print("WOULD_" + actions[relative] + " " + relative)
    if changes and not confirm_existing_setup(project, args.yes, args.dry_run):
        return 1
    if args.dry_run:
        print("Dry run: no project files changed. Setup readiness is unchecked.")
        return 0
    if not changes:
        print("UNCHANGED: no project files need changes.")
        return 0
    save_transaction(project, identifier, {path: (content, None) for path, content in changes.items()}, "init")
    for relative, content in changes.items():
        atomic_write(safe_path(project, relative), content)
        print({"CREATE": "CREATED", "APPEND": "APPENDED", "UPDATE": "UPDATED"}[actions[relative]] + " " + relative)
    print("Existing documents and managed blocks were preserved; init never resets them.")
    print("Next: complete setup with your agent, then run contextrivet project status.")
    return 0


def load_backup(project, identifier):
    root = safe_path(project, BACKUPS + "/" + identifier, directory=True)
    manifest = backup_path(project, identifier, "manifest.json")
    if not root.is_dir():
        raise ValueError("Backup not found: " + identifier)
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("version") != 1 or data.get("action") not in ("init", "restore", "uninstall", "skills-install"):
            raise ValueError("Invalid project backup manifest: " + identifier)
        validate_records(data.get("files"), allowed_paths())
        return data
    # Older releases saved only originals, so they cannot prove which files were created.
    records = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError("Refusing symlink in legacy backup: " + str(path))
        if path.is_dir():
            continue
        if relative not in set(CANONICALS) | set(ENTRIES.values()) | {STATE}:
            raise ValueError("Unrecognized legacy backup file: " + relative)
        safe = backup_path(project, identifier, relative)
        records[relative] = {"before_sha256": digest(safe.read_bytes()),
                             "before_mode": stat.S_IMODE(safe.stat().st_mode), "after_sha256": None}
    if not records:
        raise ValueError("Backup has no manifest or recognized originals: " + identifier)
    return {"version": 1, "action": "legacy", "files": records}


def list_backups(project):
    directories = [safe_path(project, ".agents/" + name + "/backups", directory=True)
                   for name in ("contextrivet", "dev-agent-config")]
    found = False
    for directory in directories:
        if not directory.exists():
            continue
        for path in sorted(directory.iterdir()):
            select_namespace(project, "restore", path.name)
            data = load_backup(project, path.name)
            print("{}  {}  {} file(s)  {}".format(path.name, data["action"], len(data["files"]), path))
            found = True
    if not found:
        print("No project backups found.")
        return 0
    print("Backups remain available after project uninstall.")
    return 0


def apply_removal_plan(project, args, changes):
    if not changes:
        print("UNCHANGED: no project files need changes.")
        return 0
    identifier = backup_id()
    for relative, (content, _mode) in changes.items():
        safe_path(project, relative)
        backup_path(project, identifier, relative)
        print(("WOULD_REMOVE " if content is None else "WOULD_RESTORE ") + relative)
    backup_path(project, identifier, "manifest.json")
    print("Current files will be saved to a recovery backup before changes; existing backups are retained.")
    if args.dry_run:
        print("Dry run: no project files changed.")
        return 0
    if not confirm_action("Apply this project " + args.action + " plan?", args.yes):
        return 1
    save_transaction(project, identifier, changes, args.action)
    for relative, (content, mode) in changes.items():
        path = safe_path(project, relative)
        if content is None:
            if path.exists():
                path.unlink()
            print("REMOVED " + relative)
        else:
            atomic_write(path, content, mode)
            print("RESTORED " + relative)
    print("Recovery command: contextrivet project restore --project {} --backup {} --dry-run".format(
        shlex.quote(str(project)), identifier
    ))
    return 0


def restore(project, args):
    data = load_backup(project, args.backup)
    changes = {}
    conflicts = []
    for relative, record in data["files"].items():
        path = safe_path(project, relative)
        current = path.read_bytes() if path.exists() else None
        original = read_original(project, args.backup, relative, record)
        if current == original and (original is None or stat.S_IMODE(path.stat().st_mode) == record["before_mode"]):
            continue
        if data["action"] != "legacy" and digest(current) != record["after_sha256"]:
            conflicts.append(relative)
        changes[relative] = (original, record["before_mode"])
    for relative in conflicts:
        print("LATER_EDIT " + relative)
    if conflicts and not args.force:
        print("Restore refused: files differ from that transaction. Review --force --dry-run before approving replacement.")
        return 1
    if data["action"] == "legacy":
        print("Legacy backup: restoring saved originals only; untracked generated files will remain.")
    return apply_removal_plan(project, args, changes)


def remove_project_block(content, relative):
    text = content.decode("utf-8")
    if managed_block(text, relative) is None:
        return content
    lines = text.splitlines(keepends=True)
    start = next(index for index, line in enumerate(lines) if line.rstrip("\r\n") in (START, LEGACY_START))
    end = next(index for index, line in enumerate(lines) if line.rstrip("\r\n") in (END, LEGACY_END))
    return "".join(lines[:start] + lines[end + 1:]).encode("utf-8")


def uninstall(project, args):
    config = load_config(project)
    owned = load_ownership(project)
    if not config and not owned:
        print("UNCHANGED: no managed project configuration found. Backups are retained.")
        return 0
    known_entries = set(CANONICALS) | set(ENTRIES.values())
    entries = (set(instruction_files(config)) if config else set()) | (set(owned) & known_entries)
    changes = {}
    for relative, record in owned.items():
        if relative == STATE:
            continue
        path = safe_path(project, relative)
        if not path.exists():
            continue
        current = path.read_bytes()
        if digest(current) == record["after_sha256"] or args.force:
            original = read_original(project, record.get("backup"), relative, record)
            changes[relative] = (original, record["before_mode"])
        elif relative not in entries:
            print("KEPT modified project file: " + relative)
    # Strip only this tool's marked block, preserving later edits outside the block.
    for relative in entries:
        if relative in changes:
            continue
        path = safe_path(project, relative)
        if not path.exists():
            continue
        current = path.read_bytes()
        stripped = remove_project_block(current, relative)
        if stripped != current:
            changes[relative] = (stripped if stripped.strip() else None, None)
    if not owned:
        print("Legacy setup: untracked documents and skills are retained; only managed rule blocks and manager metadata are removed.")
    if config:
        for relative in scaffold(config, include_references=False):
            if relative not in owned and safe_path(project, relative).exists():
                print("KEPT untracked project file: " + relative)
    for relative in (STATE, OWNERSHIP):
        if safe_path(project, relative).exists():
            changes[relative] = (None, None)
    return apply_removal_plan(project, args, changes)


def status(project):
    config = load_config(project)
    if config is None:
        raise ValueError("Project not initialized; run contextrivet project init --dry-run first")
    check_override(project, config)
    issues = []
    for relative in load_ownership(project):
        if remote_skill_path(relative) and not safe_path(project, relative).exists():
            issues.append("missing installed skill file: " + relative)
    instructions = instruction_files(config)
    for relative in list(scaffold(config)) + list(instructions):
        path = safe_path(project, relative)
        if not path.exists() or not path.read_text(encoding="utf-8").strip():
            issues.append("missing or empty: " + relative)
            continue
        if relative in instructions:
            block = managed_block(path.read_text(encoding="utf-8"), relative)
            references = (
                (".agents/PROJECT.md", ".agents/ARCHITECTURE.md")
                if relative == config["canonical"] else (config["canonical"],)
            )
            if not block or any("`" + reference + "`" not in block for reference in references):
                issues.append("missing project instruction route: " + relative)
    for relative, sections in SECTIONS.items():
        path = safe_path(project, relative)
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        if re.findall(r"^Status: (.+)$", content, re.MULTILINE) != ["ready"]:
            issues.append("expected one Status: ready line: " + relative)
        if "[REQUIRED:" in content:
            issues.append("unresolved required placeholders: " + relative)
        for section in sections:
            match = re.search(r"^## " + re.escape(section) + r"\n(.*?)(?=^## |\Z)", content, re.MULTILINE | re.DOTALL)
            if match is None or not match.group(1).strip():
                issues.append("missing or empty section '{}': {}".format(section, relative))
    print("Project: {}\nCanonical: {}\nAgents: {}".format(
        project, config["canonical"], ", ".join(config["agents"]) or "canonical only"
    ))
    for issue in issues:
        print("PENDING " + issue)
    print("Setup: " + ("pending" if issues else "ready (structural checks only)"))
    print("Agent loading, skill activation, and factual accuracy require manual verification.")
    return 1 if issues else 0


def main():
    parser = ProjectHelpParser(
        prog="contextrivet project",
        description="Create project-local instructions, onboarding, architecture, and knowledge. Requires Python 3; never runs project code.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    init = subparsers.add_parser("init", help="add missing files; preserve existing docs and managed rules")
    init.add_argument("--project", default=".", help="existing project directory (default: current directory)")
    init.add_argument("--canonical", choices=CANONICALS, help="canonical rules file (default: AGENTS.md)")
    init.add_argument("--agents", help="comma-separated: " + ",".join(ENTRIES) + "; default: none; adds entries without removing existing ones")
    init.add_argument("--stack", choices=STACKS, help="NestJS, Next.js, or Flutter; inferred from root manifests when unambiguous")
    init.add_argument("--skills", choices=("none", "ponytail"), help="initial skill selection (default: ponytail); existing skills are preserved")
    init.add_argument("--dry-run", action="store_true", help="preview without creating or modifying files")
    init.add_argument("--yes", action="store_true", help="explicitly consent to the additive plan when agent files already exist")
    check = subparsers.add_parser("status", help="check scaffold and required docs; exit 1 while pending")
    check.add_argument("--project", default=".", help="existing project directory (default: current directory)")
    backups = subparsers.add_parser("backups", help="list saved originals and recovery backups")
    backups.add_argument("--project", default=".", help="existing project directory (default: current directory)")
    skills = subparsers.add_parser(
        "skills", help="list GitHub references or install selected pinned project skills",
        description="Install catalog skills from reviewed GitHub commits into .agents/skills/.\n"
                    "Includes references, license and source records; no skill scripts execute.\n"
                    "Flutter has catalog entries; NestJS/Next.js catalogs are currently empty.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  contextrivet project skills --stack flutter\n"
               "  contextrivet project skills install --names flutter-architecture --dry-run\n"
               "  contextrivet project skills install --names flutter-architecture\n"
               "  contextrivet project skills install --all\n\n"
               "Initialize the project first. Installation asks for consent; --yes approves the plan.\n"
               "Dry runs make no downloads. Custom files are preserved; verify agent activation.\n"
               "See README.md for usage and CONTRIBUTING.md to suggest improvements.",
    )
    skills.add_argument("skills_action", nargs="?", choices=("install",), help="omit to list references")
    skills.add_argument("--stack", choices=STACKS, help="required for listing; installation uses the saved project stack")
    skills.add_argument("--project", default=".", help="initialized project directory")
    selection = skills.add_mutually_exclusive_group()
    selection.add_argument("--names", help="comma-separated catalog skill names to install")
    selection.add_argument("--all", action="store_true", help="install every catalog skill for the project stack")
    skills.add_argument("--dry-run", action="store_true", help="preview sources without network requests or project changes")
    skills.add_argument("--yes", action="store_true", help="approve the displayed skill installation plan")
    for action in ("restore", "uninstall"):
        command = subparsers.add_parser(action, help="restore a selected backup" if action == "restore" else "remove owned configuration and restore original rules")
        command.add_argument("--project", default=".", help="existing project directory (default: current directory)")
        command.add_argument("--dry-run", action="store_true", help="preview without creating, deleting, or modifying files")
        command.add_argument("--yes", action="store_true", help="explicitly approve the displayed plan")
        command.add_argument("--force", action="store_true", help="include later-edited owned files; current files are saved in a recovery backup first")
        if action == "restore":
            command.add_argument("--backup", required=True, help="backup ID from project backups")
    args = parser.parse_args()
    try:
        if args.action == "skills" and args.skills_action is None:
            if not args.stack or args.names or args.all or args.yes or args.dry_run:
                raise ValueError("List with project skills --stack <stack>; install with project skills install --names <name,...> or --all")
            print(skill_index(args.stack), end="")
            return 0
        project = Path(args.project).resolve(strict=True)
        if not project.is_dir():
            raise ValueError("Project must be an existing directory")
        if args.action != "backups":
            select_namespace(project, args.action, getattr(args, "backup", None))
        if args.action == "init":
            return initialize(project, args)
        if args.action == "skills":
            return install_skills(project, args)
        if args.action == "status":
            return status(project)
        if args.action == "backups":
            return list_backups(project)
        return restore(project, args) if args.action == "restore" else uninstall(project, args)
    except (OSError, ValueError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
