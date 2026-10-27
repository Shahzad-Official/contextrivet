# Shared engineering principles

- Prefer the smallest complete, maintainable solution. Inspect relevant code,
  callers, tests, contracts, and error paths before changing them.
- Apply SOLID where it clarifies responsibilities and real dependency boundaries:
  give modules cohesive responsibilities, keep contracts substitutable, expose
  focused interfaces, and keep business rules independent of concrete I/O.
  Do not add interfaces, layers, or factories without a demonstrated need.
- For new projects, prefer feature-first organization: keep a feature's behavior,
  state, UI or endpoints, data access, and tests close together where the framework
  permits. Document shared infrastructure and allowed cross-feature dependencies.
- Preserve a working project's established architecture. Document it first;
  propose restructuring only when requested or necessary for the authorized task.
  Feature-first organization does not require identical folders across stacks.
- Reuse installed dependencies and existing components. Keep shared code focused
  on actual reuse; avoid catch-all utilities and speculative framework building.
- Preserve validation, authentication, authorization, accessibility, data integrity,
  error handling, and compatibility. Keep credentials out of source and notes.
- Do not launch apps, servers, emulators, or physical-device debug sessions unless
  explicitly requested. Use permitted focused checks and explain manual testing.
- Follow Conventional Commits when asked to commit. Base proposed messages on
  staged changes; never stage or commit unrelated user work.
