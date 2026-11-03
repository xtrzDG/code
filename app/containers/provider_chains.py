"""
Typed providers of the generic role chain (conventions: an endpoint backed
by one use case is `PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(
use_case)))`). Input and output types flow from the use case's contract to
the operator, so a router builder given the wrong operator fails type
checking.
"""

from collections.abc import Callable
from typing import cast

from dependency_injector.providers import Dependency, Factory, Provider

from app.contracts.acting_user import ActingUserInputContract
from app.contracts.operator_contract import OperatorContract
from app.contracts.orchestrator_contract import OrchestratorContract
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


def use_case_orchestrator[InputData, OutputData](
    use_case: Provider[UseCaseContract[InputData, OutputData]],
) -> Factory[OrchestratorContract[InputData, OutputData]]:
    """Orchestrator of an endpoint that needs exactly one use case."""

    return Factory(UseCaseOrchestrator[InputData, OutputData], use_case=use_case)


# Whether a person sees platform details: a platform admin of now (API-05).
type PlatformDetailsCheck = UseCaseContract[UserId, IsPlatformAdmin]


def platform_details_edge() -> Dependency[PlatformDetailsCheck]:
    """
    A container's typed edge to the conversation feed's
    `see_platform_details_use_case` (a use case contract is a protocol,
    which `instance_of` cannot check at run time).
    """

    return cast(Dependency[PlatformDetailsCheck], Dependency())


def team_view_orchestrator[InputData: ActingUserInputContract, OutputData](
    orchestrator: Provider[OrchestratorContract[InputData, OutputData]],
    see_platform_details: Provider[PlatformDetailsCheck],
    for_team: Callable[[OutputData], OutputData],
) -> Factory[OrchestratorContract[InputData, OutputData]]:
    """
    The orchestrator of an endpoint whose answer holds platform details:
    platform admins get it whole, everyone else `for_team(answer)` (API-05).
    """

    return Factory(
        TeamViewOrchestrator[InputData, OutputData],
        orchestrator=orchestrator,
        see_platform_details=see_platform_details,
        for_team=for_team,
    )


def orchestrator_pipeline[InputData, OutputData](
    orchestrator: Provider[OrchestratorContract[InputData, OutputData]],
) -> Factory[PipelineContract[InputData, OutputData]]:
    """Pipeline whose phase has a single orchestrator."""

    return Factory(
        OrchestratorPipeline[InputData, OutputData],
        orchestrator=orchestrator,
    )


def pipeline_operator[InputData, OutputData](
    pipeline: Provider[PipelineContract[InputData, OutputData]],
    storage_scope: Provider[StorageScopeContract],
) -> Factory[OperatorContract[InputData, OutputData]]:
    """
    Operator that runs one pipeline synchronously, inside the storage scope
    of the business its input names (an input without a business runs in
    the caller's scope: unscoped unless the caller entered one).
    """

    return Factory(
        BusinessScopedPipelineOperator[InputData, OutputData],
        pipeline=pipeline,
        storage_scope=storage_scope,
    )


def platform_pipeline_operator[InputData, OutputData](
    pipeline: Provider[PipelineContract[InputData, OutputData]],
    storage_scope: Provider[StorageScopeContract],
) -> Factory[OperatorContract[InputData, OutputData]]:
    """
    Operator of platform-level work (webhooks before their business is
    known, admin views, demo seeding, periodic jobs over every business):
    it runs the pipeline platform-wide, the explicit escalation of the
    fail-closed storage scope.
    """

    return Factory(
        PlatformWidePipelineOperator[InputData, OutputData],
        pipeline=pipeline,
        storage_scope=storage_scope,
    )
