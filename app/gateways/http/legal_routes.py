"""The platform's legal texts and its sub-processor list (public)."""

from fastapi import APIRouter, Request, Response

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.language_negotiation import (
    negotiate_language,
    parse_language_parameter,
)
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.query_parsing import parse_optional
from app.schemas.constants.legal import LegalDocumentKind
from app.schemas.dto.legal import (
    LegalDocumentQuery,
    LegalDocumentView,
    LegalOverviewQuery,
    LegalOverviewView,
    SubprocessorListQuery,
    SubprocessorListView,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.legal.constrained_strings import LegalDocumentVersion
from app.schemas.typings.localization.constrained_strings import LanguageTag

type SubprocessorsOperator = OperatorContract[
    SubprocessorListQuery, SubprocessorListView
]
type LegalDocumentOperator = OperatorContract[LegalDocumentQuery, LegalDocumentView]
type LegalOverviewOperator = OperatorContract[LegalOverviewQuery, LegalOverviewView]

# The texts change only with a release (or on the day a published version
# takes effect): browsers and the cabinet's server may keep them a while.
LEGAL_CACHE_CONTROL: str = "public, max-age=300"


def build_legal_router(
    get_subprocessors_operator: SubprocessorsOperator,
    get_legal_document_operator: LegalDocumentOperator,
    get_legal_overview_operator: LegalOverviewOperator,
) -> APIRouter:
    """
    Routes (no token):
        GET /v1/legal/subprocessors?language=      the sub-processor list
        GET /v1/legal/overview      drafts or final, the DPA in force and
                                    the operator's details
        GET /v1/legal/{document}?language=&version=
                                 terms, privacy, cookies or security: the
                                 version in force, or the one asked for

    The language comes from `?language=`, else Accept-Language; the answer
    says which language it is in (its base language, else English). The
    data processing agreement keeps its own route, /v1/legal/dpa/{version}.
    """

    router = APIRouter(tags=["legal"], responses=standard_error_responses())

    @router.get("/v1/legal/subprocessors")
    def get_subprocessors(
        request: Request,
        response: Response,
        language: str | None = None,
    ) -> SubprocessorListView:
        response.headers["Cache-Control"] = LEGAL_CACHE_CONTROL
        return get_subprocessors_operator.operate(
            SubprocessorListQuery(language=request_language(request, language))
        )

    @router.get("/v1/legal/overview")
    def get_legal_overview(response: Response) -> LegalOverviewView:
        response.headers["Cache-Control"] = LEGAL_CACHE_CONTROL
        return get_legal_overview_operator.operate(LegalOverviewQuery())

    @router.get("/v1/legal/{document}")
    def get_legal_document(
        request: Request,
        response: Response,
        document: str,
        language: str | None = None,
        version: str | None = None,
    ) -> LegalDocumentView:
        response.headers["Cache-Control"] = LEGAL_CACHE_CONTROL
        return get_legal_document_operator.operate(
            LegalDocumentQuery(
                kind=parse_document_kind(document),
                language=request_language(request, language),
                version=parse_optional(version, LegalDocumentVersion, "version"),
            )
        )

    return router


def request_language(request: Request, raw_language: str | None) -> LanguageTag | None:
    """`?language=`, else the browser's preferred language, else None (English)."""

    return parse_language_parameter(raw_language) or negotiate_language(
        request.headers.get("accept-language")
    )


def parse_document_kind(raw_document: str) -> LegalDocumentKind:
    """terms, privacy, cookies or security; anything else is 404."""

    try:
        return LegalDocumentKind(raw_document)
    except ValueError as error:
        raise NotFoundError("There is no such legal document.") from error
