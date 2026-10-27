# Flutter guidance

- For new codebases, group screens/widgets, feature state, business behavior, and
  data integration by feature. Separate domain rules from Flutter/plugin I/O when
  that boundary has a concrete purpose; avoid empty mandatory layers.
- Reuse the project's state management, navigation, dependency injection, and
  design system. Do not select replacement packages during scaffolding.
- Document app startup, navigation, state ownership, persistence/network flow,
  and platform integrations. Preserve lifecycle handling and accessibility.
- Record focused analysis/test commands and physical-device checks. Do not run
  the app, emulator, or device debug sessions unless the user asks.
