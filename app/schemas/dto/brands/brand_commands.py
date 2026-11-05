"""
Commands of the brand routes. None of them names a `business_id` at the
top: a brand request runs in no business's storage scope, and every step
that touches a location's data enters that location's scope itself.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.brands import BrandMemberRole
from app.schemas.dto.brands.brand_requests import (
    AddBrandLocationRequest,
    ChangeBrandMemberRequest,
    CloneBrandLocationRequest,
    CreateBrandRequest,
    InviteBrandMemberRequest,
    RenameBrandRequest,
)
from app.schemas.typings.brands.prefixed_id import BrandId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId


class BrandAccessRequest(ImmutableDTO):
    """
    May the person act on the brand? Members may read; `required_role`
    BRAND_OWNER limits the action to its owners (the team, the locations,
    the shared knowledge, the name).
    """

    user_id: UserId
    brand_id: BrandId
    required_role: BrandMemberRole | None = None


class BrandQuery(ImmutableDTO):
    """One brand as a member sees it."""

    user_id: UserId
    brand_id: BrandId


class CreateBrandCommand(ImmutableDTO):
    """An owner makes one of their businesses the first location of a brand."""

    user_id: UserId
    request: CreateBrandRequest
    client_ip_address: ClientIpAddress | None = None


class RenameBrandCommand(ImmutableDTO):
    user_id: UserId
    brand_id: BrandId
    request: RenameBrandRequest


class DeleteBrandCommand(ImmutableDTO):
    """A brand owner removes a brand that has no locations left."""

    user_id: UserId
    brand_id: BrandId


class AddBrandLocationCommand(ImmutableDTO):
    user_id: UserId
    brand_id: BrandId
    request: AddBrandLocationRequest
    client_ip_address: ClientIpAddress | None = None


class RemoveBrandLocationCommand(ImmutableDTO):
    """A location leaves the brand; it stays its owners' business."""

    user_id: UserId
    brand_id: BrandId
    location_id: BusinessId
    client_ip_address: ClientIpAddress | None = None


class CloneBrandLocationCommand(ImmutableDTO):
    user_id: UserId
    brand_id: BrandId
    request: CloneBrandLocationRequest
    client_ip_address: ClientIpAddress | None = None


class InviteBrandMemberCommand(ImmutableDTO):
    user_id: UserId
    brand_id: BrandId
    invitation: InviteBrandMemberRequest
    client_ip_address: ClientIpAddress | None = None


class ChangeBrandMemberCommand(ImmutableDTO):
    user_id: UserId
    brand_id: BrandId
    member_user_id: UserId
    change: ChangeBrandMemberRequest
    client_ip_address: ClientIpAddress | None = None


class RemoveBrandMemberCommand(ImmutableDTO):
    user_id: UserId
    brand_id: BrandId
    member_user_id: UserId
    client_ip_address: ClientIpAddress | None = None


class LeaveBrandCommand(ImmutableDTO):
    """An owner of a location takes it out of its brand (a business route)."""

    user_id: UserId
    business_id: BusinessId
    client_ip_address: ClientIpAddress | None = None
