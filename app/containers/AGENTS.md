# Container typing

Type every `Container(...)` and `DependenciesContainer()` edge as its concrete child container, with a local `# type: ignore[assignment]`; never use provider generics such as `Container[ChildContainer]`.

This exposes child providers directly to mypy and IDEs while confining dependency-injector's stub mismatch to the wiring line.
