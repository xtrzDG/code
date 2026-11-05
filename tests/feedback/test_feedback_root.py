"""The feedback context's typed composition root (ADR 0010 pilot)."""

from app.containers.app import AppContainer
from app.containers.feedback.feedback_root import FeedbackRoot
from app.operators.business_scoped_pipeline_operator import (
    BusinessScopedPipelineOperator,
)
from app.operators.platform_wide_pipeline_operator import (
    PlatformWidePipelineOperator,
)
from app.use_cases.feedback.answers.answer_customer_signal_use_case import (
    AnswerCustomerSignalUseCase,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.workshop_container import replace_provider


def app_container() -> AppContainer:
    container = AppContainer()
    replace_provider(
        container.config.app_settings, assemble_app_settings(E2E_ENVIRONMENT)
    )
    return container


def test_the_graph_holds_one_root_for_use_cases_and_operators() -> None:
    container = app_container()

    root = container.use_cases.feedback.root()

    assert isinstance(root, FeedbackRoot)
    assert container.operators.feedback_root() is root
    assert root.use_cases is root.use_cases
    assert root.operators is root.operators


def test_the_job_runs_platform_wide_and_the_cabinet_in_its_business() -> None:
    feedback = app_container().operators.feedback

    assert isinstance(
        feedback.request_visit_feedback_operator(), PlatformWidePipelineOperator
    )
    for operator in (
        feedback.open_review_link_operator(),
        feedback.get_review_settings_operator(),
        feedback.update_review_settings_operator(),
        feedback.get_review_stats_operator(),
        feedback.list_feedback_requests_operator(),
    ):
        assert isinstance(operator, BusinessScopedPipelineOperator)


def test_every_call_builds_a_new_chain_like_a_factory() -> None:
    container = app_container()
    feedback = container.operators.feedback

    assert (
        feedback.get_review_settings_operator()
        is not feedback.get_review_settings_operator()
    )
    answer = container.use_cases.feedback.answer_customer_signal_use_case()
    assert isinstance(answer, AnswerCustomerSignalUseCase)
    assert answer is not container.use_cases.feedback.answer_customer_signal_use_case()
