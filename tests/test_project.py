#!/usr/bin/env python3
"""Project setup integration checks using disposable directories and the real CLI."""
import json
import os
from pathlib import Path
import re
import runpy
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "contextrivet"
STATE = ".agents/contextrivet/project.json"
OWNERSHIP = ".agents/contextrivet/installed.json"
BACKUPS = ".agents/contextrivet/backups"


class ProjectSetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.project = self.base / "project with spaces"
        self.project.mkdir()
        self.home = self.base / "home"
        self.home.mkdir()

    def run_cli(self, *arguments, expected=0, cwd=None, infer_stack=False):
        if not infer_stack and arguments and arguments[0] == "init" and "--stack" not in arguments:
            target = Path(arguments[arguments.index("--project") + 1]) if "--project" in arguments else Path(cwd or self.project)
            if not any((target / ".agents" / name / "project.json").exists() for name in ("contextrivet", "dev-agent-config")):
                arguments += ("--stack", "nextjs")
        result = subprocess.run(
            [str(CLI), "project", *arguments],
            cwd=str(cwd or self.project),
            env=dict(os.environ, HOME=str(self.home)),
            input="", text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual(list(self.home.iterdir()), [], "project setup changed global configuration")
        return result

    def snapshot(self):
        return {str(path.relative_to(self.project)): path.read_bytes()
                for path in self.project.rglob("*") if path.is_file()}

    def make_ready(self):
        for name in ("PROJECT.md", "ARCHITECTURE.md"):
            path = self.project / ".agents" / name
            content = path.read_text().replace("Status: pending", "Status: ready")
            path.write_text(re.sub(r"\[REQUIRED: ([^\]]+)\]", r"Resolved fixture: \1", content))

    def history(self):
        return {path.parent.name: json.loads(path.read_text())
                for path in sorted((self.project / BACKUPS).glob("*/manifest.json"))}

    def active_files(self):
        return {path: content for path, content in self.snapshot().items() if not path.startswith(BACKUPS + "/")}

    def test_help_and_dry_run_are_read_only(self):
        self.assertIn("init", self.run_cli("--help").stdout)
        self.run_cli("init", "--help")
        self.run_cli("status", "--help")
        for action in ("backups", "restore", "uninstall"):
            self.run_cli(action, "--help")
        result = self.run_cli("init", "--project", str(self.project), "--agents", "codex,claude",
                              "--dry-run", cwd=self.base)
        self.assertIn("WOULD_CREATE", result.stdout)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_canonical_only_and_independent_skill_choice(self):
        self.run_cli("init", "--canonical", ".agents/AGENTS.md", "--skills", "none")
        self.assertTrue((self.project / ".agents/AGENTS.md").is_file())
        for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", ".clinerules", ".agents/skills"):
            self.assertFalse((self.project / name).exists())
        config = json.loads((self.project / STATE).read_text())
        self.assertEqual(config["agents"], [])
        self.assertFalse(config["skills"])

    def test_single_agent_does_not_create_other_entries(self):
        self.run_cli("init", "--agents", "claude", "--canonical", "CLAUDE.md", "--stack", "flutter")
        self.assertTrue((self.project / "CLAUDE.md").is_file())
        self.assertFalse((self.project / "AGENTS.md").exists())
        self.assertFalse((self.project / "GEMINI.md").exists())
        self.assertEqual((self.project / ".agents/instructions/stack.md").read_bytes(),
                         (ROOT / "templates/project/stacks/flutter.md").read_bytes())
        self.assertFalse((self.project / "pubspec.yaml").exists())

    def test_all_canonicals_route_selected_agents_without_canonical_loop(self):
        for canonical in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", ".agents/AGENTS.md"):
            project = self.base / canonical.replace("/", "-")
            project.mkdir()
            self.run_cli("init", "--project", str(project), "--canonical", canonical,
                         "--agents", "codex,claude,gemini,opencode,cline,antigravity")
            main = (project / canonical).read_text()
            self.assertIn(".agents/PROJECT.md", main)
            for entry in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", ".clinerules/00-contextrivet.md"):
                if entry != canonical:
                    self.assertIn("`" + canonical + "`", (project / entry).read_text())
            self.run_cli("status", "--project", str(project), expected=1)

    def test_existing_rules_are_backed_up_and_private_mode_preserved(self):
        path = self.project / "AGENTS.md"
        original = b"Keep my custom rule exactly.\n"
        path.write_bytes(original)
        path.chmod(0o600)
        self.run_cli("init", "--agents", "codex", "--yes")
        self.assertTrue(path.read_bytes().startswith(original))
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        backups = list((self.project / ".agents/contextrivet/backups").rglob("AGENTS.md"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)

    def test_repeat_preserves_customized_documents_and_rules(self):
        self.run_cli("init", "--agents", "claude", "--stack", "nextjs")
        for name in ("AGENTS.md", ".agents/ARCHITECTURE.md", ".agents/skills/ponytail/SKILL.md"):
            path = self.project / name
            path.write_text(path.read_text() + "\nMy project-specific additions.\n")
        before = self.snapshot()
        self.run_cli("init")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(list((self.project / ".agents/contextrivet/backups").glob("*/manifest.json"))), 1)
        self.assertEqual(list(self.project.glob(".contextrivet-*")), [])

    def test_existing_documents_are_not_replaced(self):
        path = self.project / ".agents/ARCHITECTURE.md"
        path.parent.mkdir()
        path.write_text("# My existing architecture\nSee docs/architecture.md\n")
        self.run_cli("init", "--yes")
        self.assertEqual(path.read_text(), "# My existing architecture\nSee docs/architecture.md\n")
        self.run_cli("status", expected=1)

    def test_adding_agents_preserves_existing_selection(self):
        self.run_cli("init", "--agents", "claude", "--skills", "none")
        rules = (self.project / "AGENTS.md").read_bytes()
        before = self.snapshot()
        self.run_cli("init", "--agents", "gemini, gemini", "--skills", "ponytail", expected=1)
        self.assertEqual(self.snapshot(), before)
        self.run_cli("init", "--agents", "gemini, gemini", "--skills", "ponytail", "--yes")
        config = json.loads((self.project / STATE).read_text())
        self.assertEqual(config["agents"], ["claude", "gemini"])
        self.assertTrue(config["skills"])
        self.assertEqual((self.project / "AGENTS.md").read_bytes(), rules)
        self.assertTrue((self.project / ".agents/skills/ponytail/SKILL.md").is_file())
        self.run_cli("init", "--agents", "none", "--skills", "none")
        self.assertTrue((self.project / "GEMINI.md").is_file())
        self.assertTrue((self.project / ".agents/skills/ponytail/SKILL.md").is_file())

    def test_status_checks_readiness_routes_sections_and_resources(self):
        self.run_cli("status", expected=1)
        self.run_cli("init", "--agents", "claude")
        before = self.snapshot()
        self.assertIn("Setup: pending", self.run_cli("status", expected=1).stdout)
        self.assertEqual(self.snapshot(), before)
        self.make_ready()
        self.assertIn("Setup: ready", self.run_cli("status").stdout)
        path = self.project / ".agents/PROJECT.md"
        ready = path.read_text()
        for broken in (ready.replace("## Scope", "## Unknown"),
                       re.sub(r"## Scope\n.*?(?=## Stack)", "## Scope\n\n", ready, flags=re.DOTALL),
                       ready + "\n[REQUIRED: Unresolved constraint]\n",
                       ready + "\nStatus: pending\n"):
            path.write_text(broken)
            self.run_cli("status", expected=1)
        path.write_text(ready)
        route = self.project / "CLAUDE.md"
        content = route.read_text()
        route.write_text(content.replace("AGENTS.md", "WRONG_AGENTS.md"))
        self.assertIn("missing project instruction route", self.run_cli("status", expected=1).stdout)
        route.write_text(content)
        (self.project / ".agents/instructions/workflow.md").unlink()
        self.run_cli("status", expected=1)

    def test_existing_agent_setup_requires_consent_even_without_overlapping_files(self):
        for index, relative in enumerate(("AGENTS.md", "CLAUDE.md", "GEMINI.md", "agents.md",
                         ".agents/README.md", ".agents/architecture.md",
                         ".agents/knowledge/README.md", ".agents/skills/custom/SKILL.md",
                         ".agent/rules/custom.md", ".clinerules", ".claude/rules/custom.md",
                         ".gemini/settings.json", ".opencode/instructions.md", ".cline/rules/custom.md")):
            with self.subTest(relative=relative):
                project = self.base / ("consent-" + str(index))
                path = project / relative
                path.parent.mkdir(parents=True)
                original = "Existing project guidance\n"
                path.write_text(original)
                result = self.run_cli("init", "--project", str(project), expected=1)
                self.assertIn("Consent required", result.stdout)
                self.assertIn("Existing agent setup detected", result.stdout)
                self.assertNotIn("\nCREATED ", result.stdout)
                self.assertNotIn("\nAPPENDED ", result.stdout)
                self.assertEqual(path.read_text(), original)
                self.assertEqual([p for p in project.rglob("*") if p.is_file()], [path])

    def test_existing_setup_dry_run_never_applies_or_prompts_even_with_yes(self):
        path = self.project / "AGENTS.md"
        path.write_text("Existing rule\n")
        before = self.snapshot()
        for flags in (("--dry-run",), ("--dry-run", "--yes")):
            result = self.run_cli("init", *flags)
            self.assertIn("WOULD_APPEND AGENTS.md", result.stdout)
            self.assertIn("WOULD_CREATE .agents/PROJECT.md", result.stdout)
            self.assertIn("Existing agent setup detected", result.stdout)
            self.assertNotIn("[y/N]", result.stdout)
            self.assertNotIn("Consent supplied", result.stdout)
            self.assertEqual(self.snapshot(), before)

    def test_explicit_consent_allows_additive_setup_and_is_not_remembered(self):
        router = self.project / ".agents/README.md"
        router.parent.mkdir()
        router.write_text("Keep this router\n")
        self.run_cli("init", expected=1)
        result = self.run_cli("init", "--yes")
        self.assertIn("Consent supplied with --yes", result.stdout)
        self.assertIn("CREATED AGENTS.md", result.stdout)
        self.assertEqual(router.read_text(), "Keep this router\n")
        before = self.snapshot()
        result = self.run_cli("init")
        self.assertIn("UNCHANGED", result.stdout)
        self.assertNotIn("Consent required", result.stdout)
        self.assertEqual(self.snapshot(), before)
        (self.project / ".agents/instructions/workflow.md").unlink()
        before = self.snapshot()
        self.run_cli("init", expected=1)
        self.assertEqual(self.snapshot(), before)
        self.run_cli("init", "--yes")
        self.assertTrue((self.project / ".agents/instructions/workflow.md").is_file())

    def test_terminal_confirmation_defaults_to_no_and_handles_interruption(self):
        confirm = runpy.run_path(str(ROOT / "scripts/project.py"))["confirm_existing_setup"]
        (self.project / "AGENTS.md").write_text("Existing rules\n")
        before = self.snapshot()
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.print"):
            for answer, approved in (("", False), ("n", False), ("no", False), ("anything", False),
                                     ("y", True), ("YES", True), (" yes ", True)):
                with patch("builtins.input", return_value=answer) as prompt:
                    self.assertEqual(confirm(self.project, False), approved)
                    self.assertIn("[y/N]", prompt.call_args[0][0])
            for error in (EOFError, KeyboardInterrupt):
                with patch("builtins.input", side_effect=error):
                    self.assertFalse(confirm(self.project, False))
            with patch("builtins.input") as prompt:
                self.assertTrue(confirm(self.project, True))
                self.assertTrue(confirm(self.project, False, dry_run=True))
                prompt.assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_invalid_input_and_migrations_never_mutate(self):
        self.run_cli("init", "--agents", "unknown", expected=1)
        self.run_cli("init", "--canonical", "../AGENTS.md", expected=2)
        missing = self.base / "does not exist"
        self.run_cli("init", "--project", str(missing), expected=1)
        self.assertFalse(missing.exists())
        self.assertEqual(list(self.project.iterdir()), [])
        self.run_cli("init")
        before = self.snapshot()
        self.run_cli("init", "--canonical", "CLAUDE.md", expected=1)
        self.run_cli("init", "--stack", "flutter", expected=1)
        self.assertEqual(self.snapshot(), before)

    def test_corrupt_metadata_does_not_control_paths(self):
        self.run_cli("init")
        path = self.project / STATE
        for invalid in ("[]", "{", '{"version": 1}',
                        json.dumps(dict(version=1, canonical="../../escape", stack="generic", skills=True, agents=[])),
                        json.dumps(dict(version=1, canonical="AGENTS.md", stack="generic", skills=True, agents=[{}]))):
            path.write_text(invalid)
            before = self.snapshot()
            self.run_cli("init", expected=1)
            self.run_cli("status", expected=1)
            self.assertEqual(self.snapshot(), before)

    def test_symlinks_and_non_file_targets_are_rejected_before_writes(self):
        outside = self.base / "outside"
        outside.mkdir()
        for relative in (".agents", ".agents/PROJECT.md", ".agents/contextrivet",
                         ".clinerules", "GEMINI.md"):
            project = self.base / ("unsafe-" + relative.replace("/", "-"))
            project.mkdir()
            target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(outside, target_is_directory=True)
            before = sorted(str(path.relative_to(project)) for path in project.rglob("*"))
            self.run_cli("init", "--project", str(project), "--agents", "cline,gemini", expected=1)
            self.assertEqual(sorted(str(path.relative_to(project)) for path in project.rglob("*")), before)
            self.assertEqual(list(outside.iterdir()), [])
        (self.project / "AGENTS.md").mkdir()
        self.run_cli("init", expected=1)
        self.assertFalse((self.project / ".agents").exists())

    def test_malformed_markers_and_codex_override_fail_before_writes(self):
        path = self.project / "AGENTS.md"
        for content in ("# >>> contextrivet project >>>\n", "# <<< contextrivet project <<<\n",
                        "# <<< contextrivet project <<<\n# >>> contextrivet project >>>\n"):
            path.write_text(content)
            self.run_cli("init", expected=1)
            self.assertEqual(path.read_text(), content)
            self.assertFalse((self.project / ".agents").exists())
        path.unlink()
        override = self.project / "AGENTS.override.md"
        override.write_text("Override rules\n")
        self.run_cli("init", "--agents", "codex", expected=1)
        self.assertFalse((self.project / ".agents").exists())
        self.run_cli("init", "--agents", "claude", "--yes")

    def test_local_copy_does_not_depend_on_checkout_links(self):
        self.run_cli("init", "--stack", "nestjs")
        for path in self.project.rglob("*"):
            self.assertFalse(path.is_symlink())
        skill = self.project / ".agents/skills/ponytail/SKILL.md"
        self.assertEqual(skill.read_bytes(), (ROOT / "skills/ponytail/SKILL.md").read_bytes())
        self.assertNotIn(str(ROOT), (self.project / "AGENTS.md").read_text())

    def test_project_symlink_and_explicit_path_resolve_to_same_setup(self):
        alias = self.base / "project alias"
        alias.symlink_to(self.project, target_is_directory=True)
        self.run_cli("init", "--project", str(alias), "--agents", "opencode")
        before = self.snapshot()
        self.run_cli("init", "--project", str(self.project), cwd=self.base)
        self.assertEqual(self.snapshot(), before)
        self.make_ready()
        self.run_cli("status", "--project", str(alias), cwd=self.base)

    def test_init_tracks_creation_originals_and_ownership_across_runs(self):
        original = self.project / "AGENTS.md"
        original.write_bytes(b"My original rules\r\n")
        original.chmod(0o600)
        self.run_cli("init", "--yes")
        first_id = next(iter(self.history()))
        self.assertTrue(original.read_bytes().startswith(b"My original rules\r\n"))
        first = self.history()[first_id]["files"]
        self.assertIsNone(first[".agents/PROJECT.md"]["before_sha256"])
        self.assertEqual(first["AGENTS.md"]["before_mode"], 0o600)
        self.assertEqual((self.project / BACKUPS / first_id / "AGENTS.md").read_bytes(), b"My original rules\r\n")
        self.run_cli("init", "--agents", "claude", "--yes")
        owned = json.loads((self.project / OWNERSHIP).read_text())["files"]
        self.assertEqual(owned["AGENTS.md"]["backup"], first_id)
        self.assertIn("CLAUDE.md", owned)
        self.assertEqual(len(self.history()), 2)

    def test_uninstall_previews_and_requires_consent_without_writing(self):
        self.run_cli("init")
        before = self.snapshot()
        result = self.run_cli("uninstall", "--dry-run")
        self.assertIn("WOULD_REMOVE AGENTS.md", result.stdout)
        self.run_cli("uninstall", expected=1)
        self.assertEqual(self.snapshot(), before)
        result = self.run_cli("uninstall", "--dry-run", "--yes")
        self.assertNotIn("REMOVED AGENTS.md", result.stdout.replace("WOULD_REMOVE AGENTS.md", ""))
        self.assertEqual(self.snapshot(), before)

    def test_uninstall_restores_original_files_and_retains_backups_and_untracked_files(self):
        original = self.project / "AGENTS.md"
        original.write_bytes(b"Keep exact original rules\n")
        original.chmod(0o600)
        architecture = self.project / ".agents/ARCHITECTURE.md"
        architecture.parent.mkdir()
        architecture.write_text("Existing architecture\n")
        self.run_cli("init", "--agents", "claude", "--yes")
        feature = self.project / ".agents/knowledge/features/custom.md"
        feature.parent.mkdir()
        feature.write_text("New feature memory\n")
        before = self.active_files()
        self.run_cli("uninstall", "--yes")
        self.assertEqual(original.read_bytes(), b"Keep exact original rules\n")
        self.assertEqual(stat.S_IMODE(original.stat().st_mode), 0o600)
        self.assertEqual(architecture.read_text(), "Existing architecture\n")
        self.assertEqual(feature.read_text(), "New feature memory\n")
        for relative in ("CLAUDE.md", ".agents/PROJECT.md", STATE, OWNERSHIP):
            self.assertFalse((self.project / relative).exists())
        history = self.history()
        recovery = next(identifier for identifier, manifest in history.items() if manifest["action"] == "uninstall")
        self.assertIn(recovery, self.run_cli("backups").stdout)
        self.run_cli("uninstall", "--yes")
        self.assertEqual(len(self.history()), 2)
        self.run_cli("restore", "--backup", recovery, "--yes")
        self.assertEqual(self.active_files(), before)

    def test_uninstall_preserves_modified_documents_and_later_unrelated_rules(self):
        root = self.project / "AGENTS.md"
        root.write_text("Original private rule\n")
        self.run_cli("init", "--yes")
        root.write_text(root.read_text() + "\nLater unrelated rule\n")
        context = self.project / ".agents/PROJECT.md"
        context.write_text("Completed project-specific context\n")
        result = self.run_cli("uninstall", "--yes")
        self.assertIn("KEPT modified project file: .agents/PROJECT.md", result.stdout)
        self.assertEqual(context.read_text(), "Completed project-specific context\n")
        self.assertIn("Original private rule", root.read_text())
        self.assertIn("Later unrelated rule", root.read_text())
        self.assertNotIn("# >>> contextrivet project >>>", root.read_text())

    def test_force_uninstall_saves_modified_owned_files_for_recovery(self):
        self.run_cli("init")
        context = self.project / ".agents/PROJECT.md"
        context.write_text("Important customized context\n")
        before = self.active_files()
        self.run_cli("uninstall", "--force", "--yes")
        self.assertFalse(context.exists())
        recovery = next(identifier for identifier, manifest in self.history().items() if manifest["action"] == "uninstall")
        saved = self.project / BACKUPS / recovery / ".agents/PROJECT.md"
        self.assertEqual(saved.read_text(), "Important customized context\n")
        self.assertEqual(stat.S_IMODE(saved.stat().st_mode), 0o600)
        self.run_cli("restore", "--backup", recovery, "--yes")
        self.assertEqual(self.active_files(), before)

    def test_restore_reverses_selected_init_and_keeps_recovery_history(self):
        self.run_cli("init", "--agents", "codex")
        first_id = next(iter(self.history()))
        first = self.active_files()
        self.run_cli("init", "--agents", "claude", "--yes")
        second_id = next(identifier for identifier in self.history() if identifier != first_id)
        before = self.snapshot()
        self.run_cli("restore", "--backup", second_id, "--dry-run")
        self.run_cli("restore", "--backup", second_id, expected=1)
        self.assertEqual(self.snapshot(), before)
        self.run_cli("restore", "--backup", second_id, "--yes")
        self.assertEqual(self.active_files(), first)
        self.run_cli("restore", "--backup", first_id, "--yes")
        self.assertEqual(self.active_files(), {})
        self.assertEqual(len(self.history()), 4)

    def test_restore_refuses_later_edits_until_force_and_saves_them(self):
        self.run_cli("init")
        identifier = next(iter(self.history()))
        context = self.project / ".agents/PROJECT.md"
        context.write_text("Important new facts\n")
        before = self.snapshot()
        self.run_cli("restore", "--backup", identifier, "--yes", expected=1)
        self.assertEqual(self.snapshot(), before)
        self.run_cli("restore", "--backup", identifier, "--force", "--dry-run")
        self.assertEqual(self.snapshot(), before)
        self.run_cli("restore", "--backup", identifier, "--force", "--yes")
        self.assertFalse(context.exists())
        recovery = next(key for key, manifest in self.history().items() if manifest["action"] == "restore")
        self.assertEqual((self.project / BACKUPS / recovery / ".agents/PROJECT.md").read_text(), "Important new facts\n")

    def test_changed_backups_and_invalid_history_paths_are_refused(self):
        root = self.project / "AGENTS.md"
        root.write_text("Original rules\n")
        self.run_cli("init", "--yes")
        identifier = next(iter(self.history()))
        saved = self.project / BACKUPS / identifier / "AGENTS.md"
        saved.write_text("Changed backup\n")
        before = self.snapshot()
        self.run_cli("uninstall", "--yes", expected=1)
        self.run_cli("restore", "--backup", identifier, "--force", "--yes", expected=1)
        self.assertEqual(self.snapshot(), before)
        manifest = self.project / BACKUPS / identifier / "manifest.json"
        data = json.loads(manifest.read_text())
        data["files"]["../../escape"] = data["files"]["AGENTS.md"]
        manifest.write_text(json.dumps(data))
        before = self.snapshot()
        self.run_cli("restore", "--backup", identifier, "--force", "--yes", expected=1)
        self.run_cli("restore", "--backup", "../escape", "--yes", expected=1)
        self.assertEqual(self.snapshot(), before)

    def test_symlinked_history_and_targets_are_refused_before_removal(self):
        self.run_cli("init")
        identifier = next(iter(self.history()))
        outside = self.base / "outside"
        outside.write_text("Outside content\n")
        context = self.project / ".agents/PROJECT.md"
        context.unlink()
        context.symlink_to(outside)
        before = self.snapshot()
        self.run_cli("uninstall", "--force", "--yes", expected=1)
        self.run_cli("restore", "--backup", identifier, "--force", "--yes", expected=1)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(outside.read_text(), "Outside content\n")
        context.unlink()
        manifest = self.project / BACKUPS / identifier / "manifest.json"
        manifest.unlink()
        manifest.symlink_to(outside)
        self.run_cli("backups", expected=1)
        self.run_cli("restore", "--backup", identifier, "--yes", expected=1)

    def test_legacy_backups_restore_originals_without_guessing_file_ownership(self):
        root = self.project / "AGENTS.md"
        root.write_text("Original legacy rules\n")
        self.run_cli("init", "--yes")
        identifier = next(iter(self.history()))
        (self.project / BACKUPS / identifier / "manifest.json").unlink()
        (self.project / OWNERSHIP).unlink()
        before = self.snapshot()
        self.assertIn("legacy", self.run_cli("backups").stdout)
        self.run_cli("restore", "--backup", identifier, "--dry-run")
        self.assertEqual(self.snapshot(), before)
        self.run_cli("restore", "--backup", identifier, "--yes")
        self.assertEqual(root.read_text(), "Original legacy rules\n")
        self.assertTrue((self.project / ".agents/PROJECT.md").exists())
        self.run_cli("uninstall", "--force", "--yes")
        self.assertEqual(root.read_text(), "Original legacy rules\n")
        self.assertTrue((self.project / ".agents/PROJECT.md").exists())
        self.assertFalse((self.project / STATE).exists())
        self.assertIn(identifier, self.run_cli("backups").stdout)

    def test_malformed_rules_and_ownership_refuse_uninstall_without_changes(self):
        self.run_cli("init")
        root = self.project / "AGENTS.md"
        root.write_text(root.read_text().replace("# <<< contextrivet project <<<", "Missing end marker"))
        before = self.snapshot()
        self.run_cli("uninstall", "--yes", expected=1)
        self.assertEqual(self.snapshot(), before)
        ownership = self.project / OWNERSHIP
        data = json.loads(ownership.read_text())
        data["files"][".git/config"] = data["files"]["AGENTS.md"]
        ownership.write_text(json.dumps(data))
        before = self.snapshot()
        self.run_cli("uninstall", "--force", "--yes", expected=1)
        self.assertEqual(self.snapshot(), before)

    def test_backup_listing_and_uninstall_on_uninitialized_project_are_read_only(self):
        self.assertIn("No project backups", self.run_cli("backups").stdout)
        self.run_cli("uninstall", "--yes")
        self.assertEqual(list(self.project.iterdir()), [])

    def test_stack_inference_reads_manifests_without_generating_app_code(self):
        fixtures = {
            "nestjs": ("package.json", json.dumps({"dependencies": {"@nestjs/core": "fixture"}})),
            "nextjs": ("package.json", json.dumps({"devDependencies": {"next": "fixture"}})),
            "flutter": ("pubspec.yaml", "name: fixture\ndependencies:\n  flutter:\n    sdk: flutter\n"),
        }
        for stack, (manifest, content) in fixtures.items():
            with self.subTest(stack=stack):
                project = self.base / stack
                project.mkdir()
                (project / manifest).write_text(content)
                self.run_cli("init", "--project", str(project), infer_stack=True)
                config = json.loads((project / STATE).read_text())
                self.assertEqual(config["stack"], stack)
                self.assertEqual((project / manifest).read_text(), content)
                self.assertEqual((project / ".agents/instructions/stack.md").read_bytes(),
                                 (ROOT / "templates/project/stacks" / (stack + ".md")).read_bytes())

    def test_missing_ambiguous_or_unsupported_stacks_do_not_write(self):
        self.run_cli("init", infer_stack=True, expected=1)
        self.assertEqual(list(self.project.iterdir()), [])
        package = self.project / "package.json"
        for dependencies in ({"react": "fixture"}, {"next": "fixture", "@nestjs/core": "fixture"}):
            package.write_text(json.dumps({"dependencies": dependencies}))
            before = self.snapshot()
            self.run_cli("init", infer_stack=True, expected=1)
            self.assertEqual(self.snapshot(), before)
        for stack in ("generic", "backend", "react"):
            self.run_cli("init", "--stack", stack, expected=2)
            self.run_cli("skills", "--stack", stack, expected=2)
        self.run_cli("init", "--stack", "nestjs")
        self.assertEqual(json.loads((self.project / STATE).read_text())["stack"], "nestjs")

    def test_old_stack_profiles_still_support_status_and_removal(self):
        self.run_cli("init")
        path = self.project / STATE
        config = json.loads(path.read_text())
        config["stack"] = "generic"
        path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")
        self.assertIn("Setup: pending", self.run_cli("status", expected=1).stdout)
        self.run_cli("init")
        self.assertEqual(json.loads(path.read_text())["stack"], "generic")
        self.run_cli("uninstall", "--yes")
        self.assertFalse(path.exists())

    def test_skill_reference_index_is_selected_by_stack_and_not_a_download(self):
        helpers = runpy.run_path(str(ROOT / "scripts/project.py"))
        catalog_dir = self.base / "skills"
        catalog_dir.mkdir()
        catalog = {"version": 1, "stacks": {"nestjs": [
            {"name": "nest-patterns", "description": "Fixture Nest conventions", "github_url": "https://github.com/example/skills/tree/fixture/nest-patterns"}
        ], "nextjs": [], "flutter": [
            {"name": "flutter-patterns", "description": "Fixture Flutter conventions", "github_url": "https://github.com/example/skills/tree/fixture/flutter-patterns"}
        ]}}
        (catalog_dir / "stacks.json").write_text(json.dumps(catalog))
        with patch.dict(helpers["stack_skills"].__globals__, {"ROOT": self.base}):
            index = helpers["skill_index"]("nestjs")
            self.assertIn("nest-patterns", index)
            self.assertNotIn("flutter-patterns", index)
            self.assertIn("No custom GitHub skills", helpers["skill_index"]("nextjs"))
        self.assertEqual(list(self.project.iterdir()), [])
        for stack in ("nestjs", "nextjs"):
            self.assertIn("No custom GitHub skills", self.run_cli("skills", "--stack", stack).stdout)
        self.assertIn("flutter-async-state-safety", self.run_cli("skills", "--stack", "flutter").stdout)
        self.run_cli("init", "--stack", "nestjs")
        index = self.project / ".agents/skills/README.md"
        self.assertIn("Stack profile: nestjs", index.read_text())
        self.assertIn(".agents/skills/README.md", (self.project / "AGENTS.md").read_text())
        index.write_text("Keep project-specific skill choices\n")
        self.run_cli("init")
        self.assertEqual(index.read_text(), "Keep project-specific skill choices\n")

    def test_skill_catalog_rejects_invalid_references_and_duplicate_names(self):
        helpers = runpy.run_path(str(ROOT / "scripts/project.py"))
        catalog_dir = self.base / "skills"
        catalog_dir.mkdir()
        valid = {"name": "nest-patterns", "description": "Fixture conventions", "github_url": "https://github.com/example/skills"}
        cases = [
            [dict(valid, github_url="file:///private/example")],
            [dict(valid, github_url="https://github.com.evil.example/owner/repo")],
            [dict(valid, github_url="https://github.com/owner/repo\nnext")],
            [dict(valid, name="../escape")],
            [dict(valid, description="")],
            [valid, valid],
        ]
        with patch.dict(helpers["stack_skills"].__globals__, {"ROOT": self.base}):
            for entries in cases:
                (catalog_dir / "stacks.json").write_text(json.dumps({"version": 1, "stacks": {"nestjs": entries, "nextjs": [], "flutter": []}}))
                with self.assertRaises(ValueError):
                    helpers["stack_skills"]("nestjs")


if __name__ == "__main__":
    unittest.main()
