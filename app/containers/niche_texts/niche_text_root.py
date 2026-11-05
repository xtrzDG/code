from functools import cached_property

from app.containers.niche_texts.niche_text_dependencies import NicheTextDependencies
from app.containers.niche_texts.niche_text_operator_factories import (
    NicheTextOperatorFactories,
)
from app.containers.niche_texts.niche_text_use_case_factories import (
    NicheTextUseCaseFactories,
)


class NicheTextRoot:
    """
    The typed composition root of the platform admin's niche template
    editor (R17-NICHE-TEMPLATE-EDITOR, ADR 0010): plain Python that builds
    its use cases and their operators from NicheTextDependencies, checked by
    mypy and pyright without a single `# type: ignore`. The dependency
    graph holds one root (UseCasesContainer.niche_text_root); the admin
    routes take its operators.
    """

    def __init__(self, dependencies: NicheTextDependencies) -> None:
        self._dependencies: NicheTextDependencies = dependencies

    @cached_property
    def use_cases(self) -> NicheTextUseCaseFactories:
        return NicheTextUseCaseFactories(self._dependencies)

    @cached_property
    def operators(self) -> NicheTextOperatorFactories:
        return NicheTextOperatorFactories(self._dependencies, self.use_cases)
