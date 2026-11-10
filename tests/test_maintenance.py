#!/usr/bin/env python3
"""Bootstrap, repair, health, drift and automation in disposable HOME/projects."""
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "contextrivet"
STATE = ".agents/contextrivet/project.json"


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.home = self.base / "home"
        self.project = self.base / "project with spaces"
        self.home.mkdir()
        self.project.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), PYTHONDONTWRITEBYTECODE="1")
        for name in ("XDG_STATE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "GIT_DIR", "GIT_WORK_TREE"):
            self.env.pop(name, None)

    def command(self, *args, expected=0, cli=CLI):
        result = subprocess.run([str(cli), *args], cwd=self.project, env=self.env,
                                input="", text=True, capture_output=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def snapshot(self, directory=None):
        return {str(path.relative_to(directory or self.base)):
                ("link", os.readlink(path)) if path.is_symlink() else
                ("dir",) if path.is_dir() else ("file", path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_mode)
                for path in (directory or self.base).rglob("*")}

    def active_content(self, directory=None):
        return {name: (value[0], value[1], value[-1]) if value[0] == "file" else value
                for name, value in self.snapshot(directory or self.project).items()
                if value[0] != "dir" and "/backups/" not in name}

    def ready(self):
        self.command("project", "init")
        for name in ("PROJECT.md", "ARCHITECTURE.md"):
            path = self.project / ".agents" / name
            path.write_text(re.sub(r"\[REQUIRED: [^\]]+\]", "Explicit fixture evidence", path.read_text().replace("Status: pending", "Status: ready")))

    def health(self, *args, expected=0):
        return json.loads(self.command("health", "--project-only", "--json", *args, expected=expected).stdout)

    def copy_checkout(self):
        checkout = self.base / "old checkout"
        checkout.mkdir()
        for name in ("scripts", "skills", "instructions"):
            shutil.copytree(ROOT / name, checkout / name, ignore=shutil.ignore_patterns("__pycache__"))
        for name in ("AGENTS.md", "contextrivet"):
            shutil.copy2(ROOT / name, checkout / name)
        return checkout

    def load_pre_upgrade_project(self):
        fixture = json.loads((ROOT / "tests/fixtures/pre-upgrade-project.json").read_text())
        self.assertTrue(fixture["source_revision"].startswith("af0a523"))
        for relative, record in fixture["files"].items():
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(record["content"])
            path.chmod(record["mode"])
        subprocess.run(["git", "init", "-q", str(self.project)], check=True, env=self.env)
        return self.active_content()

    def transaction(self, action):
        backups = self.project / ".agents/contextrivet/backups"
        return sorted(path.parent.name for path in backups.glob("*/manifest.json")
                      if json.loads(path.read_text())["action"] == action)[-1]

    def test_pre_upgrade_project_preserves_customizations_and_legacy_automation(self):
        original = self.load_pre_upgrade_project()
        before = self.snapshot()
        self.command("project", "init", "--dry-run")
        self.command("project", "init")
        self.command("project", "init")
        self.command("project", "repair", "--apply")
        self.command("project", "status")
        self.assertEqual(json.loads((self.project / STATE).read_text())["stack"], "flutter")
        self.assertFalse(any(item["state"] == "failure" for item in self.health()["findings"]))
        for flag in ("--dry-run", "--apply"):
            self.command("project", "automate", "--hook", "--ci", flag, expected=1)
        self.assertEqual(before, self.snapshot(), "upgrade rewrote customized or unowned files")
        owned = json.loads((self.project / ".agents/contextrivet/installed.json").read_text())["files"]
        for relative in (".git/hooks/pre-commit", ".github/workflows/contextrivet.yml", ".agents/contextrivet/checker/README.md"):
            self.assertNotIn(relative, owned)
        note = ".agents/knowledge/features/schedule.md"
        self.command("project", "baseline", "--note", note, "--yes")
        self.command("project", "restore", "--backup", self.transaction("baseline"), "--yes")
        self.assertEqual(original, self.active_content(), "baseline rollback changed pre-upgrade state")
        self.command("project", "uninstall", "--yes")
        for relative in (".agents/PROJECT.md", ".agents/ARCHITECTURE.md", note,
                         ".agents/instructions/workflow.md", ".agents/skills/ponytail/SKILL.md",
                         ".git/hooks/pre-commit", ".github/workflows/contextrivet.yml", ".agents/contextrivet/checker/README.md"):
            self.assertEqual(original[relative], self.active_content()[relative], relative)
        self.assertIn("Team rule: preserve the offline schedule cache.", (self.project / "AGENTS.md").read_text())
        self.assertNotIn("# >>> contextrivet project >>>", (self.project / "AGENTS.md").read_text())
        self.assertFalse((self.project / STATE).exists())
        self.command("project", "restore", "--backup", self.transaction("uninstall"), "--yes")
        self.assertEqual(original, self.active_content(), "uninstall recovery failed to restore old ownership")

    def test_pre_upgrade_explicit_automation_migration_has_recovery(self):
        original = self.load_pre_upgrade_project()
        archive = self.base / "reviewed-legacy-automation"
        archive.mkdir()
        for relative, name in ((".git/hooks/pre-commit", "pre-commit"),
                               (".github/workflows/contextrivet.yml", "contextrivet.yml"),
                               (".agents/contextrivet/checker", "checker")):
            shutil.move(str(self.project / relative), str(archive / name))
        before_adoption = self.active_content()
        self.command("project", "automate", "--hook", "--ci", "--dry-run")
        self.command("project", "automate", "--hook", "--ci", "--apply")
        adopted = self.active_content()
        for relative in ("AGENTS.md", ".agents/PROJECT.md", ".agents/ARCHITECTURE.md",
                         ".agents/knowledge/features/schedule.md", ".agents/instructions/workflow.md"):
            self.assertEqual(original[relative], adopted[relative])
        self.health()
        before = self.snapshot()
        self.command("project", "automate", "--hook", "--ci", "--apply")
        self.command("project", "init")
        self.command("project", "repair", "--apply")
        self.assertEqual(before, self.snapshot(), "repeat adoption was not idempotent")
        self.command("project", "restore", "--backup", self.transaction("automate"), "--yes")
        self.assertEqual(before_adoption, self.active_content())
        self.assertTrue((archive / "pre-commit").is_file(), "CLI rollback touched the manual archive")
        self.command("project", "automate", "--hook", "--ci", "--apply")
        hook = self.project / ".git/hooks/pre-commit"
        hook.write_text(hook.read_text() + "\n# Team's post-adoption customization\n")
        customized = self.active_content()
        self.command("project", "uninstall", "--yes")
        self.assertEqual(customized[".git/hooks/pre-commit"], self.active_content()[".git/hooks/pre-commit"])
        self.assertFalse((self.project / ".github/workflows/contextrivet.yml").exists())
        self.assertFalse((self.project / ".agents/contextrivet/checker/scripts/maintenance.py").exists())
        self.command("project", "restore", "--backup", self.transaction("uninstall"), "--yes")
        self.assertEqual(customized, self.active_content())

    def test_matching_unowned_automation_is_not_silently_adopted(self):
        self.ready()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True, env=self.env)
        ownership = self.project / ".agents/contextrivet/installed.json"
        old_records = ownership.read_bytes()
        self.command("project", "automate", "--hook", "--ci", "--apply")
        # Model the earlier untracked generator, even when every byte matches.
        ownership.write_bytes(old_records)
        before = self.snapshot()
        self.command("project", "automate", "--hook", "--ci", "--apply")
        self.assertEqual(before, self.snapshot())
        self.assertEqual(ownership.read_bytes(), old_records)
        unowned = {relative: self.active_content()[relative] for relative in (
            ".git/hooks/pre-commit", ".github/workflows/contextrivet.yml", ".agents/contextrivet/checker/scripts/maintenance.py")}
        self.command("project", "uninstall", "--yes")
        self.assertEqual(unowned, {relative: self.active_content()[relative] for relative in unowned})

    def test_neutral_defaults_ignore_manifests_and_are_idempotent(self):
        fixtures = ({}, {"package.json": '{"dependencies":{"next":"x"}}'},
                    {"package.json": '{"dependencies":{"@nestjs/core":"x"}}'},
                    {"pubspec.yaml": "dependencies:\n  flutter:\n    sdk: flutter\n"},
                    {"package.json": '{"dependencies":{"next":"x","@nestjs/core":"x"}}'},
                    {"Cargo.toml": "[package]\nname = 'fixture'"}, {"package.json": "invalid JSON"})
        for index, files in enumerate(fixtures):
            directory = self.project / str(index)
            directory.mkdir()
            for name, content in files.items():
                (directory / name).write_text(content)
            self.command("project", "init", "--project", str(directory), "--dry-run")
            self.assertEqual(set(path.name for path in directory.iterdir()), set(files))
            self.command("project", "init", "--project", str(directory))
            self.assertEqual(json.loads((directory / STATE).read_text())["stack"], "none")
            self.assertEqual((directory / ".agents/instructions/stack.md").read_bytes(), (ROOT / "templates/project/stacks/none.md").read_bytes())
            before = self.snapshot(directory)
            self.command("project", "init", "--project", str(directory))
            self.assertEqual(before, self.snapshot(directory))
        self.assertEqual(list(self.home.iterdir()), [])

    def test_explicit_profiles_saved_defaults_and_legacy_profiles(self):
        for stack in ("none", "nestjs", "nextjs", "flutter"):
            directory = self.project / stack
            directory.mkdir()
            self.command("project", "init", "--project", str(directory), "--stack", stack, "--skills", "none")
            self.assertFalse((directory / ".agents/skills").exists())
            (directory / "package.json").write_text('{"dependencies":{"@nestjs/core":"conflicting manifest"}}' if stack == "nextjs" else '{"dependencies":{"next":"conflicting manifest"}}')
            before = self.snapshot(directory)
            self.command("project", "init", "--project", str(directory))
            self.assertEqual(before, self.snapshot(directory))
            self.command("project", "init", "--project", str(directory), "--stack", "flutter" if stack == "none" else "none", expected=1)
            self.assertEqual(before, self.snapshot(directory))
        for stack in ("generic", "backend", "react"):
            directory = self.project / stack
            directory.mkdir()
            self.command("project", "init", "--project", str(directory))
            path = directory / STATE
            config = json.loads(path.read_text())
            config["stack"] = stack
            path.write_text(json.dumps(config))
            self.command("project", "init", "--project", str(directory), "--yes")
            self.assertEqual(json.loads(path.read_text())["stack"], stack)
            self.command("project", "status", "--project", str(directory), expected=1)
            self.command("project", "uninstall", "--project", str(directory), "--yes")

    def test_project_repair_backups_restore_and_preserves_customization(self):
        self.ready()
        path = self.project / ".agents/instructions/stack.md"
        path.unlink()
        context = (self.project / ".agents/PROJECT.md").read_bytes()
        before = self.snapshot()
        self.command("project", "repair")
        self.assertEqual(before, self.snapshot())
        self.command("project", "repair", "--apply")
        self.assertTrue(path.is_file())
        self.assertEqual(context, (self.project / ".agents/PROJECT.md").read_bytes())
        before = self.snapshot()
        self.command("project", "repair", "--apply")
        self.assertEqual(before, self.snapshot())
        manifests = list((self.project / ".agents/contextrivet/backups").glob("*/manifest.json"))
        repair = next(item.parent.name for item in manifests if json.loads(item.read_text())["action"] == "repair")
        self.command("project", "restore", "--backup", repair, "--yes")
        self.assertFalse(path.exists())

    def test_project_repair_refuses_links_and_unknown_bytes(self):
        self.command("project", "init")
        owned = self.project / ".agents/contextrivet/installed.json"
        data = json.loads(owned.read_text())
        data["files"][".agents/instructions/stack.md"]["after_sha256"] = "a" * 64
        owned.write_text(json.dumps(data))
        path = self.project / ".agents/instructions/stack.md"
        path.unlink()
        before = self.snapshot()
        self.command("project", "repair", "--apply", expected=1)
        self.assertEqual(before, self.snapshot())
        path.symlink_to(self.base / "missing-custom")
        before = self.snapshot()
        self.command("project", "repair", "--apply", expected=1)
        self.assertEqual(before, self.snapshot())

    def test_repair_preserves_edited_managed_files_and_custom_content(self):
        self.ready()
        for relative in ("AGENTS.md", ".agents/PROJECT.md", ".agents/ARCHITECTURE.md",
                         ".agents/instructions/workflow.md", ".agents/skills/ponytail/SKILL.md"):
            path = self.project / relative
            path.write_text(path.read_text() + "\nKeep this project customization.\n")
        note = self.project / ".agents/knowledge/features/custom.md"
        note.parent.mkdir()
        note.write_text("Custom project knowledge\n")
        missing = self.project / ".agents/instructions/stack.md"
        missing.unlink()
        before = self.active_content()
        self.command("project", "repair", "--apply")
        after = self.active_content()
        del after[".agents/instructions/stack.md"]
        self.assertEqual(before, after)

    def test_moved_checkout_links_repair_merge_and_rollback(self):
        old = self.copy_checkout()
        self.command("install", cli=old / "contextrivet")
        moved = old.with_name("moved checkout")
        old.rename(moved)
        link = self.home / ".agents/skills/ponytail"
        original = os.readlink(link)
        registry = self.home / ".agents/contextrivet/links.json"
        original_registry = registry.read_bytes()
        self.assertFalse(link.exists())
        before = self.snapshot()
        self.command("repair")
        self.assertEqual(before, self.snapshot())
        self.command("repair", "--apply")
        self.assertEqual(os.readlink(link), str(ROOT / "skills/ponytail"))
        before = self.snapshot()
        self.command("repair", "--apply")
        self.assertEqual(before, self.snapshot())
        self.command("rollback")
        self.assertEqual(os.readlink(link), original)
        self.assertEqual(registry.read_bytes(), original_registry)
        self.command("install", "--mode=merge")
        self.assertEqual(os.readlink(link), str(ROOT / "skills/ponytail"))
        installed = self.active_content(self.home)
        self.command("uninstall", "--apply")
        self.assertFalse(link.is_symlink())
        self.assertFalse(registry.exists())
        self.command("repair", "--apply")
        self.assertFalse(link.exists())
        self.command("rollback")
        restored = self.active_content(self.home)
        installed.pop(".agents/contextrivet/last-backup")
        restored.pop(".agents/contextrivet/last-backup")
        self.assertEqual(installed, restored)

    def test_supported_legacy_broken_link_requires_creation_and_source_evidence(self):
        old = self.copy_checkout()
        self.command("install", cli=old / "contextrivet")
        (self.home / ".agents/contextrivet/links.json").unlink()
        (old / "instructions/code-intelligence.md").unlink()
        link = self.home / ".agents/instructions/code-intelligence.md"
        self.assertFalse(link.exists())
        self.command("repair", "--apply")
        self.assertEqual(os.readlink(link), str(ROOT / "instructions/code-intelligence.md"))

    def test_unproven_legacy_link_and_unexpected_registry_path_are_preserved(self):
        old = self.copy_checkout()
        self.command("install", cli=old / "contextrivet")
        registry = self.home / ".agents/contextrivet/links.json"
        registry.unlink()
        shutil.rmtree(old)
        link = self.home / ".agents/instructions/code-intelligence.md"
        original = os.readlink(link)
        before = self.snapshot()
        self.assertIn("AMBIGUOUS", self.command("repair", "--apply").stderr)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(os.readlink(link), original)
        registry.write_text(json.dumps({"version": 1, "links": {str(self.home / "custom"): str(ROOT / "skills/ponytail")}}))
        before = self.snapshot()
        self.command("repair", "--apply", expected=1)
        self.assertEqual(before, self.snapshot())

    def test_shared_repair_failure_rolls_back_links_and_records(self):
        old = self.copy_checkout()
        self.command("install", cli=old / "contextrivet")
        old.rename(old.with_name("moved checkout"))
        registry = self.home / ".agents/contextrivet/links.json"
        records = registry.read_bytes()
        link = self.home / ".agents/skills/ponytail"
        original = os.readlink(link)
        fake_bin = self.base / "fake-bin"
        fake_bin.mkdir()
        fake_ln = fake_bin / "ln"
        fake_ln.write_text('#!/bin/sh\nif [ -f "$HOME/ln-called" ]; then exit 1; fi\ntouch "$HOME/ln-called"\nexec /bin/ln "$@"\n')
        fake_ln.chmod(0o755)
        self.env["PATH"] = str(fake_bin) + os.pathsep + os.environ["PATH"]
        result = self.command("repair", "--apply", expected=1)
        self.assertIn("Repair failed", result.stderr)
        self.assertEqual(os.readlink(link), original)
        self.assertEqual(registry.read_bytes(), records)

    def test_custom_links_files_and_directories_are_preserved(self):
        self.command("install")
        link = self.home / ".agents/skills/ponytail"
        link.unlink()
        link.symlink_to(self.base / "missing-custom")
        self.command("repair", "--apply")
        self.assertEqual(os.readlink(link), str(self.base / "missing-custom"))
        self.command("install", "--mode=merge")
        self.assertEqual(os.readlink(link), str(self.base / "missing-custom"))
        link.unlink()
        link.mkdir()
        (link / "SKILL.md").write_text("custom")
        before = self.snapshot()
        self.command("repair", "--apply")
        self.assertEqual(before, self.snapshot())
        shutil.rmtree(link)
        link.write_text("custom file")
        before = self.snapshot()
        self.command("repair", "--apply")
        self.assertEqual(before, self.snapshot())

    def test_missing_recorded_link_is_restored_and_unsafe_parents_fail_before_writes(self):
        self.command("install")
        link = self.home / ".agents/skills/ponytail"
        link.unlink()
        self.command("repair", "--apply")
        self.assertTrue(link.is_symlink())
        directory = link.parent
        directory.rename(self.home / "custom-skills")
        directory.symlink_to(self.home / "custom-skills", target_is_directory=True)
        before = self.snapshot()
        self.command("repair", "--apply", expected=1)
        self.assertEqual(before, self.snapshot())

    def test_symlinked_backup_parent_refused_before_repair(self):
        self.command("install")
        link = self.home / ".agents/skills/ponytail"
        link.unlink()
        backups = self.home / ".agents/contextrivet/backups"
        outside = self.base / "outside-backups"
        backups.rename(outside)
        backups.symlink_to(outside, target_is_directory=True)
        before = self.snapshot()
        self.command("repair", "--apply", expected=1)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(link.exists())

    def test_health_json_scopes_readiness_and_exit_codes(self):
        pending = self.health(expected=1)
        self.assertEqual(pending["schema_version"], 1)
        self.assertEqual(pending["overall"], "fail")
        self.ready()
        before = self.snapshot()
        report = self.health()
        self.assertEqual(before, self.snapshot())

        self.assertEqual(report["scopes"]["global"]["result"], "skipped")
        self.assertTrue(any(f["id"] == "activation.unverified" and f["state"] == "unknown" for f in report["findings"]))
        self.assertFalse(any(f["state"] == "failure" for f in report["findings"]))
        self.command("health", "--json", expected=1)
        self.command("install")
        self.command("health", "--json")
        rules = self.home / "AGENTS.md"
        rules.write_text(rules.read_text().replace("# <<< contextrivet managed <<<", "Extra local guidance.\n# <<< contextrivet managed <<<"))
        changed = json.loads(self.command("health", "--global-only", "--json").stdout)
        self.assertTrue(any(f["id"] == "instructions.drift" and f["state"] == "warning" for f in changed["findings"]))
        metadata = self.home / ".local/state/contextrivet/tools/codebase-memory-mcp"
        metadata.mkdir(parents=True)
        (metadata / "codex-mcp.tsv").write_text("fixture integration record")
        observed = json.loads(self.command("health", "--global-only", "--json").stdout)
        self.assertTrue(any(f["id"] == "intelligence.configured" and f["state"] == "unknown" for f in observed["findings"]))
        self.command("health", "--project-only", "--global-only", expected=2)
        self.command("health", "--invalid", expected=2)
        before = self.snapshot()
        self.command("repair", "--apply", "--dry-run", expected=1)
        self.assertEqual(before, self.snapshot())

    def test_project_only_without_home_or_network(self):
        self.ready()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True, env=self.env)
        self.command("project", "automate", "--hook", "--ci", "--apply")
        # A distributed checkout may use a worktree .git file rather than the
        # developer's local .git/hooks directory recorded in project metadata.
        shutil.rmtree(self.project / ".git")
        (self.project / ".git").write_text("gitdir: /unavailable-local-worktree\n")
        # Deny both Python networking and child processes; a check cannot hide
        # a network request in a dependency installer, agent, or shell command.
        guard = '''
import runpy, socket, subprocess, sys, urllib.request
def forbidden(*args, **kwargs):
    raise AssertionError("health attempted networking or process execution")
socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden
socket.create_connection = forbidden
socket.getaddrinfo = forbidden
urllib.request.urlopen = forbidden
subprocess.Popen = forbidden
sys.path.insert(0, sys.argv[1])
sys.argv = [sys.argv[2], "--project-only", "--json"]
runpy.run_path(sys.argv[0], run_name="__main__")
'''
        env = dict(self.env)
        env.pop("HOME")
        before = self.snapshot()
        for script in (ROOT / "scripts/maintenance.py", self.project / ".agents/contextrivet/checker/scripts/maintenance.py"):
            checked = subprocess.run([sys.executable, "-B", "-c", guard, str(script.parent), str(script)],
                                     cwd=self.project, env=env, text=True, capture_output=True)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertEqual(json.loads(checked.stdout)["scopes"]["global"]["result"], "skipped")
        self.assertEqual(before, self.snapshot())

    def test_global_rollback_preflights_all_records(self):
        old = self.copy_checkout()
        self.command("install", cli=old / "contextrivet")
        old.rename(old.with_name("moved checkout"))
        self.command("repair", "--apply")
        backup = Path((self.home / ".agents/contextrivet/last-backup").read_text().strip())
        (backup / "original/.agents/contextrivet/links.json").unlink()
        before = self.snapshot()
        self.command("rollback", str(backup), expected=1)
        self.assertEqual(before, self.snapshot())

    def test_global_rollback_recovers_a_failed_metadata_restore(self):
        old = self.copy_checkout()
        self.command("install", cli=old / "contextrivet")
        old.rename(old.with_name("moved checkout"))
        self.command("repair", "--apply")
        backup = Path((self.home / ".agents/contextrivet/last-backup").read_text().strip())
        fake_bin = self.base / "fake-bin"
        fake_bin.mkdir()
        fake_cp = fake_bin / "cp"
        fake_cp.write_text('#!/bin/sh\nif [ "$2" = "$FAIL_COPY_SOURCE" ] && [ ! -f "$FAIL_COPY_ONCE" ]; then\n  touch "$FAIL_COPY_ONCE"\n  exit 1\nfi\nexec /bin/cp "$@"\n')
        fake_cp.chmod(0o755)
        self.env.update(PATH=str(fake_bin) + os.pathsep + os.environ["PATH"],
                        FAIL_COPY_SOURCE=str(backup / "original/.agents/contextrivet/links.json"),
                        FAIL_COPY_ONCE=str(self.base / "copy-failed"))
        before = {name: value for name, value in self.snapshot(self.home).items() if "/backups/" not in name}
        self.command("rollback", str(backup), expected=1)
        after = {name: value for name, value in self.snapshot(self.home).items() if "/backups/" not in name}
        self.assertEqual(before, after)

    def test_global_rollback_rejects_corrupt_metadata_before_writes(self):
        old = self.copy_checkout()
        self.command("install", cli=old / "contextrivet")
        old.rename(old.with_name("moved checkout"))
        self.command("repair", "--apply")
        backup = Path((self.home / ".agents/contextrivet/last-backup").read_text().strip())
        saved = backup / "original/.agents/contextrivet/links.json"
        saved.write_text('{"version": 1, "links": {"/unexpected": "/unrelated"}}')
        before = self.snapshot()
        self.command("rollback", str(backup), expected=1)
        self.assertEqual(before, self.snapshot())
    def test_references_detect_missing_but_ignore_examples_placeholders_and_urls(self):
        self.ready()
        path = self.project / ".agents/knowledge/INDEX.md"
        path.write_text(path.read_text() + '\n```markdown\n- `.agents/example.md` — example\n```\n- `.agents/features/<name>.md` — placeholder\n[remote](https://example.com/no)\n`arbitrary/missing`\n`[example](missing.md)`\n')
        self.health()
        path.write_text(path.read_text() + "\n- `.agents/knowledge/missing.md` — broken\n")
        self.assertTrue(any(f["id"] == "reference.missing" for f in self.health(expected=1)["findings"]))
        path.write_text("# Knowledge index\n")
        canonical = self.project / "AGENTS.md"
        canonical.write_text(canonical.read_text().replace(".agents/instructions/bootstrap.md", ".agents/instructions/missing.md"))
        self.assertTrue(any(f["id"] == "reference.missing" for f in self.health(expected=1)["findings"]))

    def test_drift_is_explicit_deterministic_read_only_and_recoverable(self):
        self.ready()
        source = self.project / "source.txt"
        source.write_text("v1")
        note = ".agents/knowledge/features/behavior.md"
        path = self.project / note
        path.parent.mkdir()
        path.write_text("# Observed behavior\nSource: `source.txt`\n")
        self.assertTrue(any(f["id"] == "knowledge.unbaselined" for f in self.health()["findings"]))
        before = self.snapshot()
        self.command("project", "baseline", "--note", note, "--dry-run")
        self.assertEqual(before, self.snapshot())
        self.command("project", "baseline", "--note", note, "--yes")
        source.write_text("v2")
        before = self.snapshot()
        report = self.health()
        self.assertEqual(report, self.health())
        self.assertEqual(before, self.snapshot())
        self.assertTrue(any(f["id"] == "knowledge.stale" and f["path"] == note and "source.txt" in f["message"] for f in report["findings"]))
        self.command("project", "baseline", "--note", note, "--yes")
        self.assertFalse(any(f["id"] == "knowledge.stale" for f in self.health()["findings"]))
        before = self.snapshot()
        self.command("project", "baseline", "--note", note, "--yes")
        self.assertEqual(before, self.snapshot())
        source.unlink()
        self.assertTrue(any(f["id"] == "knowledge.source_missing" for f in self.health()["findings"]))
        self.command("project", "baseline", "--note", note, "--yes", expected=1)

    def test_evidence_restore_and_uninstall_keep_metadata_consistent(self):
        self.ready()
        source = self.project / "source.txt"
        source.write_text("v1")
        note = ".agents/knowledge/features/evidence.md"
        path = self.project / note
        path.parent.mkdir()
        path.write_text("# Observation\nSource: `source.txt`\n")
        original = self.active_content()
        output = self.command("project", "baseline", "--note", note, "--yes").stdout
        self.assertIn("does not confirm factual accuracy", output)
        self.assertNotIn("reviewed", output.lower())
        recorded = self.active_content()
        evidence = self.project / ".agents/contextrivet/evidence.json"
        ownership = self.project / ".agents/contextrivet/installed.json"
        self.assertIn(".agents/contextrivet/evidence.json", json.loads(ownership.read_text())["files"])
        manifests = self.project / ".agents/contextrivet/backups"
        baseline = next(file.parent.name for file in manifests.glob("*/manifest.json") if json.loads(file.read_text())["action"] == "baseline")
        self.command("project", "restore", "--backup", baseline, "--yes")
        self.assertEqual(original, self.active_content())
        recovery = next(file.parent.name for file in manifests.glob("*/manifest.json") if json.loads(file.read_text())["action"] == "restore")
        self.command("project", "restore", "--backup", recovery, "--yes")
        self.assertEqual(recorded, self.active_content())
        self.command("project", "uninstall", "--yes")
        self.assertFalse(evidence.exists())
        self.assertFalse(ownership.exists())
        self.assertTrue(path.exists())
        uninstall = next(file.parent.name for file in manifests.glob("*/manifest.json") if json.loads(file.read_text())["action"] == "uninstall")
        self.command("project", "restore", "--backup", uninstall, "--yes")
        self.assertEqual(recorded, self.active_content())

    def test_pending_onboarding_is_a_readiness_failure(self):
        self.command("project", "init")
        before = self.snapshot()
        report = self.health(expected=1)
        pending = [item for item in report["findings"] if item["id"] == "project.readiness"]
        self.assertTrue(any(item["state"] == "failure" and "Status: ready" in item["message"] for item in pending))
        self.assertTrue(any("unresolved required placeholders" in item["message"] for item in pending))
        self.assertEqual(report["scopes"]["project"]["result"], "fail")
        self.assertIn("Setup: pending", self.command("project", "status", expected=1).stdout)
        self.assertEqual(before, self.snapshot())

    def test_legacy_evidence_and_automation_restore_preexisting_metadata(self):
        code = (ROOT / "scripts/project.py").read_text().replace("contextrivet", "dev-agent-config").replace(
            "ROOT = Path(__file__).resolve().parent.parent", "ROOT = Path(" + repr(str(ROOT)) + ")")
        initialized = subprocess.run([sys.executable, "-B", "-c", code, "init", "--stack", "flutter"],
                                     cwd=self.project, env=self.env, text=True, capture_output=True)
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        manager = self.project / ".agents/dev-agent-config"
        evidence = manager / "evidence.json"
        original = b'{"version": 1, "notes": {}}\n'
        evidence.write_bytes(original)
        evidence.chmod(0o600)
        (self.project / "source.txt").write_text("Legacy source\n")
        note = ".agents/knowledge/legacy.md"
        (self.project / note).write_text("Source: `source.txt`\n")
        self.command("project", "baseline", "--note", note, "--yes")
        self.command("project", "automate", "--ci", "--apply")
        recorded = self.active_content()
        self.command("project", "uninstall", "--yes")
        self.assertEqual(evidence.read_bytes(), original)
        self.assertEqual(evidence.stat().st_mode & 0o777, 0o600)
        self.assertFalse((manager / "installed.json").exists())
        self.assertFalse((manager / "checker/scripts/maintenance.py").exists())
        recovery = next(file.parent.name for file in (manager / "backups").glob("*/manifest.json") if json.loads(file.read_text())["action"] == "uninstall")
        self.command("project", "restore", "--backup", recovery, "--yes")
        self.assertEqual(recorded, self.active_content())
        self.assertFalse((self.project / ".agents/contextrivet").exists())

    def test_automation_records_participate_in_restore_and_uninstall(self):
        self.ready()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True, env=self.env)
        original = self.active_content()
        self.command("project", "automate", "--hook", "--ci", "--apply")
        recorded = self.active_content()
        ownership = self.project / ".agents/contextrivet/installed.json"
        owned = json.loads(ownership.read_text())["files"]
        for relative in (".git/hooks/pre-commit", ".github/workflows/contextrivet.yml", ".agents/contextrivet/checker/scripts/maintenance.py"):
            self.assertIn(relative, owned)
        manifests = self.project / ".agents/contextrivet/backups"
        setup = next(file.parent.name for file in manifests.glob("*/manifest.json") if json.loads(file.read_text())["action"] == "automate")
        self.command("project", "restore", "--backup", setup, "--yes")
        self.assertEqual(original, self.active_content())
        recovery = next(file.parent.name for file in manifests.glob("*/manifest.json") if json.loads(file.read_text())["action"] == "restore")
        self.command("project", "restore", "--backup", recovery, "--yes")
        self.assertEqual(recorded, self.active_content())
        hook = self.project / ".git/hooks/pre-commit"
        hook.write_text(hook.read_text() + "\n# Later customization\n")
        customized = self.active_content()
        self.command("project", "uninstall", "--yes")
        self.assertTrue(hook.exists(), "customized hook was removed")
        self.assertFalse((self.project / ".github/workflows/contextrivet.yml").exists())
        self.assertFalse((self.project / ".agents/contextrivet/checker/scripts/maintenance.py").exists())
        self.assertFalse(ownership.exists())
        uninstall = next(file.parent.name for file in manifests.glob("*/manifest.json") if json.loads(file.read_text())["action"] == "uninstall")
        self.command("project", "restore", "--backup", uninstall, "--yes")
        self.assertEqual(customized, self.active_content())

    def test_baseline_and_automation_failures_restore_ownership(self):
        self.ready()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True, env=self.env)
        (self.project / "source.txt").write_text("Source fixture\n")
        note = ".agents/knowledge/features/failure.md"
        path = self.project / note
        path.parent.mkdir()
        path.write_text("Source: `source.txt`\n")
        sys.path.insert(0, str(ROOT / "scripts"))
        self.addCleanup(lambda: sys.path.remove(str(ROOT / "scripts")))
        module = importlib.import_module("maintenance")
        module.p.select_namespace(self.project, "baseline")
        original = self.active_content()
        for action in ("baseline", "automate"):
            failed = False
            write = module.p.atomic_write

            def fail_after_metadata_write(path, content, mode=None):
                nonlocal failed
                write(path, content, mode)
                if path == self.project / module.p.OWNERSHIP and not failed:
                    failed = True
                    raise OSError("simulated metadata write failure")

            args = type("Args", (), dict(note=note, yes=True, dry_run=False, hook=True, ci=True, local=False, apply=True))()
            with patch.dict(os.environ, self.env, clear=True), patch.object(module.p, "atomic_write", side_effect=fail_after_metadata_write):
                with self.assertRaises(OSError):
                    getattr(module, action)(self.project, args)
            self.assertEqual(original, self.active_content(), action + " left partial ownership")

    def test_hooks_preserved_hookspath_explained_ci_works_without_home(self):
        self.ready()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True, env=self.env)
        before = self.snapshot()
        self.command("project", "automate", "--hook", "--ci")
        self.assertEqual(before, self.snapshot())
        hook = self.project / ".git/hooks/pre-commit"
        hook.write_text("custom hook\n")
        self.command("project", "automate", "--hook", "--ci", "--apply", expected=1)
        self.assertEqual(hook.read_text(), "custom hook\n")
        self.assertFalse((self.project / ".github").exists())
        hook.unlink()
        subprocess.run(["git", "-C", str(self.project), "config", "core.hooksPath", "custom-hooks"], check=True, env=self.env)
        self.assertIn("core.hooksPath", self.command("project", "automate", "--hook", "--apply", expected=1).stderr)
        subprocess.run(["git", "-C", str(self.project), "config", "--unset", "core.hooksPath"], check=True, env=self.env)
        self.command("project", "automate", "--hook", "--ci", "--apply")
        before = self.snapshot()
        self.command("project", "automate", "--hook", "--ci", "--apply")
        self.assertEqual(before, self.snapshot())
        script = self.project / ".agents/contextrivet/checker/scripts/maintenance.py"
        report = subprocess.run([sys.executable, str(script), "--project-only", "--json"], cwd=self.project, env=self.env, text=True, capture_output=True)
        self.assertEqual(report.returncode, 0, report.stderr + report.stdout)
        self.assertEqual(json.loads(report.stdout)["scopes"]["global"]["result"], "skipped")
        self.assertEqual((self.project / ".agents/contextrivet/checker/LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
        self.assertFalse(list(script.parent.rglob("__pycache__")))
        self.assertEqual(list(self.home.iterdir()), [])
        subprocess.run([str(hook)], cwd=self.project, env=self.env, check=True, capture_output=True)
        (self.project / ".github/workflows/contextrivet.yml").unlink()
        disabled = self.health()
        self.assertTrue(any(item["id"] == "automation.disabled" and item["state"] == "optional" for item in disabled["findings"]))
        before = self.snapshot()
        self.command("project", "repair", "--apply")
        self.assertEqual(before, self.snapshot(), "repair re-enabled optional automation")

    def test_project_repair_rolls_back_a_failed_write(self):
        self.command("project", "init")
        for name in ("stack", "workflow"):
            (self.project / (".agents/instructions/" + name + ".md")).unlink()
        sys.path.insert(0, str(ROOT / "scripts"))
        self.addCleanup(lambda: sys.path.remove(str(ROOT / "scripts")))
        module = importlib.import_module("maintenance")
        module.p.select_namespace(self.project, "repair")
        write = module.p.atomic_write
        count = 0

        def fail_once(path, content, mode=None):
            nonlocal count
            if "backups" not in path.parts:
                count += 1
                if count == 2:
                    raise OSError("simulated write failure")
            return write(path, content, mode)

        with patch.object(module.p, "atomic_write", side_effect=fail_once):
            before = self.active_content()
            with self.assertRaises(OSError):
                module.repair(self.project, type("Args", (), {"apply": True})())
        self.assertEqual(before, self.active_content(), "repair failure changed config or ownership")
        for name in ("stack", "workflow"):
            self.assertFalse((self.project / (".agents/instructions/" + name + ".md")).exists())


if __name__ == "__main__":
    unittest.main()
