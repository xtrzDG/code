# Implementation conventions

Rules every module of this backend follows. They extend `AGENTS.md` (domain
primitives) and `docs/architecture.md` (roles and flows).

## Role chain

Every HTTP endpoint runs `operator.operate` -> `pipeline.start` ->
`orchestrator.execute` -> `use_case.run`.

- For an endpoint backed by exactly one use case, do not write pass-through
  classes. Compose the generic ones:
  `PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(use_case)))`
  (`app/operators/pipeline_operator.py`, `app/pipelines/orchestrator_pipeline.py`,
  `app/orchestrators/use_case_orchestrator.py`).
- Write a dedicated orchestrator when a flow coordinates several use cases, and a
  dedicated pipeline when a phase orders several orchestrators.
- Cabinet endpoints check access with `AuthorizeBusinessAccessUseCase`
  (`app/use_cases/authorize_business_access_use_case.py`) before acting: owners
  and staff pass, `required_role=OWNER` limits billing/settings/publishing to
  owners, platform admins pass with an audit entry. A foreign business is
  reported as `NotFoundError`.
- Tenant-owned documents are read only together with their `business_id`
  (`BusinessScopedRepository`). The business of a channel message comes from the
  server-side channel lookup, never from model output.
- Use cases depend on contracts from `app/contracts/` (repositories, registries,
  utilities, facilitators, LLM adapter), never on concrete classes of another
  module. Constructor injection only; no globals, no service locators.
- `app/services/` is forbidden.

## Files and names

- One public class per file. File `create_booking_use_case.py` holds
  `CreateBookingUseCase`; same for `*_orchestrator.py`, `*_pipeline.py`,
  `*_operator.py`, `*_registry.py`, `*_facilitator.py`, `*_adapter.py`,
  `*_client.py`, `*_transformer.py`. Utilities may group small pure functions.
- Group a module's files in a sub-package when it has more than a few files,
  e.g. `app/use_cases/bookings/`.
- Module-specific DTOs go to a new file `app/schemas/dto/<module>.py`; do not
  edit DTO files owned by the foundation unless a field is truly missing.
- New primitives go to `app/schemas/typings/<bounded_context>/<allowed_name>.py`
  in abc order. Reuse existing primitives first.

## Time

- "Now" comes from an injected `WallClock[Microseconds]` (`typed_time_provider`).
  Tests pass `WallClock(preferred_time_unit_type=Microseconds,
  unix_nanosecond_factory=lambda: <fixed ns>)`.
- Business-local dates and times are computed with `zoneinfo` in the business
  `timezone`; storage is UTC.

## HTTP

- Each module exposes `build_<module>_router(...) -> APIRouter` in
  `app/gateways/http/<module>_routes.py`. The builder receives ready operators
  (and, for cabinet endpoints, the result of `build_current_user_dependency`)
  as arguments.
- Request and response bodies are DTOs with typed primitives. Path and query
  parameters arrive as raw `str` and are converted to primitives inside the
  route function (the transport boundary).
- Errors are raised as `app/schemas/exceptions/application_errors.py` classes;
  `install_error_handlers` maps them to status codes. Never raise
  `HTTPException` for business errors.
- Router tests build a small `FastAPI()` with `install_error_handlers` and the
  module router, and call it with `fastapi.testclient.TestClient`.

## Internationalization

- Phone numbers: parse with `PhoneNumberParserContract`, store E.164 only.
- Texts shown to owners or customers: `LocalizedText` resolved with
  `LocalizedTextResolverContract` (requested tag -> base language -> English).
  English is mandatory; Russian is provided for every owner-facing text.
- Never hard-code a country, currency, language, or time zone in business logic;
  read them from the business document or the country profile.

## Tests and checks

- Personal-data operations (view of a conversation or contact, export, delete,
  admin access, retention purge) append an `AuditLogEntryDocument`.
- Tests live under `tests/<module>/`. No network: use `ScriptedLlmAdapter`
  (`app/adapters/llm/scripted_llm_adapter.py`), in-memory repositories
  (`app/repositories/*` over `InMemoryDocumentCollectionAdapter`), and fakes
  that implement contracts.
- Before committing: `uv run ruff check . && uv run ruff format --check . &&
  uv run mypy . && uv run pyright && uv run pytest`.
