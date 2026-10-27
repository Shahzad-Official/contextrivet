#!/usr/bin/env python3
"""Check terminal help presentation without executing configuration commands."""
import errno
import os
from pathlib import Path
import pty
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent.parent
CLI = str(ROOT / "contextrivet")
ANSI = re.compile(r"\x1b\[[0-9;]*m")


class HelpTests(unittest.TestCase):
    def environment(self, **overrides):
        env = dict(os.environ)
        for name in ("NO_COLOR", "FORCE_COLOR"):
            env.pop(name, None)
        env.update(TERM="xterm-256color", COLUMNS="80")
        env.update(overrides)
        return env

    def capture(self, arguments, **overrides):
        result = subprocess.run([CLI, *arguments], env=self.environment(**overrides),
                                input="", text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def terminal(self, arguments, **overrides):
        master, slave = pty.openpty()
        process = subprocess.Popen([CLI, *arguments], env=self.environment(**overrides),
                                   stdin=subprocess.DEVNULL, stdout=slave, stderr=subprocess.PIPE)
        os.close(slave)
        chunks = []
        try:
            while True:
                try:
                    chunk = os.read(master, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                chunks.append(chunk)
        finally:
            os.close(master)
        _, error = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 0, error.decode())
        return b"".join(chunks).decode().replace("\r\n", "\n")

    def test_grouped_help_exposes_workflows_and_current_stacks(self):
        text = self.capture(["--help"])
        for command in ("project init", "project status", "project skills", "project backups",
                        "project restore", "project uninstall", "graphify", "cbm run", "cli install|uninstall"):
            self.assertIn(command, text)
        for stack in ("NestJS", "Next.js", "Flutter"):
            self.assertIn(stack, text)
        self.assertIn("--dry-run", text)
        panel = [line for line in text.splitlines() if line.startswith(("  ╭", "  │", "  ╰"))]
        self.assertEqual(len(panel), 4)
        self.assertEqual(len({len(line) for line in panel}), 1)

    def test_pipes_stay_plain_and_forced_color_preserves_text(self):
        for arguments in (["--help"], ["project", "--help"], ["project", "init", "--help"]):
            with self.subTest(arguments=arguments):
                plain = self.capture(arguments)
                self.assertNotIn("\x1b", plain)
                colored = self.capture(arguments, FORCE_COLOR="1")
                self.assertIn("\x1b[", colored)
                self.assertEqual(ANSI.sub("", colored), plain)

    def test_explicit_plain_preferences_override_forced_color(self):
        for arguments in (["--help"], ["project", "--help"], ["project", "restore", "--help"]):
            for overrides in ({"NO_COLOR": "1", "FORCE_COLOR": "1"},
                              {"NO_COLOR": "", "FORCE_COLOR": "1"}, {"FORCE_COLOR": "0"}):
                with self.subTest(arguments=arguments, overrides=overrides):
                    self.assertNotIn("\x1b", self.capture(arguments, **overrides))

    def test_real_terminal_enables_color_and_respects_plain_terminals(self):
        for arguments in (["--help"], ["project", "--help"]):
            self.assertIn("\x1b[", self.terminal(arguments))
            self.assertNotIn("\x1b", self.terminal(arguments, NO_COLOR="1"))
            self.assertNotIn("\x1b", self.terminal(arguments, TERM="dumb"))

    def test_narrow_help_stacks_rows_and_keeps_all_commands(self):
        text = self.capture(["--help"], COLUMNS="60")
        self.assertNotIn("╭", text)
        self.assertIn("    project status\n      Check project readiness", text)
        self.assertIn("project restore --backup <id>", text)
        self.assertIn("project skills --stack <stack>", text)
        self.assertEqual(self.capture(["--help"], COLUMNS="invalid"), self.capture(["--help"]))


if __name__ == "__main__":
    unittest.main()
