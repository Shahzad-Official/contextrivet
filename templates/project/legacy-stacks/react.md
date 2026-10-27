# React guidance

- Group new UI, feature hooks/state, behavior, API integration, and tests by feature
  while following the project's router and build conventions.
- Keep shared UI primitives separate from feature behavior; give state a clear
  owner and derive values rather than duplicating state unnecessarily.
- Document rendering/runtime, routing, state and server-data ownership, and API
  contracts. Keep secrets and privileged operations outside browser code.
- Preserve existing component patterns, accessibility, loading/error behavior,
  and test tools; do not introduce a state library or data layer during setup.
