from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.domain.brands import BrandMember
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.brands.brand_views import (
    BrandLocationView,
    BrandMemberView,
    BrandView,
    BrandViewSource,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.brands.brand_access import find_brand_member, visible_location_ids


class BrandViewTransformer(TransformerContract[BrandViewSource, BrandView]):
    """
    Shape a brand for one member: the locations they reach (all of them
    for a brand owner, the assigned ones for a regional manager) and, for
    brand owners only, the team with their contacts.
    """

    def transform(self, input_data: BrandViewSource) -> BrandView:
        brand = input_data.brand
        viewer: BrandMember | None = find_brand_member(brand, input_data.viewer_id)
        if viewer is None:
            raise NotFoundError(f"Brand {brand.id} was not found.")

        primary_id: BusinessId | None = (
            input_data.locations[0].id if input_data.locations else None
        )
        visible: set[BusinessId] = set(
            visible_location_ids(
                brand,
                input_data.viewer_id,
                [location.id for location in input_data.locations],
            )
        )
        is_owner: bool = viewer.role is BrandMemberRole.BRAND_OWNER
        return BrandView(
            id=brand.id,
            name=brand.name,
            viewer_role=viewer.role,
            locations=[
                describe_location(location, location.id == primary_id)
                for location in input_data.locations
                if location.id in visible
            ],
            members=(
                describe_members(brand.members, input_data.member_users)
                if is_owner
                else []
            ),
            created_at=brand.created_at,
        )


def describe_location(
    location: BusinessDocument, is_primary: bool
) -> BrandLocationView:
    return BrandLocationView(
        business_id=location.id,
        name=location.name,
        city=location.city,
        status=location.status,
        niche_key=location.niche_key,
        plan_key=location.plan_key,
        country_code=location.country_code,
        currency_code=location.currency_code,
        is_primary=is_primary,
    )


def describe_members(
    members: list[BrandMember],
    users: list[UserDocument],
) -> list[BrandMemberView]:
    users_by_id: dict[UserId, UserDocument] = {user.id: user for user in users}
    views: list[BrandMemberView] = []
    for member in members:
        user: UserDocument | None = users_by_id.get(member.user_id)
        views.append(
            BrandMemberView(
                user_id=member.user_id,
                role=member.role,
                business_ids=list(member.business_ids),
                display_name=None if user is None else user.display_name,
                phone_number=None if user is None else user.phone_number,
                email=None if user is None else user.email,
                is_verified=False if user is None else user.is_verified,
            )
        )

    return views
