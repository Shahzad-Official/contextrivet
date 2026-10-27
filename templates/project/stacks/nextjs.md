# Next.js guidance

- Identify the installed Next.js version, router, and rendering/runtime choices
  from existing configuration; preserve the router's required file conventions.
- Organize feature behavior around those conventions, with shared UI and
  infrastructure only where needed. Do not move required route files merely to
  enforce a generic folder layout.
- Document server/client boundaries, data access, authentication/authorization,
  rendering, cache/revalidation ownership, and deployment constraints.
- Keep privileged data and secrets on the server. Validate input and authorization
  at server boundaries; preserve existing loading/error/accessibility behavior.
- Record the project's actual static/test commands without starting a dev server.
