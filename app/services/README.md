# No `services` Package

This directory exists only to document a forbidden architectural category.

Do not add Python files here and do not turn this directory into a package.
`service` is too broad for this architecture. It does not name a stable
responsibility or boundary, so AI agents tend to use it as a dumping ground for
business rules, orchestration, adapters, utilities, and side effects.

Choose the concrete role instead:

- `use_cases/` for one business action or invariant.
- `orchestrators/` for coordinating multiple use cases.
- `pipelines/` for ordering orchestrators into an execution phase.
- `operators/` for endpoint-level execution strategy.
- `repositories/` for persistence.
- `registries/` for runtime lookup catalogs.
- `facilitators/` for narrow boundary-adjacent side effects.
- `utilities/` for deterministic technical operations.
- `adapters/` and `clients/` for external systems.
- `gateways/` for transport-facing responses.
- `transformers/` for shape conversion.
