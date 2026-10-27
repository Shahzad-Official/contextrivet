#!/usr/bin/env python3
"""Remote skill installs using in-memory GitHub archives and disposable projects."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import stat
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile


ROOT = Path(__file__).resolve().parent.parent
COMMIT = "a" * 40
NAME = "flutter-architecture"
SKILL = ".agents/skills/" + NAME + "/"


def archive(files=None, license=True):
    data = io.BytesIO()
    if files is None:
        files = {
            "SKILL.md": "---\nname: " + NAME + "\ndescription: Fixture skill\n---\n# Fixture\n",
            "references/check.md": "# Reference\n",
            "scripts/never-run.py": "raise RuntimeError('must not execute')\n",
        }
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as output:
        if license:
            output.writestr("repo-commit/LICENSE", "Fixture source license\n")
        for path, content in files.items():
            output.writestr("repo-commit/" + NAME + "/" + path, content)
    return data.getvalue()


class SkillInstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name) / "project with spaces"
        self.project.mkdir()
        helpers = runpy.run_path(str(ROOT / "scripts/project.py"))
        self.main = helpers["main"]
        self.globals = self.main.__globals__
        self.entry = {"name": NAME, "description": "Fixture skill", "github_url":
                      "https://github.com/example/skills/tree/" + COMMIT + "/" + NAME}
        self.download = Mock(side_effect=lambda *args, **kwargs: io.BytesIO(archive()))
        self.addCleanup(patch.stopall)
        patch.dict(self.globals, {"urlopen": self.download}).start()
        self.call("init", "--stack", "flutter", "--skills", "none")
        patch.dict(self.globals, {"stack_skills": lambda stack: [self.entry]}).start()

    def call(self, *args, expected=0, project=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["project.py", *args, "--project", str(project or self.project)]), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr), \
                patch.object(sys.stdin, "isatty", return_value=False):
            result = self.main()
        self.assertEqual(result, expected, stdout.getvalue() + stderr.getvalue())
        return stdout.getvalue() + stderr.getvalue()

    def install(self, *args, expected=0):
        return self.call("skills", "install", "--names", NAME, *args, expected=expected)

    def snapshot(self):
        return {p.relative_to(self.project).as_posix(): p.read_bytes()
                for p in self.project.rglob("*") if p.is_file()}

    def history(self):
        return {p.parent.name: json.loads(p.read_text()) for p in
                (self.project / ".agents/contextrivet/backups").glob("*/manifest.json")}

    def test_dry_run_and_selection_errors_make_no_network_requests_or_changes(self):
        before = self.snapshot()
        self.assertIn("No network requests", self.install("--dry-run"))
        self.call("skills", "install", "--all", "--dry-run")
        self.call("skills", "install", expected=1)
        self.call("skills", "install", "--names", "unknown", expected=1)
        self.install("--stack", "nextjs", expected=1)
        self.install("--names", NAME + "," + NAME, expected=1)
        self.download.assert_not_called()
        self.assertEqual(before, self.snapshot())

    def test_requires_initialized_project_and_full_pinned_commit(self):
        other = self.project / "empty"
        other.mkdir()
        self.call("skills", "install", "--all", expected=1, project=other)
        self.entry["github_url"] = self.entry["github_url"].replace(COMMIT, "main")
        self.assertIn("40-character-commit", self.install("--dry-run", expected=1))
        self.download.assert_not_called()

    def test_declined_install_does_not_change_project(self):
        before = self.snapshot()
        self.assertIn("Consent required", self.install(expected=1))
        self.assertEqual(before, self.snapshot())

    def test_multiple_skills_share_one_archive_and_bad_selection_is_not_partly_applied(self):
        second = dict(self.entry, name="flutter-ui-quality", github_url=self.entry["github_url"].replace(NAME, "flutter-ui-quality"))
        self.globals["stack_skills"] = lambda stack: [self.entry, second]
        before = self.snapshot()
        # The first skill exists, but the second is absent: neither is applied.
        self.call("skills", "install", "--all", "--yes", expected=1)
        self.assertEqual(before, self.snapshot())
        self.download.assert_called_once()
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as output:
            output.writestr("repo/LICENSE", "Fixture license")
            for name in (NAME, second["name"]):
                output.writestr("repo/" + name + "/SKILL.md", "---\nname: " + name + "\ndescription: Fixture\n---\n")
        self.download.reset_mock()
        self.download.side_effect = lambda *args, **kwargs: io.BytesIO(data.getvalue())
        self.call("skills", "install", "--all", "--yes")
        self.download.assert_called_once()
        for name in (NAME, second["name"]):
            self.assertTrue((self.project / (".agents/skills/" + name + "/SKILL.md")).is_file())

    def test_restore_rejects_skill_paths_escaping_the_skills_directory(self):
        self.install("--yes")
        identifier = next(key for key, value in self.history().items() if value["action"] == "skills-install")
        manifest = self.project / ".agents/contextrivet/backups" / identifier / "manifest.json"
        value = json.loads(manifest.read_text())
        value["files"][".agents/skills/" + NAME + "/../../../outside"] = value["files"][SKILL + "SKILL.md"]
        manifest.write_text(json.dumps(value))
        before = self.snapshot()
        self.assertIn("Invalid managed paths", self.call("restore", "--backup", identifier, "--force", "--yes", expected=1))
        self.assertEqual(before, self.snapshot())

    def test_installs_complete_skill_license_source_and_is_idempotent(self):
        self.install("--yes")
        self.assertEqual((self.project / (SKILL + "references/check.md")).read_text(), "# Reference\n")
        self.assertTrue((self.project / (SKILL + "scripts/never-run.py")).is_file())
        self.assertEqual((self.project / (SKILL + "LICENSE")).read_text(), "Fixture source license\n")
        source = json.loads((self.project / (SKILL + ".contextrivet-source.json")).read_text())
        self.assertEqual(source["commit"], COMMIT)
        self.assertEqual(source["github_url"], self.entry["github_url"])
        owned = json.loads((self.project / ".agents/contextrivet/installed.json").read_text())["files"]
        self.assertIn(SKILL + "SKILL.md", owned)
        self.assertFalse((self.project / ".agents/skills/ponytail").exists())
        before = self.snapshot()
        self.assertIn("UNCHANGED", self.install("--yes"))
        self.assertEqual(before, self.snapshot())

    def test_existing_different_files_and_local_edits_are_preserved(self):
        path = self.project / (SKILL + "SKILL.md")
        path.parent.mkdir(parents=True)
        path.write_text("My custom skill\n")
        before = self.snapshot()
        self.assertIn("preserved", self.install("--yes", expected=1))
        self.assertEqual(before, self.snapshot())
        path.unlink()
        self.install("--yes")
        path.write_text(path.read_text() + "My local rule\n")
        before = self.snapshot()
        self.assertIn("preserved", self.install("--yes", expected=1))
        self.assertEqual(before, self.snapshot())

    def test_download_error_or_invalid_archive_makes_no_project_changes(self):
        before = self.snapshot()
        self.download.side_effect = OSError("offline")
        self.assertIn("offline", self.install("--yes", expected=1))
        self.download.side_effect = lambda *args, **kwargs: io.BytesIO(b"not a zip")
        self.assertIn("Invalid skill archive", self.install("--yes", expected=1))
        self.assertEqual(before, self.snapshot())

    def test_rejects_unsafe_archives_before_any_project_write(self):
        before = self.snapshot()
        cases = [
            archive({"references/only.md": "No entrypoint"}),
            archive({"SKILL.md": "---\nname: other\n---\n"}),
            archive(license=False),
            archive({"../escape": "evil"}),
            archive({"sub/../../escape": "evil"}),
            archive({".git/config": "evil"}),
            archive({".contextrivet-source.json": "fake provenance"}),
            archive({"large.txt": "x" * (4 * 1024 * 1024 + 1)}),
        ]
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as output:
            link = zipfile.ZipInfo("repo-commit/" + NAME + "/SKILL.md")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            output.writestr(link, "/outside")
        cases.append(data.getvalue())
        for payload in cases:
            with self.subTest(payload_size=len(payload)):
                self.download.side_effect = lambda *args, **kwargs: io.BytesIO(payload)
                self.install("--yes", expected=1)
                self.assertEqual(before, self.snapshot())

    def test_destination_symlinks_are_refused(self):
        target = self.project / (SKILL + "references")
        outside = self.project / "outside"
        outside.mkdir()
        target.parent.mkdir(parents=True)
        target.symlink_to(outside, target_is_directory=True)
        self.assertIn("symlinked", self.install("--yes", expected=1))
        self.assertEqual(list(outside.iterdir()), [])

    def test_restore_reverses_install_and_recovery_can_reapply_it(self):
        self.install("--yes")
        identifier = next(key for key, value in self.history().items() if value["action"] == "skills-install")
        self.call("restore", "--backup", identifier, "--yes")
        self.assertFalse((self.project / (SKILL + "SKILL.md")).exists())
        recovery = next(key for key, value in self.history().items() if value["action"] == "restore")
        self.call("restore", "--backup", recovery, "--yes")
        self.assertTrue((self.project / (SKILL + "SKILL.md")).is_file())

    def test_uninstall_removes_unchanged_skill_and_keeps_local_edits(self):
        self.install("--yes")
        edited = self.project / (SKILL + "references/check.md")
        edited.write_text("My local reference\n")
        self.call("uninstall", "--yes")
        self.assertFalse((self.project / (SKILL + "SKILL.md")).exists())
        self.assertEqual(edited.read_text(), "My local reference\n")
        self.assertTrue(self.history())

    def test_update_removes_obsolete_files_and_can_restore_previous_version(self):
        self.install("--yes")
        old = (self.project / (SKILL + "SKILL.md")).read_bytes()
        self.entry["github_url"] = self.entry["github_url"].replace(COMMIT, "b" * 40)
        updated = archive({"SKILL.md": "---\nname: " + NAME + "\ndescription: Updated\n---\n# New\n"})
        self.download.side_effect = lambda *args, **kwargs: io.BytesIO(updated)
        before_ids = set(self.history())
        self.install("--yes")
        self.assertFalse((self.project / (SKILL + "references/check.md")).exists())
        update_id, = set(self.history()) - before_ids
        self.call("restore", "--backup", update_id, "--yes")
        self.assertEqual((self.project / (SKILL + "SKILL.md")).read_bytes(), old)
        self.assertTrue((self.project / (SKILL + "references/check.md")).is_file())

    def test_status_reports_missing_installed_skill_files(self):
        self.install("--yes")
        (self.project / (SKILL + "SKILL.md")).unlink()
        self.assertIn("missing installed skill file", self.call("status", expected=1))


if __name__ == "__main__":
    unittest.main()
