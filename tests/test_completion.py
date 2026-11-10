#!/usr/bin/env python3
"""Exercise generated completions in actual Bash and zsh, without project actions."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
CLI = str(ROOT / "contextrivet")


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), TERM="dumb")
        self.scripts = {}
        self.shells = [shell for shell in ("bash", "zsh") if shutil.which(shell)]
        for shell in self.shells:
            result = subprocess.run([CLI, "completion", shell], env=self.env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            path = self.base / (shell + ".sh")
            path.write_text(result.stdout)
            self.scripts[shell] = path
        self.assertEqual(list(self.home.iterdir()), [])

    def candidates(self, shell, *words, cwd=None):
        if shell == "bash":
            source = '''source "$1"
shift
COMP_WORDS=("$@")
COMP_CWORD=$((${#COMP_WORDS[@]} - 1))
_contextrivet
printf '%s\\n' "${COMPREPLY[@]}"
'''
        else:
            # Capture compadd's arguments without requiring an interactive ZLE widget.
            source = '''compdef() { :; }
source "$1"
shift
compadd() { [[ "$1" != -- ]] || shift; print -rl -- "$@"; }
_files() { print -r -- "native-file-completion:$*"; }
compset() { :; }
words=("$@")
CURRENT=${#words}
_contextrivet
'''
        result = subprocess.run([shell, "-c", source, shell, str(self.scripts[shell]), "contextrivet", *words],
                                cwd=cwd or self.base, env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return [line for line in result.stdout.splitlines() if line]

    def test_generation_and_validation_are_read_only(self):
        for arguments in (("--help",), (), ("fish",), ("zsh", "extra")):
            result = subprocess.run([CLI, "completion", *arguments], env=self.env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0 if not arguments or arguments == ("--help",) else 2)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_command_and_nested_subcommand_context(self):
        cases = [
            (("pro",), {"project"}),
            (("project", ""), {"init", "status", "skills", "backups", "restore", "uninstall", "repair", "baseline", "automate", "--help", "-h"}),
            (("project", "skills", ""), {"install", "--stack", "--help", "-h"}),
            (("project", "skills", "install", "--"), {"--project", "--stack", "--names", "--all", "--dry-run", "--yes", "--help"}),
            (("health", ""), {"--project", "--json", "--project-only", "--global-only", "--help", "-h"}),
            (("project", "repair", ""), {"--project", "--apply", "--dry-run", "--help", "-h"}),
            (("project", "baseline", ""), {"--project", "--note", "--yes", "--dry-run", "--help", "-h"}),
            (("project", "automate", ""), {"--project", "--hook", "--ci", "--local", "--apply", "--dry-run", "--help", "-h"}),
            (("tools", ""), {"graphify", "codebase-memory-mcp", "--help", "-h"}),
            (("completion", ""), {"bash", "zsh", "--help", "-h"}),
            (("tools", "codebase-memory-mcp", "mcp", ""), {"status", "enable", "disable", "--help", "-h"}),
            (("tools", "codebase-memory-mcp", "mcp", "enable", ""), {"codex", "opencode", "antigravity"}),
            (("tools", "codebase-memory-mcp", "mcp", "enable", "codex", "--d"), {"--dry-run"}),
            (("tools", "codebase-memory-mcp", "watcher", "set", ""), {"enabled", "disabled"}),
        ]
        for shell in self.shells:
            for words, expected in cases:
                with self.subTest(shell=shell, words=words):
                    self.assertEqual(set(self.candidates(shell, *words)), expected)

    def test_flags_and_enum_values_follow_the_selected_command(self):
        for shell in self.shells:
            self.assertEqual(set(self.candidates(shell, "project", "init", "--stack", "")), {"none", "nestjs", "nextjs", "flutter", "auto"})
            self.assertEqual(self.candidates(shell, "project", "init", "--stack", "nes"), ["nestjs"])
            self.assertEqual(set(self.candidates(shell, "project", "init", "--skills", "")), {"none", "ponytail"})
            self.assertEqual(self.candidates(shell, "project", "restore", "--b"), ["--backup"])
            self.assertNotIn("--force", self.candidates(shell, "project", "init", "--"))
            self.assertIn("--force", self.candidates(shell, "project", "uninstall", "--"))
            self.assertIn("run", self.candidates(shell, "cbm", ""))
            self.assertEqual(self.candidates(shell, "cbm", "run", "--agent", "co"), ["codex"])
            self.assertEqual(self.candidates(shell, "graphify", "serve", "--port", ""), [])
            self.assertEqual(self.candidates(shell, "completion", "zsh", ""), [])
            self.assertNotIn("--help", self.candidates(shell, "cli", "install", "--"))

    def test_equals_values_and_comma_separated_agents(self):
        for shell in self.shells:
            self.assertEqual(self.candidates(shell, "project", "init", "--stack=nes"), ["--stack=nestjs"])
            self.assertEqual(self.candidates(shell, "install", "--mode=m"), ["--mode=merge"])
            self.assertEqual(self.candidates(shell, "project", "init", "--agents", "codex,cl"), ["codex,claude", "codex,cline"])
            agents = self.candidates(shell, "project", "init", "--agents=codex,")
            self.assertIn("--agents=codex,claude", agents)
            self.assertNotIn("--agents=codex,codex", agents)
            self.assertNotIn("--agents=codex,none", agents)
        if "bash" in self.shells:
            self.assertEqual(self.candidates("bash", "project", "init", "--stack", "=", "nes"), ["nestjs"])
            self.assertEqual(self.candidates("bash", "install", "--mode", "=", "m"), ["merge"])

    def test_paths_with_spaces_use_native_file_completion(self):
        folder = self.base / "project with spaces"
        folder.mkdir()
        if "bash" in self.shells:
            self.assertEqual(self.candidates("bash", "project", "init", "--project", str(self.base / "project")), [str(folder) + "/"])
            self.assertEqual(self.candidates("bash", "project", "init", "--project=" + str(self.base / "project")), ["--project=" + str(folder) + "/"])
        if "zsh" in self.shells:
            self.assertIn("native-file-completion:-/", self.candidates("zsh", "project", "init", "--project", ""))

    def test_saved_backup_ids_respect_the_explicit_project_and_keep_files_unchanged(self):
        project = self.base / "another project"
        identifiers = ("20261027-155358-733474-48496", "20261028-120000-12345")
        for namespace, identifier in zip(("contextrivet", "dev-agent-config"), identifiers):
            (project / ".agents" / namespace / "backups" / identifier).mkdir(parents=True)
        (project / ".agents/contextrivet/backups/invalid").mkdir()
        before = sorted(str(path) for path in self.base.rglob("*"))
        for shell in self.shells:
            result = self.candidates(shell, "project", "restore", "--project", str(project), "--backup", "")
            self.assertEqual(set(result), set(identifiers))
            self.assertEqual(self.candidates(shell, "project", "restore", "--backup", ""), [])
        self.assertEqual(sorted(str(path) for path in self.base.rglob("*")), before)


if __name__ == "__main__":
    unittest.main()
