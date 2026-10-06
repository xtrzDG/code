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
- An endpoint's operator comes from `pipeline_operator(...)` (runs in the
  storage scope of the business its input names; business routes must use
  it, `tests/architecture_policy/test_business_routes_are_scoped.py`) or,
  for platform-level work only (webhooks before their business is known,
  admin lists across businesses, jobs over every business),
  `platform_pipeline_operator(...)`, which runs platform-wide. The storage
  scope is fail-closed: code in no scope cannot touch tenant collections.
- Cabinet endpoints check access with `AuthorizeBusinessAccessUseCase`
  (`app/use_cases/authorize_business_access_use_case.py`) before acting: owners
  and staff pass, `required_role=OWNER` limits billing/settings/publishing to
  owners, platform admins pass with an audit entry. A foreign business is
  reported as `NotFoundError`.
- Tenant-owned documents are read only together with their `business_id`
  (`BusinessScopedRepository`). Repositories never read a whole collection
  to find documents: they query declared, indexed lookup fields
  (`find_one_by_field`, `list_by_fields`, `count_by_fields`,
  `list_by_range`; see `migrations/README.md`), and no repository reads a
  whole collection
  (`tests/architecture_policy/test_no_full_scans_in_hot_paths.py`, whose
  allow-list is empty). Periodic jobs ask by indexed predicates; a job or
  admin view that must see every business walks them with
  `walk_businesses` (`app/use_cases/shared/business_walk.py`: keyset
  batches of 200 in first-write order) and keeps only what it needs per
  business. The business of a channel message comes from the server-side
  channel lookup, never from model output.
- Use cases depend on contracts from `app/contracts/` (repositories, registries,
  utilities, facilitators, LLM adapter), never on concrete classes of another
  module. Constructor injection only; no globals, no service locators.
- `app/services/` is forbidden.
- Use-case packages (`app/use_cases/<package>/`) are independent of each
  other (an import-linter `independence` contract, direct and indirect
  imports). What several packages need — loading the business
  (`require_business`), contact updates with audit, subscription records,
  staff alert texts, list-item views — lives in `app/use_cases/shared/`,
  which imports no use-case package; a new package joins the contract
  (`tests/architecture_policy/test_import_layers.py`).

## Files and names

- One public class per file. File `create_booking_use_case.py` holds
  `CreateBookingUseCase`; same for `*_orchestrator.py`, `*_pipeline.py`,
  `*_operator.py`, `*_registry.py`, `*_facilitator.py`, `*_adapter.py`,
  `*_client.py`, `*_transformer.py`. Utilities may group small pure functions.
- Group a module's files in a sub-package when it has more than a few files,
  e.g. `app/use_cases/bookings/`.
- A hand-written source file has at most 300 lines (aim for 150–300): every
  `.py` file under `app/`, `scripts/` and `tests/`, and the widget's parts
  under `app/gateways/http/static/`. Split a bigger file along its
  responsibilities (a use case with its helpers in a sub-package, data
  tables in data modules, a test file's shared fixtures and fakes in their
  own modules next to it), not at an arbitrary line;
  `tests/architecture_policy/test_source_file_size.py` checks it, and the
  cabinet's files under `web/src/` and `web/e2e/` too (generated files and
  the translation dictionaries exempt); ESLint `max-lines` checks the
  cabinet as well. CI fails on a longer file.
- Module-specific DTOs go to a new file `app/schemas/dto/<module>.py`; do not
  edit DTO files owned by the foundation unless a field is truly missing.
- New primitives go to `app/schemas/typings/<bounded_context>/<allowed_name>.py`
  in abc order. Reuse existing primitives first.

## Stored documents and deploys

Two releases run side by side during every deploy and after a rollback, so
a stored shape changes only by expand and contract
(`docs/operations/deploys.md`):

- Add fields as optional; make them required only in a later release,
  after an upcaster or `workshop migrate-documents` filled old rows.
  Never rename, remove or retype a field, and never write a new enum
  value, in the release that introduces the change.
- Every shape change bumps the document's `schema_version` (on the model)
  and adds a golden fixture: run
  `uv run python -m tests.storage.document_evolution.refresh`. Old rows
  that need a change get an upcaster in
  `app/adapters/storage/document_upgrades.py`;
  `tests/architecture_policy/test_document_evolution.py` checks both.
- Documents stay strict (`extra="forbid"`) everywhere; only the storage
  read path (`PersistedDocumentCodec`) ignores unknown fields. Never relax
  inputs or DTOs to make old data load.
- SQL migrations are additive; drop or rename only what no running
  release uses. They run while the previous release serves, so they are
  online-safe (`migrations/README.md`, linted by
  `tests/storage/test_migration_safety.py`): no rewrite, plain index build
  or unbatched `UPDATE`/`DELETE` on an existing table. A lookup field on an
  existing table is a nullable column filled by a BEFORE INSERT/UPDATE
  trigger, backfilled by
  `workshop backfill-lookup --collection X --field Y --batch 5000` in
  keyset batches outside the deploy, then indexed CONCURRENTLY in a later
  file.

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
  `install_error_handlers` maps them to status codes, and every error body is
  an `ErrorBody` (the framework's refusals too). Never raise `HTTPException`
  for business errors. Each router declares
  `APIRouter(..., responses=standard_error_responses())`, so the description
  documents its errors; DELETE routes answer `204 No Content`
  (`tests/platform/test_api_contract.py`).
- A new business route joins the authorization matrix by itself
  (`tests/platform/test_authorization_matrix.py`); an owner-only one goes to
  `OWNER_ONLY_OPERATIONS`, and a body with required fields to
  `REQUEST_BODIES` (`tests/platform/authorization_*.py`).
- Paged lists take `?limit=N&cursor=…` (`parse_page_request` in
  `app/gateways/http/paging_query.py` → `PageRequest`) and answer
  `{"items": [...], "next_cursor": … | null}` with a concrete page DTO per list
  (e.g. `BookingPage`). Lists of growing collections page in the database:
  the repository reads one keyset page (`page_by` of the document store,
  `app/utilities/paging/keyset_paging.py` turns the cursor into a position
  and the page into `next_cursor`), and counts, sums and dashboards group
  there (`count_by`); a page's related documents come in one read
  (`get_many`, `latest_by`), never one query per row. Filters are part of
  the query; there is no in-memory paging helper, and
  `tests/architecture_policy/test_lists_page_in_the_database.py` keeps the
  cabinet's lists, cards and dashboards on the database. A list whose
  order the database cannot compute per request (the platform admin's
  client list, ordered by figures summarized from several collections) is
  computed ahead by a periodic job into a read model with a stored rank
  per order (`client_standings`, `refresh_client_standings`) and pages by
  that rank. Their latency budgets live in `tests/perf`
  (`docs/operations/capacity.md`).
- JSON request bodies have one parsing stack,
  `app/gateways/http/strict_request_parsing.py`: read them with
  `build_json_body_dependency(Body)` (or `optional=True` when an empty body
  means all defaults) and describe them for OpenAPI with
  `openapi_extra=describe_json_body(Body)` (same `optional`), so the
  cabinet's generated client knows them. Signed webhooks and bodies whose
  type depends on the path read `read_raw_request_body` and validate with
  `parse_json_body`. Path ids go through `parse_path_identifier`, optional
  query values through `parse_optional` (`query_parsing.py`), `?language=`
  and Accept-Language through `language_negotiation.py`.
- Every operation has a tag (its router's) and the operationId
  `<tag>_<route function name>` (`app/gateways/http/operation_ids.py`): a
  route function's name is a public SDK method name, so renaming it is a
  breaking change (docs/api-versioning.md).
- A route that creates something a retry must not create twice (a booking,
  a staff message, a checkout, an assistant) takes the Idempotency-Key with
  one line, `dependencies=[Depends(idempotent)]`, from the dependency its
  router builder receives (`app/gateways/http/idempotency/`); the response
  recorder installed by `build_http_application` keeps its answer.
- Router tests build a small `FastAPI()` with `install_error_handlers` and the
  module router, and call it with `fastapi.testclient.TestClient`.

## Internationalization

- Phone numbers: parse with `PhoneNumberParserContract`, store E.164 only.
- Texts shown to owners or customers: `LocalizedText` resolved with
  `LocalizedTextResolverContract` (requested tag -> base language -> English).
  English is mandatory and the only fallback.
- Owner-facing backend texts (plans, niche templates, staff notifications,
  call forwarding guides, billing texts) live in the owner text catalog,
  `app/registries/localization/texts/<language>.json`, one file per cabinet
  language (`CABINET_LANGUAGES`: ka, ru, en, he, de). Code reads them by key
  (`owner_text("plans.chat.name")`, `app/utilities/localization/owner_texts.py`)
  and never writes them as literals (architecture policy test). A new text is
  added to `en.json` and to every other file; a text not checked by a native
  speaker goes into the file's `draft_keys` (`uv run python -m
  scripts.translate_catalogs backend draft --language <tag>` drafts missing
  texts that way). Wording of issued invoices and receipts uses
  `reviewed_owner_text`, so drafts never reach a kept document. The
  assistant's prompts read only English values.
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
  uv run mypy . && uv run pyright && uv run pytest` (or `just check`, which
  also runs the cabinet checks). pytest includes the architecture policies:
  the role layers of `.importlinter` (`lint-imports`), dead code
  (`vulture`, whitelist in `vulture_whitelist.py`) and the 300-line limit.
  CI also enforces at least 95 % line-and-branch coverage of `app/`
  (`uv run pytest -n auto --cov=app --cov-branch --cov-fail-under=95`).
