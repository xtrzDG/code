"""
Dependency edges on containers that are composed of child containers.

A plain `DependenciesContainer()` learns the names of its providers only when
it is wired, so a class body can reach `edge.provider` but not
`edge.child.provider`. The composed edge declares one nested edge per child
container of the composed type, so `use_cases.bookings.create_booking_use_case`
can be wired in a class body like any other provider.
"""

from dependency_injector import containers
from dependency_injector.providers import Container, DependenciesContainer


def composed_container_edge(
    composed_type: type[containers.DeclarativeContainer],
) -> DependenciesContainer:
    """Edge on `composed_type` with a nested edge for each of its children."""

    return DependenciesContainer(
        **{
            child_name: DependenciesContainer()
            for child_name, provider in composed_type.providers.items()
            if isinstance(provider, Container)
        }
    )
