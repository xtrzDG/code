# Container typing

Type every `Container(...)` and `DependenciesContainer()` edge as its concrete child container, with a local `# type: ignore[assignment]`; never use provider generics such as `Container[ChildContainer]`.

This exposes child providers directly to mypy and IDEs while confining dependency-injector's stub mismatch to the wiring line.

# Composed containers

A role container too big for one file is split into child containers by bounded context (`app/containers/<role>/<context>_<role>.py`) and composed by `<role>_container.py` with `Container(...)` edges. A child gets as edges only the containers it uses: the lower roles, the contexts of the role below it (flat edges such as `booking_use_cases`) and the sibling contexts it needs. A container that reaches into a composed container's children (`use_cases.bookings.create_booking_use_case`) declares that edge with `composed_container_edge(ComposedContainer)` from `app/containers/container_edges.py`; a plain `DependenciesContainer()` cannot resolve nested children in a class body.

# Typed roots

A context may instead be wired as plain typed Python (ADR 0010; the pilot is `app/containers/feedback/`, followed by `app/containers/passkeys/` and, for a set of adapters, `app/containers/adapters/provider_resilience.py`): a frozen `<Context>Dependencies` dataclass of contracts, `<Context>UseCaseFactories` and `<Context>OperatorFactories` with one typed factory method per use case and operator (`app/containers/role_chain_factories.py` builds the role chain), and a `<Context>Root` whose role children are `functools.cached_property`. The provider graph holds one root `Singleton` filled by a single seam function and exposes only what other contexts and the gateways call, through `Dependency(instance_of=<Context>Root)` views. A typed root imports nothing from `dependency_injector` and has no `# type: ignore`; `tests/architecture_policy/test_container_ignores_ratchet.py` checks both and keeps the number of ignores in `app/containers` from growing.
