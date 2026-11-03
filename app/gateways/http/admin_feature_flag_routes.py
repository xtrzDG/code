"""
The feature flags of staged rollouts (REL-08), for the platform admin
(Bearer auth, a two-factor session).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.feature_flags import (
    FeatureFlagCheck,
    FeatureFlagCheckQuery,
    FeatureFlagCommand,
    FeatureFlagList,
    FeatureFlagListQuery,
    FeatureFlagRequest,
    FeatureFlagView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.feature_flags.constrained_strings import FeatureFlagName
from app.schemas.typings.users.prefixed_id import UserId

FEATURE_FLAGS_PATH: str = "/v1/admin/feature-flags"
read_flag_body = build_json_body_dependency(FeatureFlagRequest)


def build_admin_feature_flag_router(
    *,
    current_user: CurrentUserDependency,
    list_feature_flags: OperatorContract[FeatureFlagListQuery, FeatureFlagList],
    set_feature_flag: OperatorContract[FeatureFlagCommand, FeatureFlagView],
    check_feature_flag: OperatorContract[FeatureFlagCheckQuery, FeatureFlagCheck],
) -> APIRouter:
    """
    Routes:
        GET /v1/admin/feature-flags
            every flag of the registry and how it stands; admins who see
            operations
        PUT /v1/admin/feature-flags/{flag_name}
            the whole new state of a flag (on, rollout percentage, the
            businesses it always and never holds for) and why; SUPER admins
            after a recent sign-in (401 step_up_required), audited on the
            platform's log; 404 for a name the registry lacks, 409 when it
            already stands so
        GET /v1/admin/feature-flags/{flag_name}/businesses/{business_id}
            whether the flag holds for that business now, why, and its
            bucket; admins who see operations
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.get(FEATURE_FLAGS_PATH)
    def list_admin_feature_flags(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> FeatureFlagList:
        return list_feature_flags.operate(FeatureFlagListQuery(user_id=user_id))

    @router.put(
        FEATURE_FLAGS_PATH + "/{flag_name}",
        openapi_extra=describe_json_body(FeatureFlagRequest),
    )
    def set_admin_feature_flag(
        flag_name: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[FeatureFlagRequest, Depends(read_flag_body)],
    ) -> FeatureFlagView:
        return set_feature_flag.operate(
            FeatureFlagCommand(
                user_id=user_id,
                name=parse_path_identifier(flag_name, FeatureFlagName, "Feature flag"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(FEATURE_FLAGS_PATH + "/{flag_name}/businesses/{business_id}")
    def check_admin_feature_flag(
        flag_name: str,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> FeatureFlagCheck:
        return check_feature_flag.operate(
            FeatureFlagCheckQuery(
                user_id=user_id,
                name=parse_path_identifier(flag_name, FeatureFlagName, "Feature flag"),
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    return router
