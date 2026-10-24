# 0002. Role chain from the copier template, enforced as import layers

- Status: Accepted
- Date: 2026-10-02

## Context

The backend was generated from `copier-template-python-backend`, whose
roles (gateways, operators, pipelines, orchestrators, use cases,
repositories, registries, facilitators, utilities, transformers, adapters,
clients) keep business logic independent of HTTP, storage and providers. A
role chain only helps while the direction of dependencies holds, and review
alone does not keep it across hundreds of files and several people.

## Decision

- Every HTTP endpoint runs `operator.operate -> pipeline.start ->
  orchestrator.execute -> use_case.run` (`docs/conventions.md`). Use cases
  depend on contracts (`app/contracts/`), never on concrete classes of
  another role; `app/containers/` is the only composition root.
- `.importlinter` enforces the layers, checked by `lint-imports` in every
  test run (`tests/architecture_policy/test_import_layers.py`):

  ```text
  gateways > operators > pipelines > orchestrators > use_cases
    > repositories | registries | facilitators | transformers   (independent)
    > adapters > clients > utilities > contracts > schemas
  ```

  Utilities sit low because they are deterministic helpers that every role
  uses (formatting, parsing, paging) and import nothing above contracts.
  A second contract keeps the composition root (`app.containers`,
  `app.main`, `app.worker_main`) out of reach of every role below gateways.
- Command-line entry points are gateways too (`app/gateways/cli/`): the
  migration runner moved there from the storage adapters because it starts
  a use case.
- Broken contracts are fixed by moving code to the role it belongs to;
  `ignore_imports` is not used (a test checks it).

## Consequences

- Business rules are tested with fakes of contracts, without HTTP or a
  database, and a provider can be swapped by writing one adapter.
- Small features touch several files (route, operator chain, use case,
  container wiring). Generic chain classes (`PipelineOperator`,
  `OrchestratorPipeline`, `UseCaseOrchestrator`) keep single-use-case
  endpoints cheap.
- `app/services/` stays forbidden (`tests/architecture_policy/test_no_services.py`).
