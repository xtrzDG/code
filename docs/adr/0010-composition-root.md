# 0010. One composition root: a provider graph today, typed roots from now on

- Status: Accepted
- Date: 2026-10-22

## Context

The API and the worker are wired in one place, `app/containers/`
(dependency-injector, from the copier template): one declarative container
per role and bounded context, composed by
`app/containers/app.py::AppContainer`, and the only module allowed to import
concrete classes across roles (ADR 0002). The graph has grown with the
product, to over 270 files and about 26,000 lines in wave 20.

dependency-injector types a child container's edge as the provider it is,
not the container it stands for, so every edge carries a local
`# type: ignore[assignment]` (`app/containers/AGENTS.md`): 1,103 of them
before this decision, almost all of the backend's silenced type errors. A
provider's keyword arguments are not checked at all, so a misspelt or
missing dependency surfaces only when the provider resolves; the only guard
is `tests/e2e/test_application_boot.py::test_every_provider_of_the_container_resolves`.
Newcomers find the wiring the hardest part of the backend to follow.

## Decision

- **One composition root stays.** Gateways (HTTP routers, the worker, CLIs)
  receive what they need from `AppContainer`; no other role imports
  `app.containers` (`.importlinter`). Tests keep overriding providers at the
  edges (settings, clock, model, external clients).
- **The ignores only go down.** `tests/architecture_policy/test_container_ignores_ratchet.py`
  stores their number (1,090 after the pilot) and fails when it changes
  without the stored number following it down; only the documented edge
  kind is allowed.
- **New wiring is typed roots in plain Python.** A context's wiring is a
  frozen `<Context>Dependencies` dataclass of contracts, typed factory
  classes for its use cases and operators (the role chain from
  `app/containers/role_chain_factories.py`), and a `<Context>Root` whose role
  children are `functools.cached_property` singletons. mypy and pyright check
  every constructor argument; a typed root imports nothing from
  `dependency_injector` and has no ignore (the ratchet test checks both).
- **One seam.** The provider graph holds one root `Singleton` per migrated
  context, filled by a single seam function that maps the graph's providers
  to the dependencies' fields, and exposes only what other contexts and the
  gateways call, through `Dependency(instance_of=<Context>Root)` views. The
  resolution test keeps covering the seam.
- **The pilot is the feedback context** (`app/containers/feedback/`): its
  use cases, the role chain of its six endpoints and job, and the use case the
  conversation turn calls. The pass-through orchestrator and pipeline
  containers of the context are gone; 13 ignores went with them.

## Consequences

- Wiring mistakes in a migrated context are type errors, found by the editor
  and CI instead of at start-up, and the context reads as ordinary Python.
- Two styles coexist while contexts migrate one at a time, each migration
  lowering the ratchet; the seam remains the one untyped mapping of a
  migrated context. If the typed roots stop reading better than the
  provider graph, the fallback is generating the container modules from a
  declarative table, so the ignores live only in generated files.
- A typed root resolves its dependencies once (the root is a singleton), so
  a migrated context must not depend on a provider whose instance is meant
  to change per call; such a dependency stays a factory method on the root.
