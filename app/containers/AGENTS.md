# Container typing

Type every `Container(...)` and `DependenciesContainer()` edge as its concrete child container, with a local `# type: ignore[assignment]`; never use provider generics such as `Container[ChildContainer]`.

This exposes child providers directly to mypy and IDEs while confining dependency-injector's stub mismatch to the wiring line.

# Composed containers

A role container too big for one file is split into child containers by bounded context (`app/containers/<role>/<context>_<role>.py`) and composed by `<role>_container.py` with `Container(...)` edges. A child gets as edges only the containers it uses: the lower roles, the contexts of the role below it (flat edges such as `booking_use_cases`) and the sibling contexts it needs. A container that reaches into a composed container's children (`use_cases.bookings.create_booking_use_case`) declares that edge with `composed_container_edge(ComposedContainer)` from `app/containers/container_edges.py`; a plain `DependenciesContainer()` cannot resolve nested children in a class body.
