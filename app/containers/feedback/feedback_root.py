from functools import cached_property

from app.containers.feedback.feedback_dependencies import FeedbackDependencies
from app.containers.feedback.feedback_operator_factories import (
    FeedbackOperatorFactories,
)
from app.containers.feedback.feedback_use_case_factories import (
    FeedbackUseCaseFactories,
)


class FeedbackRoot:
    """
    The typed composition root of the feedback context (ADR 0010): plain
    Python that builds its use cases and their operators from
    FeedbackDependencies, checked by mypy and pyright without a single
    `# type: ignore`. Its children are typed roots of their role, made once
    per root (functools.cached_property); the dependency graph holds one
    root (app/containers/use_cases/feedback_use_cases.py) and exposes what
    other contexts and the gateways call.
    """

    def __init__(self, dependencies: FeedbackDependencies) -> None:
        self._dependencies: FeedbackDependencies = dependencies

    @cached_property
    def use_cases(self) -> FeedbackUseCaseFactories:
        return FeedbackUseCaseFactories(self._dependencies)

    @cached_property
    def operators(self) -> FeedbackOperatorFactories:
        return FeedbackOperatorFactories(self._dependencies, self.use_cases)
