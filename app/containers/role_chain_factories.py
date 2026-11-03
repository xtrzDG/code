"""
The generic role chain as plain typed functions, for the typed composition
roots (ADR 0010; the pilot is app/containers/feedback/). An endpoint backed
by one use case is `Operator(OrchestratorPipeline(UseCaseOrchestrator(
use_case)))`; the provider version is app/containers/provider_chains.py.
Every argument here is checked by mypy and pyright, the use case's input
and output types flow to the operator, and nothing is silenced.
"""

from collections.abc import Callable

from app.contracts.acting_user import ActingUserInputContract
from app.contracts.operator_contract import OperatorContract
from app.contracts.pipeline_contract import PipelineContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.operators.business_scoped_pipeline_operator import (
    BusinessScopedPipelineOperator,
)
from app.operators.platform_wide_pipeline_operator import (
    PlatformWidePipelineOperator,
)
from app.orchestrators.team_view_orchestrator import TeamViewOrchestrator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.typings.users.booleans import IsPlatformAdmin
from app.schemas.typings.users.prefixed_id import UserId


def use_case_pipeline[InputData, OutputData](
    use_case: UseCaseContract[InputData, OutputData],
) -> PipelineContract[InputData, OutputData]:
    """The pipeline and orchestrator of an endpoint with one use case."""

    return OrchestratorPipeline[InputData, OutputData](
        orchestrator=UseCaseOrchestrator[InputData, OutputData](use_case=use_case)
    )


def business_scoped_operator[InputData, OutputData](
    use_case: UseCaseContract[InputData, OutputData],
    storage_scope: StorageScopeContract,
) -> OperatorContract[InputData, OutputData]:
    """
    Runs the use case's chain in the storage scope of the business its
    input names (an input without a business runs in the caller's scope).
    """

    return BusinessScopedPipelineOperator[InputData, OutputData](
        pipeline=use_case_pipeline(use_case), storage_scope=storage_scope
    )


def team_view_operator[InputData: ActingUserInputContract, OutputData](
    use_case: UseCaseContract[InputData, OutputData],
    see_platform_details: UseCaseContract[UserId, IsPlatformAdmin],
    for_team: Callable[[OutputData], OutputData],
    storage_scope: StorageScopeContract,
) -> OperatorContract[InputData, OutputData]:
    """
    `business_scoped_operator` of an endpoint whose answer holds platform
    details: platform admins get it whole, everyone else `for_team(answer)`
    (TeamViewOrchestrator, API-05).
    """

    orchestrator = TeamViewOrchestrator[InputData, OutputData](
        orchestrator=UseCaseOrchestrator[InputData, OutputData](use_case=use_case),
        see_platform_details=see_platform_details,
        for_team=for_team,
    )
    return BusinessScopedPipelineOperator[InputData, OutputData](
        pipeline=OrchestratorPipeline[InputData, OutputData](orchestrator=orchestrator),
        storage_scope=storage_scope,
    )


def platform_wide_operator[InputData, OutputData](
    use_case: UseCaseContract[InputData, OutputData],
    storage_scope: StorageScopeContract,
) -> OperatorContract[InputData, OutputData]:
    """Runs platform-level work (a periodic job over every business)."""

    return PlatformWidePipelineOperator[InputData, OutputData](
        pipeline=use_case_pipeline(use_case), storage_scope=storage_scope
    )
