# Pre-upgrade project fixture

`pre-upgrade-project.json` is synthetic project data generated with ContextRivet
initializer, templates, catalog, and bundled skills from commit
`af0a5238c053e6e4b4bc3594444a6bae5b3c5aa3`. It retains the actual original transaction
manifest and ownership digests, with a deterministic backup ID. The fixture does
not require Git history or network access when tests run.

After old-version initialization with the Flutter profile and Codex/Claude
routers, the fixture was customized to contain completed onboarding documents,
private team rules, a feature note and index entry, edited workflow/Ponytail
content, and unowned team hook/workflow/checker files. These are test observations
and requirements, not facts about any real application. No app code executes.

The loader restores exact text and file modes, then initializes a disposable Git
repository. Upgrade tests verify byte/mode preservation, saved profile retention,
read-only repetition, rejection of conflicting legacy automation, explicit
archive/regeneration, ownership, rollback, uninstall, and recovery. A separate
case verifies that identical unowned automation is not silently adopted.

Keep the historical installed hashes and originals intact when editing the
fixture. Generate a new snapshot with a pinned historical initializer when the
migration baseline changes; do not generate it using the current initializer and
label it as historical.
