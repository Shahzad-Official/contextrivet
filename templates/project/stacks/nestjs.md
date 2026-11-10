# NestJS guidance

Preserve existing architecture first; the conventions below guide compatible new
work and do not authorize restructuring or establish past architectural intent.

- Group feature behavior into Nest modules. Keep controllers focused on transport
  mapping and boundary validation; put application behavior in cohesive providers.
- Declare imports, providers, and exports deliberately. Export only the contracts
  another module needs, and reuse Nest dependency injection instead of constructing
  infrastructure clients throughout business code.
- Keep domain policies independent of HTTP and concrete persistence integrations
  where a real boundary is useful. Apply SOLID without adding empty service or
  repository layers for every entity.
- Document request flow, module ownership, DTO validation, guards/authorization,
  transaction ownership, error mapping, and external integration contracts.
- Preserve existing database, migration, configuration, and test conventions.
  Do not select an ORM, install dependencies, or start the server during setup.

Official references: [modules](https://docs.nestjs.com/modules) and
[providers](https://docs.nestjs.com/providers).
