"""Brands: chains of locations run by one team (cabinet, bearer token)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.idempotency.idempotency_dependency import (
    IdempotencyDependency,
)
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.value import ValuePeriod
from app.schemas.dto.brands.brand_commands import (
    AddBrandLocationCommand,
    BrandQuery,
    CloneBrandLocationCommand,
    CreateBrandCommand,
    DeleteBrandCommand,
    RemoveBrandLocationCommand,
    RenameBrandCommand,
)
from app.schemas.dto.brands.brand_dashboard import BrandDashboard, BrandDashboardQuery
from app.schemas.dto.brands.brand_requests import (
    AddBrandLocationRequest,
    CloneBrandLocationRequest,
    CreateBrandRequest,
    RenameBrandRequest,
)
from app.schemas.dto.brands.brand_views import BrandView
from app.schemas.dto.businesses import BusinessView
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.brands.prefixed_id import BrandId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

BRAND_PATH: str = "/v1/brands/{brand_id}"
BRAND_OWNER_ACTION: str = (
    "Brand owners only: a regional manager gets 403 `access_denied`. It is an "
    "owner's action in every location of the brand, so while one of them asks "
    "its team for two factors, a session signed in with the login code alone "
    "gets 403 `mfa_required`."
)
JOINING_A_BRAND: str = (
    "Only an owner of the business, in no brand yet, brings it in; while the "
    "business asks its team for two factors, a session signed in with the "
    "login code alone gets 403 `mfa_required`."
)
read_create_body = build_json_body_dependency(CreateBrandRequest)
read_rename_body = build_json_body_dependency(RenameBrandRequest)
read_location_body = build_json_body_dependency(AddBrandLocationRequest)
read_clone_body = build_json_body_dependency(CloneBrandLocationRequest)


def brand_of(raw_id: str) -> BrandId:
    return parse_path_identifier(raw_id, BrandId, "Brand")


def build_brand_router(
    *,
    current_user: CurrentUserDependency,
    idempotent: IdempotencyDependency,
    list_brands: OperatorContract[UserId, list[BrandView]],
    get_brand: OperatorContract[BrandQuery, BrandView],
    create_brand: OperatorContract[CreateBrandCommand, BrandView],
    rename_brand: OperatorContract[RenameBrandCommand, BrandView],
    delete_brand: OperatorContract[DeleteBrandCommand, None],
    get_dashboard: OperatorContract[BrandDashboardQuery, BrandDashboard],
    add_location: OperatorContract[AddBrandLocationCommand, BrandView],
    remove_location: OperatorContract[RemoveBrandLocationCommand, None],
    clone_location: OperatorContract[CloneBrandLocationCommand, BusinessView],
) -> APIRouter:
    """
    Routes (members of the brand's team; others get 404):
        GET    /v1/brands                         my brands
        POST   /v1/brands                         a brand from a business I own
        GET    {B}                                the brand as I see it
        PATCH  {B}                                brand owners: rename
        DELETE {B}                                brand owners: an empty brand
        GET    {B}/dashboard                      every location side by side
        POST   {B}/locations                      brand owners: add my business
        DELETE {B}/locations/{business_id}        brand owners: take one out
        POST   {B}/locations/clone                brand owners: new location from…
    """

    router = APIRouter(tags=["brands"], responses=standard_error_responses())

    @router.get("/v1/brands")
    def list_my_brands(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> list[BrandView]:
        return list_brands.operate(user_id)

    @router.post(
        "/v1/brands",
        description=JOINING_A_BRAND,
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(CreateBrandRequest),
        dependencies=[Depends(idempotent)],
    )
    def create_brand_route(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CreateBrandRequest, Depends(read_create_body)],
    ) -> BrandView:
        return create_brand.operate(
            CreateBrandCommand(
                user_id=user_id,
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(BRAND_PATH)
    def get_brand_route(
        brand_id: str, user_id: Annotated[UserId, Depends(current_user)]
    ) -> BrandView:
        return get_brand.operate(
            BrandQuery(user_id=user_id, brand_id=brand_of(brand_id))
        )

    @router.patch(
        BRAND_PATH,
        description=BRAND_OWNER_ACTION,
        openapi_extra=describe_json_body(RenameBrandRequest),
    )
    def rename_brand_route(
        brand_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[RenameBrandRequest, Depends(read_rename_body)],
    ) -> BrandView:
        return rename_brand.operate(
            RenameBrandCommand(
                user_id=user_id, brand_id=brand_of(brand_id), request=body
            )
        )

    @router.delete(
        BRAND_PATH,
        description=BRAND_OWNER_ACTION,
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_brand_route(
        brand_id: str, user_id: Annotated[UserId, Depends(current_user)]
    ) -> None:
        delete_brand.operate(
            DeleteBrandCommand(user_id=user_id, brand_id=brand_of(brand_id))
        )

    @router.get(f"{BRAND_PATH}/dashboard")
    def get_brand_dashboard(
        brand_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        period: Annotated[str | None, Query()] = None,
        date_from: Annotated[str | None, Query(alias="from")] = None,
        date_to: Annotated[str | None, Query(alias="to")] = None,
    ) -> BrandDashboard:
        """
        Each location's value (staff see no money), customer sources (brand
        owners) and waiting work over `period` (today, 7d, 30d, 90d,
        last_week, last_month) or local dates `from` to `to`; default 30 days.
        """

        return get_dashboard.operate(
            BrandDashboardQuery(
                user_id=user_id,
                brand_id=brand_of(brand_id),
                period=parse_optional(period, ValuePeriod, "period"),
                date_from=parse_optional(date_from, LocalDate, "from"),
                date_to=parse_optional(date_to, LocalDate, "to"),
            )
        )

    @router.post(
        f"{BRAND_PATH}/locations",
        description=f"{BRAND_OWNER_ACTION} {JOINING_A_BRAND}",
        openapi_extra=describe_json_body(AddBrandLocationRequest),
    )
    def add_brand_location(
        request: Request,
        brand_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[AddBrandLocationRequest, Depends(read_location_body)],
    ) -> BrandView:
        return add_location.operate(
            AddBrandLocationCommand(
                user_id=user_id,
                brand_id=brand_of(brand_id),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete(
        f"{BRAND_PATH}/locations/{{business_id}}",
        description=BRAND_OWNER_ACTION,
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def remove_brand_location(
        request: Request,
        brand_id: str,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        remove_location.operate(
            RemoveBrandLocationCommand(
                user_id=user_id,
                brand_id=brand_of(brand_id),
                location_id=parse_path_identifier(business_id, BusinessId, "Business"),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        f"{BRAND_PATH}/locations/clone",
        description=BRAND_OWNER_ACTION,
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(CloneBrandLocationRequest),
        dependencies=[Depends(idempotent)],
    )
    def clone_brand_location(
        request: Request,
        brand_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CloneBrandLocationRequest, Depends(read_clone_body)],
    ) -> BusinessView:
        return clone_location.operate(
            CloneBrandLocationCommand(
                user_id=user_id,
                brand_id=brand_of(brand_id),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
