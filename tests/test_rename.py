#!/usr/bin/env python3
"""Check the new branding and access to configurations saved under the old name."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "contextrivet"


class RenameTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.project = self.base / "project"
        self.home = self.base / "home"
        self.project.mkdir()
        self.home.mkdir()

    def run_cli(self, *args, expected=0):
        if args[:2] == ("project", "init") and "--stack" not in args:
            if not any((self.project / ".agents" / name / "project.json").exists() for name in ("contextrivet", "dev-agent-config")):
                args += ("--stack", "nextjs")
        result = subprocess.run([str(CLI), *args], cwd=self.project,
                                env=dict(os.environ, HOME=str(self.home)), input="", text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def make_old_project(self):
        # Run the same initializer with its former constants so manifest hashes
        # and backup paths describe a real old-name installation.
        code = (ROOT / "scripts/project.py").read_text().replace("contextrivet", "dev-agent-config").replace(
            "ROOT = Path(__file__).resolve().parent.parent", "ROOT = Path(" + repr(str(ROOT)) + ")"
        )
        result = subprocess.run([sys.executable, "-c", code, "init", "--agents", "cline", "--stack", "nextjs", "--yes"],
                                cwd=self.project, env=dict(os.environ, HOME=str(self.home)),
                                input="", text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_new_cli_brand_and_generated_names(self):
        self.assertIn("contextrivet —", self.run_cli("--help").stdout)
        self.run_cli("project", "init", "--agents", "cline")
        self.assertTrue((self.project / ".agents/contextrivet/project.json").is_file())
        self.assertTrue((self.project / ".clinerules/00-contextrivet.md").is_file())
        self.assertFalse((self.project / ".agents/dev-agent-config").exists())
        self.assertIn("# >>> contextrivet project >>>", (self.project / "AGENTS.md").read_text())

    def test_old_project_keeps_working_without_duplicate_setup(self):
        original = self.project / "AGENTS.md"
        original.write_text("Existing project rule\n")
        self.make_old_project()
        before = {str(p.relative_to(self.project)): p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
        self.assertIn("Setup: pending", self.run_cli("project", "status", expected=1).stdout)
        self.assertIn("UNCHANGED", self.run_cli("project", "init").stdout)
        after = {str(p.relative_to(self.project)): p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertIn("dev-agent-config/backups", self.run_cli("project", "backups").stdout)
        self.run_cli("project", "uninstall", "--yes")
        self.assertEqual(original.read_text(), "Existing project rule\n")
        self.assertFalse((self.project / ".clinerules/00-dev-agent-config.md").exists())
        backups = self.project / ".agents/dev-agent-config/backups"
        recovery = next(p.parent.name for p in backups.glob("*/manifest.json")
                        if json.loads(p.read_text())["action"] == "uninstall")
        self.run_cli("project", "restore", "--backup", recovery, "--yes")
        self.assertTrue((self.project / ".clinerules/00-dev-agent-config.md").exists())
        self.assertFalse((self.project / ".agents/contextrivet").exists())

    def test_original_only_old_backup_remains_restorable(self):
        identifier = "20261027-155358-733474-48496"
        backup = self.project / ".agents/dev-agent-config/backups" / identifier
        backup.mkdir(parents=True)
        (backup / "AGENTS.md").write_text("Original saved rules\n")
        (self.project / "AGENTS.md").write_text("Current rules\n")
        self.assertIn(identifier, self.run_cli("project", "backups").stdout)
        self.run_cli("project", "restore", "--backup", identifier, "--dry-run")
        self.assertEqual((self.project / "AGENTS.md").read_text(), "Current rules\n")
        self.run_cli("project", "restore", "--backup", identifier, "--yes")
        self.assertEqual((self.project / "AGENTS.md").read_text(), "Original saved rules\n")

    def test_two_active_project_namespaces_require_reconciliation(self):
        self.make_old_project()
        current = self.project / ".agents/contextrivet/project.json"
        current.parent.mkdir()
        current.write_bytes((self.project / ".agents/dev-agent-config/project.json").read_bytes())
        result = self.run_cli("project", "uninstall", "--yes", expected=1)
        self.assertIn("Both contextrivet and dev-agent-config", result.stderr)
        self.assertTrue(current.is_file())

    def test_cli_link_install_replaces_only_owned_old_link(self):
        bin_dir = self.home / "bin"
        bin_dir.mkdir()
        old = bin_dir / "dev-agent-config"
        old.symlink_to(ROOT / "dev-agent-config")
        self.run_cli("cli", "install", "--bin-dir", str(bin_dir), "--dry-run")
        self.assertTrue(old.is_symlink())
        self.assertFalse((bin_dir / "contextrivet").exists())
        self.run_cli("cli", "install", "--bin-dir", str(bin_dir))
        self.assertFalse(old.is_symlink())
        self.assertEqual((bin_dir / "contextrivet").readlink(), CLI)
        old.symlink_to("/unrelated/old-command")
        self.run_cli("cli", "install", "--bin-dir", str(bin_dir))
        self.assertEqual(old.readlink(), Path("/unrelated/old-command"))

    def test_old_global_rules_are_migrated_without_duplicate_blocks(self):
        path = self.home / "AGENTS.md"
        original = "My personal rule\n\n# >>> dev-agent-config managed >>>\nOld shared rule\n# <<< dev-agent-config managed <<<\n"
        path.write_text(original)
        self.run_cli("install", "--dry-run")
        self.assertEqual(path.read_text(), original)
        self.run_cli("install")
        self.assertIn("My personal rule", path.read_text())
        self.assertEqual(path.read_text().count("# >>> contextrivet managed >>>"), 1)
        self.assertNotIn("# >>> dev-agent-config managed >>>", path.read_text())
        self.run_cli("rollback")
        self.assertEqual(path.read_text(), original)
        self.run_cli("uninstall", "--apply")
        self.assertEqual(path.read_text(), "My personal rule\n")

    def test_only_the_new_root_entry_point_exists(self):
        self.assertFalse((ROOT / "dev-agent-config").exists())
        self.assertFalse((ROOT / "dev-agent-config").is_symlink())
        self.assertTrue(CLI.is_file())
        self.assertIn("contextrivet —", self.run_cli("--help").stdout)

    def test_global_rollback_can_read_an_old_backup_location(self):
        identifier = "20261027-155358-12345"
        backup = self.home / ".agents/dev-agent-config/backups" / identifier
        saved = backup / "original/AGENTS.md"
        saved.parent.mkdir(parents=True)
        saved.write_text("Saved original global rule\n")
        target = self.home / "AGENTS.md"
        target.write_text("Current global rule\n")
        (backup / "manifest.tsv").write_text(
            "type\ttarget\tbackup\nfile\t{}\t{}\n".format(target, saved)
        )
        (self.home / ".agents/dev-agent-config/last-backup").write_text(str(backup) + "\n")
        self.run_cli("rollback", "--dry-run")
        self.assertEqual(target.read_text(), "Current global rule\n")
        self.run_cli("rollback")
        self.assertEqual(target.read_text(), "Saved original global rule\n")


if __name__ == "__main__":
    unittest.main()
