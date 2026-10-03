"""Assistant versions: assembly, autotests, publishing and rollback."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
    AssembleAssistantVersionRequest,
    AssistantVersionQuery,
    AssistantVersionsQuery,
    PublishAssistantVersionCommand,
    PublishAssistantVersionRequest,
    RollbackAssistantVersionCommand,
    RunAutotestsCommand,
    RunAutotestsRequest,
)
from app.schemas.dto.assistants.assistant_views import (
    AssistantVersionDetails,
    AssistantVersionSummary,
    AutotestRunView,
)
from app.schemas.dto.errors import ErrorBody
from app.schemas.dto.go_live import GoLiveReadiness
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

VERSIONS_PATH: str = "/v1/businesses/{business_id}/assistant-versions"
VERSION_PATH: str = VERSIONS_PATH + "/{version_id}"
REFUSAL_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_403_FORBIDDEN: {
        "model": ErrorBody,
        "description": "Not allowed; reasons[].code force_publish_admin_only.",
    },
    status.HTTP_409_CONFLICT: {
        "model": ErrorBody,
        "description": (
            "Refused; reasons[].code names each failed go-live check "
            "(subscription_or_trial, dpa, profile_gaps, staff_contact, "
            "autotests, voice_configuration) or the version state "
            "(version_already_live, version_archived, version_not_archived)."
        ),
    },
}


read_assemble_body = build_json_body_dependency(
    AssembleAssistantVersionRequest,
    optional=True,
)
read_run_autotests_body = build_json_body_dependency(
    RunAutotestsRequest,
    optional=True,
)
read_publish_body = build_json_body_dependency(
    PublishAssistantVersionRequest,
    optional=True,
)


def build_assistant_router(
    assemble_assistant_version_operator: OperatorContract[
        AssembleAssistantVersionCommand,
        AssistantVersionDetails,
    ],
    list_assistant_versions_operator: OperatorContract[
        AssistantVersionsQuery,
        list[AssistantVersionSummary],
    ],
    get_assistant_version_operator: OperatorContract[
        AssistantVersionQuery,
        AssistantVersionDetails,
    ],
    get_autotest_run_operator: OperatorContract[AssistantVersionQuery, AutotestRunView],
    get_go_live_readiness_operator: OperatorContract[
        AssistantVersionQuery,
        GoLiveReadiness,
    ],
    run_autotests_operator: OperatorContract[RunAutotestsCommand, AutotestRunView],
    publish_assistant_version_operator: OperatorContract[
        PublishAssistantVersionCommand,
        AssistantVersionDetails,
    ],
    rollback_assistant_version_operator: OperatorContract[
        RollbackAssistantVersionCommand,
        AssistantVersionDetails,
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (all require a bearer token; reads are for owners and staff,
    changes for owners):
        POST /v1/businesses/{business_id}/assistant-versions
             assemble a version, then start its autotests unless
             run_autotests is false (201; the version is TESTING while the
             background worker plays them)
        GET  /v1/businesses/{business_id}/assistant-versions
             version history, newest first
        GET  /v1/businesses/{business_id}/assistant-versions/{version_id}
             one version with its instruction and fact table
        GET  .../assistant-versions/{version_id}/autotest-run
             latest autotest run of the version (RUNNING while it plays)
        GET  .../assistant-versions/{version_id}/go-live-readiness
             the go-live checklist of the version: subscription_or_trial,
             dpa, profile_gaps, staff_contact, autotests and (voice
             versions) voice_configuration, each ok or not, blocking or not
        POST .../assistant-versions/{version_id}/autotests
             start the autotests again, optionally narrowed (202; only a
             run over every language and kind can make a version READY)
        POST .../assistant-versions/{version_id}/publish
             make a READY version live once the trial or subscription,
             the DPA and the profile allow it (accept_failed_tests forces an
             untested one, platform admins only)
        POST .../assistant-versions/{version_id}/rollback
             make an earlier, archived version live again

    A refused publish or rollback (409, or 403 for accept_failed_tests by a
    non-admin) lists machine-readable `reasons`: the failed go-live check
    codes with their details, or version_already_live, version_archived,
    version_not_archived, force_publish_admin_only.
    """

    router = APIRouter(tags=["assistant"], responses=standard_error_responses())

    @router.post(
        VERSIONS_PATH,
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(
            AssembleAssistantVersionRequest,
            optional=True,
        ),
    )
    def assemble_assistant_version(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[AssembleAssistantVersionRequest, Depends(read_assemble_body)],
    ) -> AssistantVersionDetails:
        return assemble_assistant_version_operator.operate(
            AssembleAssistantVersionCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
            )
        )

    @router.get(VERSIONS_PATH)
    def list_assistant_versions(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> list[AssistantVersionSummary]:
        return list_assistant_versions_operator.operate(
            AssistantVersionsQuery(
                user_id=user_id,
                business_id=parse_business_id(business_id),
            )
        )

    @router.get(VERSION_PATH)
    def get_assistant_version(
        business_id: str,
        version_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AssistantVersionDetails:
        return get_assistant_version_operator.operate(
            build_version_query(user_id, business_id, version_id)
        )

    @router.get(VERSION_PATH + "/autotest-run")
    def get_autotest_run(
        business_id: str,
        version_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AutotestRunView:
        return get_autotest_run_operator.operate(
            build_version_query(user_id, business_id, version_id)
        )

    @router.get(VERSION_PATH + "/go-live-readiness")
    def get_go_live_readiness(
        business_id: str,
        version_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> GoLiveReadiness:
        return get_go_live_readiness_operator.operate(
            build_version_query(user_id, business_id, version_id)
        )

    @router.post(
        VERSION_PATH + "/autotests",
        status_code=status.HTTP_202_ACCEPTED,
        openapi_extra=describe_json_body(RunAutotestsRequest, optional=True),
    )
    def run_autotests(
        business_id: str,
        version_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[RunAutotestsRequest, Depends(read_run_autotests_body)],
    ) -> AutotestRunView:
        return run_autotests_operator.operate(
            RunAutotestsCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                version_id=parse_version_id(version_id),
                languages=body.languages,
                kinds=body.kinds,
            )
        )

    @router.post(
        VERSION_PATH + "/publish",
        openapi_extra=describe_json_body(
            PublishAssistantVersionRequest,
            optional=True,
        ),
        responses=REFUSAL_RESPONSES,
    )
    def publish_assistant_version(
        business_id: str,
        version_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[PublishAssistantVersionRequest, Depends(read_publish_body)],
    ) -> AssistantVersionDetails:
        return publish_assistant_version_operator.operate(
            PublishAssistantVersionCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                version_id=parse_version_id(version_id),
                accept_failed_tests=body.accept_failed_tests,
            )
        )

    @router.post(VERSION_PATH + "/rollback", responses=REFUSAL_RESPONSES)
    def rollback_assistant_version(
        business_id: str,
        version_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AssistantVersionDetails:
        return rollback_assistant_version_operator.operate(
            RollbackAssistantVersionCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                version_id=parse_version_id(version_id),
            )
        )

    return router


def parse_business_id(raw_business_id: str) -> BusinessId:
    """Path segment -> BusinessId; malformed ids are reported as not found."""

    return parse_path_identifier(raw_business_id, BusinessId, "Business")


def parse_version_id(raw_version_id: str) -> AssistantVersionId:
    """Path segment -> AssistantVersionId; malformed ids are not found."""

    return parse_path_identifier(
        raw_version_id, AssistantVersionId, "Assistant version"
    )


def build_version_query(
    user_id: UserId,
    raw_business_id: str,
    raw_version_id: str,
) -> AssistantVersionQuery:
    """Read query for one version from raw path segments."""

    return AssistantVersionQuery(
        user_id=user_id,
        business_id=parse_business_id(raw_business_id),
        version_id=parse_version_id(raw_version_id),
    )
