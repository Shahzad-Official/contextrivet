#!/usr/bin/env python3
"""Ownership evidence for the fixed shared-link destinations; never follow parents."""
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
HOME = Path(os.environ["HOME"]).absolute()
REGISTRY = HOME / ".agents/contextrivet/links.json"


def destinations():
    skills = (".agents/skills/ponytail", ".claude/skills/ponytail",
              ".gemini/skills/ponytail", ".gemini/config/skills/ponytail",
              ".config/opencode/skills/ponytail", ".cline/data/settings/skills/ponytail")
    return dict([(str(HOME / path), str(ROOT / "skills/ponytail")) for path in skills] + [
        (str(HOME / ".agents/instructions/code-intelligence.md"), str(ROOT / "instructions/code-intelligence.md")),
        (str(HOME / ".agents/AGENTS.md"), str(HOME / "AGENTS.md")),
    ])


def safe(path):
    path = Path(path)
    relative = path.relative_to(HOME)
    if ".." in relative.parts:
        raise ValueError("Unexpected managed path: " + str(path))
    for parent in reversed(path.parents):
        if parent == HOME or HOME in parent.parents:
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise ValueError("Refusing symlinked/non-directory parent: " + str(parent))
    return path


def load(path=None):
    path = safe(REGISTRY if path is None else path)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("Refusing unsafe link registry: " + str(path))
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("links"), dict):
        raise ValueError("Invalid shared link ownership registry")
    for target, origin in data["links"].items():
        if target not in destinations() or not isinstance(origin, str) or not Path(origin).is_absolute() or any(c in origin for c in "\t\r\n"):
            raise ValueError("Unexpected shared link ownership record")
    return data["links"]


def legacy_origin(target, origin):
    """Legacy creation manifest plus recognizable source, never a basename alone."""
    suffix = "/skills/ponytail" if target.endswith("/skills/ponytail") else "/instructions/code-intelligence.md" if target.endswith("/instructions/code-intelligence.md") else None
    if suffix is None or not origin.endswith(suffix):
        return False
    root = Path(origin[:-len(suffix)])
    try:
        from project import safe_path
        if safe_path(root, "AGENTS.md").read_bytes() != (ROOT / "AGENTS.md").read_bytes():
            return False
        if safe_path(root, "skills/ponytail/SOURCE.md").read_bytes() != (ROOT / "skills/ponytail/SOURCE.md").read_bytes():
            return False
        for namespace in ("contextrivet", "dev-agent-config"):
            directory = safe(HOME / ".agents" / namespace / "backups")
            if directory.is_symlink() or not directory.is_dir():
                continue
            for manifest in directory.glob("*/manifest.tsv"):
                safe(manifest)
                if manifest.is_symlink() or not manifest.is_file():
                    continue
                for line in manifest.read_text().splitlines()[1:]:
                    saved = str(manifest.parent / "original" / Path(target).relative_to(HOME))
                    if line.split("\t") == ["missing", target, saved]:
                        return True
    except (OSError, ValueError):
        return False
    return False


def owned(target, records):
    path = safe(target)
    if path.is_symlink():
        origin = os.readlink(path)
        if records.get(target) == origin:
            return True
        # Supported legacy evidence: exact current checkout target AND a managed
        # global rules block. An old vanished checkout without a record is ambiguous.
        rules = safe(HOME / "AGENTS.md")
        if target not in records and rules.is_file() and not rules.is_symlink():
            lines = rules.read_text().splitlines()
            marked = any(start in lines and end in lines for start, end in (
                ("# >>> contextrivet managed >>>", "# <<< contextrivet managed <<<"),
                ("# >>> dev-agent-config managed >>>", "# <<< dev-agent-config managed <<<")))
            return marked and (origin == destinations()[target] or legacy_origin(target, origin))
        return False
    return not path.exists() and target in records


def main():
    action = sys.argv[1]
    records = load(sys.argv[2] if action == "validate" and len(sys.argv) == 3 else None)
    if action == "validate":
        return 0
    if action == "tracked":
        return 0 if records.get(sys.argv[2]) == destinations().get(sys.argv[2]) else 1
    if action == "owned":
        target = sys.argv[2]
        return 0 if target in destinations() and owned(target, records) else 1
    if action == "record":
        target, origin = sys.argv[2:]
        if destinations().get(target) != origin:
            raise ValueError("Unexpected link source/destination")
        records[target] = origin
        # The shell transaction has already validated and backed up this file.
        from project import atomic_write
        atomic_write(safe(REGISTRY), (json.dumps({"version": 1, "links": records}, indent=2, sort_keys=True) + "\n").encode(), 0o600)
        return 0
    if action == "plan":
        plan = []
        for target, origin in destinations().items():
            path = safe(target)
            if owned(target, records):
                source = Path(origin)
                if not source.exists():
                    raise ValueError("Managed source unavailable; restore/reinstall the checkout first: " + origin)
                if path.is_symlink() and os.readlink(path) == origin:
                    continue
                plan.append((target, origin))
            elif path.is_symlink() and (not path.exists() or os.readlink(path) != origin):
                print("AMBIGUOUS preserved link: {}. Ownership/expected source is unproven; review manually, then use explicit replace only if intended.".format(target), file=sys.stderr)
            elif target in records and path.exists() and not path.is_symlink():
                print("PRESERVED custom file/directory: " + target, file=sys.stderr)
        for target, origin in plan:
            print(target + "\t" + origin)
        return 0
    raise ValueError("Unknown ownership action")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        sys.exit(1)
