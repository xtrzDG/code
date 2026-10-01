"""
Typed providers of the generic role chain (conventions: an endpoint backed
by one use case is `PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(
use_case)))`). Input and output types flow from the use case's contract to
the operator, so a router builder given the wrong operator fails type
checking.
"""

from dependency_injector.providers import Factory, Provider

from app.contracts.operator_contract import OperatorContract
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.pipeline_contract import PipelineContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.operators.business_scoped_pipeline_operator import (
    BusinessScopedPipelineOperator,
)
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline


def use_case_orchestrator[InputData, OutputData](
    use_case: Provider[UseCaseContract[InputData, OutputData]],
) -> Factory[OrchestratorContract[InputData, OutputData]]:
    """Orchestrator of an endpoint that needs exactly one use case."""

    return Factory(UseCaseOrchestrator[InputData, OutputData], use_case=use_case)


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
    of the business its input names.
    """

    return Factory(
        BusinessScopedPipelineOperator[InputData, OutputData],
        pipeline=pipeline,
        storage_scope=storage_scope,
    )
