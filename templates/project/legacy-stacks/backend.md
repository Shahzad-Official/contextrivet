# Backend guidance

- Organize new application behavior by feature or domain within the framework's
  conventions. Keep transport handlers focused on mapping and boundary validation;
  keep business policies independent of HTTP and concrete persistence clients.
- Document request-to-use-case-to-storage flow, authorization boundaries,
  transaction ownership, error contracts, and external integration behavior.
- Use shared infrastructure only where needed. Preserve existing migration,
  dependency injection, and test conventions; do not create a repository/service
  layer for every entity by default.
