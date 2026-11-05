"""The platform admin's niche template editor (R17, migration 1221)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.language_negotiation import parse_language_parameter
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.niche_texts.niche_text_commands import (
    NicheTextCommand,
    NicheTextEditorQuery,
    NicheTextHistoryQuery,
    NicheTextOverviewQuery,
    RevertNicheTextsCommand,
    RevertNicheTextsRequest,
    SaveNicheTextDraftCommand,
    SaveNicheTextDraftRequest,
)
from app.schemas.dto.niche_texts.niche_text_views import (
    NicheTextEditorView,
    NicheTextHistoryView,
    NicheTextReleaseView,
    NicheTextStatusList,
)
from app.schemas.typings.users.prefixed_id import UserId

read_draft_body = build_json_body_dependency(SaveNicheTextDraftRequest)
read_revert_body = build_json_body_dependency(RevertNicheTextsRequest)
NICHE_PATH: str = "/v1/admin/niche-templates/{niche_key}"


def build_admin_niche_text_router(
    list_niche_texts_operator: OperatorContract[
        NicheTextOverviewQuery, NicheTextStatusList
    ],
    get_niche_text_editor_operator: OperatorContract[
        NicheTextEditorQuery, NicheTextEditorView
    ],
    save_niche_text_draft_operator: OperatorContract[
        SaveNicheTextDraftCommand, NicheTextEditorView
    ],
    discard_niche_text_draft_operator: OperatorContract[NicheTextCommand, None],
    publish_niche_texts_operator: OperatorContract[
        NicheTextCommand, NicheTextReleaseView
    ],
    revert_niche_texts_operator: OperatorContract[
        RevertNicheTextsCommand, NicheTextReleaseView
    ],
    list_niche_text_versions_operator: OperatorContract[
        NicheTextHistoryQuery, NicheTextHistoryView
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (platform admins whose role may manage niche templates: SUPER):
        GET    /v1/admin/niche-templates?language=      every niche's state
        GET    /v1/admin/niche-templates/{niche_key}?language=
                                                        its editor in a language
        PUT    /v1/admin/niche-templates/{niche_key}/draft
                                                        a language's texts of
                                                        the draft {language, texts}
        DELETE /v1/admin/niche-templates/{niche_key}/draft  discard it (204)
        POST   /v1/admin/niche-templates/{niche_key}/publish
                                                        the draft as the next
                                                        version (step-up; audited)
        POST   /v1/admin/niche-templates/{niche_key}/revert
                                                        an earlier version's texts
                                                        again {version}, 0: the
                                                        code's (step-up; audited)
        GET    /v1/admin/niche-templates/{niche_key}/versions  the history
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    def niche_of(raw_niche_key: str) -> NicheKey:
        return parse_path_identifier(raw_niche_key, NicheKey, "Niche")

    @router.get("/v1/admin/niche-templates")
    def list_niche_templates(
        user_id: Annotated[UserId, Depends(current_user)],
        language: Annotated[str | None, Query()] = None,
    ) -> NicheTextStatusList:
        return list_niche_texts_operator.operate(
            NicheTextOverviewQuery(
                user_id=user_id, language=parse_language_parameter(language)
            )
        )

    @router.get(NICHE_PATH)
    def get_niche_template_editor(
        niche_key: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: Annotated[str | None, Query()] = None,
    ) -> NicheTextEditorView:
        return get_niche_text_editor_operator.operate(
            NicheTextEditorQuery(
                user_id=user_id,
                niche_key=niche_of(niche_key),
                language=parse_language_parameter(language),
            )
        )

    @router.put(
        f"{NICHE_PATH}/draft",
        openapi_extra=describe_json_body(SaveNicheTextDraftRequest),
    )
    def save_niche_template_draft(
        niche_key: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[SaveNicheTextDraftRequest, Depends(read_draft_body)],
    ) -> NicheTextEditorView:
        return save_niche_text_draft_operator.operate(
            SaveNicheTextDraftCommand(
                user_id=user_id,
                niche_key=niche_of(niche_key),
                language=body.language,
                texts=body.texts,
            )
        )

    @router.delete(f"{NICHE_PATH}/draft", status_code=status.HTTP_204_NO_CONTENT)
    def discard_niche_template_draft(
        niche_key: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        discard_niche_text_draft_operator.operate(
            NicheTextCommand(
                user_id=user_id,
                niche_key=niche_of(niche_key),
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post(f"{NICHE_PATH}/publish")
    def publish_niche_template(
        niche_key: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> NicheTextReleaseView:
        return publish_niche_texts_operator.operate(
            NicheTextCommand(
                user_id=user_id,
                niche_key=niche_of(niche_key),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        f"{NICHE_PATH}/revert",
        openapi_extra=describe_json_body(RevertNicheTextsRequest),
    )
    def revert_niche_template(
        niche_key: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[RevertNicheTextsRequest, Depends(read_revert_body)],
    ) -> NicheTextReleaseView:
        return revert_niche_texts_operator.operate(
            RevertNicheTextsCommand(
                user_id=user_id,
                niche_key=niche_of(niche_key),
                version=body.version,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(f"{NICHE_PATH}/versions")
    def list_niche_template_versions(
        niche_key: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> NicheTextHistoryView:
        return list_niche_text_versions_operator.operate(
            NicheTextHistoryQuery(user_id=user_id, niche_key=niche_of(niche_key))
        )

    return router
