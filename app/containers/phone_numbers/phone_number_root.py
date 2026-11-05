from functools import cached_property

from app.containers.phone_numbers.phone_number_dependencies import (
    PhoneNumberDependencies,
)
from app.containers.phone_numbers.phone_number_use_case_factories import (
    PhoneNumberUseCaseFactories,
)


class PhoneNumberRoot:
    """
    The typed composition root of the phone numbers context (ADR 0010, like
    app/containers/feedback/): plain Python that builds the phone line's use
    cases and the numbers' two jobs from PhoneNumberDependencies, checked by
    mypy and pyright without a single `# type: ignore`. The dependency graph
    holds one root (BusinessUseCasesContainer.phone_number_root) and exposes
    the use cases the call orchestrators and turning the phone channel off
    call.
    """

    def __init__(self, dependencies: PhoneNumberDependencies) -> None:
        self._dependencies: PhoneNumberDependencies = dependencies

    @cached_property
    def use_cases(self) -> PhoneNumberUseCaseFactories:
        return PhoneNumberUseCaseFactories(self._dependencies)
