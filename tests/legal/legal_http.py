"""The legal router over the real texts, the registry and a set clock."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.legal_routes import build_legal_router
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.registries.legal.legal_document_registry import (
    DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
)
from app.registries.legal.legal_text_registry import LegalTextRegistry
from app.registries.legal.subprocessor_registry import SubprocessorRegistry
from app.schemas.dto.legal import SubprocessorEntry
from app.use_cases.legal.get_legal_document_use_case import GetLegalDocumentUseCase
from app.use_cases.legal.get_subprocessors_use_case import GetSubprocessorsUseCase
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.legal.legal_world import Clock


def build_legal_client(
    clock: Clock,
    entries: tuple[SubprocessorEntry, ...] | None = None,
    documents: Path = DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
) -> TestClient:
    registry = (
        SubprocessorRegistry() if entries is None else SubprocessorRegistry(entries)
    )
    subprocessors = GetSubprocessorsUseCase(
        subprocessor_registry=registry,
        localized_text_resolver=LocalizedTextResolver(),
        wall_clock=clock.wall_clock,
    )
    legal_document = GetLegalDocumentUseCase(
        legal_text_registry=LegalTextRegistry(documents),
        wall_clock=clock.wall_clock,
    )
    application = FastAPI()
    install_error_handlers(application)
    application.include_router(
        build_legal_router(
            get_subprocessors_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(subprocessors))
            ),
            get_legal_document_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(legal_document))
            ),
        )
    )
    return TestClient(application)
