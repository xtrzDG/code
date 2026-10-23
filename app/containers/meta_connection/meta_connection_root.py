from functools import cached_property

from app.containers.meta_connection.meta_connection_dependencies import (
    MetaConnectionDependencies,
)
from app.containers.meta_connection.meta_connection_operator_factories import (
    MetaConnectionOperatorFactories,
)
from app.containers.meta_connection.meta_connection_use_case_factories import (
    MetaConnectionUseCaseFactories,
)


class MetaConnectionRoot:
    """
    The typed composition root of Meta's self-serve connection (ADR 0010,
    like app/containers/passkeys/): plain Python that builds its use cases
    and their operators from MetaConnectionDependencies, checked by mypy and
    pyright without a single `# type: ignore`. The dependency graph holds
    one root (BusinessUseCasesContainer.meta_connection_root) and exposes
    the comments webhook's intake (ChannelPipelinesContainer) and the
    operators the routers and the worker call (ChannelOperatorsContainer).
    """

    def __init__(self, dependencies: MetaConnectionDependencies) -> None:
        self._dependencies: MetaConnectionDependencies = dependencies

    @cached_property
    def use_cases(self) -> MetaConnectionUseCaseFactories:
        return MetaConnectionUseCaseFactories(self._dependencies)

    @cached_property
    def operators(self) -> MetaConnectionOperatorFactories:
        return MetaConnectionOperatorFactories(self._dependencies, self.use_cases)
