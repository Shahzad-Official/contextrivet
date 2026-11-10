# Contributing to Contextrivet

You are most welcome to contribute if you think Contextrivet can be improved,
updated, or made easier to use. Bug reports, documentation fixes, skill catalog
suggestions, and practical feedback are welcome alongside code contributions.

The bundled instructions and stack presets reflect my personal engineering
preferences. Different architectures and working methods can be valid. Explain
the use case and tradeoffs behind your proposal; you do not have to share every
preference to contribute.

## Report a problem or suggest an improvement

Open an [issue](https://github.com/Shahzad-Official/contextrivet/issues) with the
command you ran, expected and actual behavior, and relevant operating system,
shell, Python version, and stack. Include a small reproduction where possible.
Remove secrets and private project content from examples and logs.

For a broad change to the supported stacks, defaults, or installation behavior,
an issue first helps us discuss the intended direction before implementation.
Focused fixes and documentation improvements can go straight to a pull request.

## Submit a pull request

1. Fork the repository and create a branch for one focused improvement.
2. Read the relevant code, tests, and project instructions. Reuse established
   patterns and dependencies.
3. Make the smallest complete change. Update README, command help, and shell
   completion when the interface changes. Update examples when behavior changes.
4. Run checks relevant to the change and explain the results. For non-trivial
   behavior changes, include a focused regression; simple copy or spacing edits
   do not need artificial tests. Say what you could not verify.
5. Open a [pull request](https://github.com/Shahzad-Official/contextrivet/pulls)
   explaining the problem, resulting behavior, and verification. Use Conventional
   Commit subjects such as `fix(project): preserve edited skill files`.

Preserve existing user documents, explicit consent, path validation, backups,
and recovery behavior. Test configuration changes in disposable directories.
Follow project instructions about app/server launches; the focused checks below
require no app or device session.

## Focused checks

Run the relevant checks from the repository root:

```bash
bash -n contextrivet scripts/*.sh scripts/lib/*.sh scripts/tools/*.sh
bash tests/test_cli.sh
python3 tests/test_help.py
python3 tests/test_completion.py
python3 tests/test_project.py
python3 tests/test_maintenance.py
python3 tests/test_skill_install.py
python3 tests/test_rename.py
```

The README's [development section](README.md#development-and-tests) lists the
broader test suites. Optional tool/service tests use fixtures; report separately
any real platform or integration behavior you verified. Passing fixture tests
alone does not prove a live service or agent integration works.

`test_verify.sh` clears inherited `XDG_DATA_HOME` and `VSCODE_AGENT_FOLDER` so
editor extension discovery is limited to its fixtures. On failure it reports the
command/line, dumps fixture JSON, and retains the temporary directory for review.
Its optional CLI version probes have a bounded wait: a reported `timeout` is
explicitly logged, rather than mistaken for unhealthy instruction configuration.
Exact version extraction is tested separately with the completed-child branch;
a deliberately slow fake CLI also checks timeout reporting. This does not prove
that real optional probes never time out under load.

The historical upgrade fixture and its provenance are described in
[tests/fixtures/README.md](tests/fixtures/README.md). The maintenance suite covers
preserving an already customized project and deliberately migrating unowned
automation, rather than testing upgrades only from freshly generated files.

## Contribute skills and presets

- Keep skills focused on a distinct task and make their selection criteria clear.
- Separate personal conventions from framework requirements and confirmed bugs.
- Preserve an existing project's sound architecture instead of imposing a migration.
- For `skills/stacks.json`, include a unique name, a concise description, and an
  HTTPS GitHub skill-directory URL pinned to a reviewed full commit hash.
- Check that the source includes `SKILL.md`, its relevant references, and a license.
  Do not silently replace a project's customized skill with upstream content.
- Flutter skill content is maintained in
  [flutter-skills](https://github.com/Shahzad-Official/flutter-skills). Propose
  content changes there; update the reviewed catalog pin here when appropriate.
  NestJS and Next.js catalog contributions are welcome too.

## License and attribution

Contextrivet's own code and documentation are under the [MIT License](LICENSE).
Keep existing copyright, license, and provenance notices when contributing or
redistributing work. Bundled adaptations and downloaded skills/tools retain their
upstream notices and applicable licenses; do not assume the root license changes
those terms.
