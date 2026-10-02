from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.businesses import (
    BusinessMemberView,
    BusinessView,
    BusinessViewSource,
    ManagerContactView,
)
from app.schemas.typings.users.prefixed_id import UserId


class BusinessViewTransformer(TransformerContract[BusinessViewSource, BusinessView]):
    """
    Shape a business for the cabinet.

    Members keep their stored order; a member whose user record is missing
    is still listed with the id and role only.
    """

    def transform(self, input_data: BusinessViewSource) -> BusinessView:
        business: BusinessDocument = input_data.business
        users_by_id: dict[UserId, UserDocument] = {
            user.id: user for user in input_data.member_users
        }
        members: list[BusinessMemberView] = []
        viewer_role: BusinessMemberRole | None = None
        for member in business.members:
            if member.user_id == input_data.viewer_id:
                viewer_role = member.role

            user: UserDocument | None = users_by_id.get(member.user_id)
            members.append(
                BusinessMemberView(
                    user_id=member.user_id,
                    role=member.role,
                    display_name=None if user is None else user.display_name,
                    phone_number=None if user is None else user.phone_number,
                    email=None if user is None else user.email,
                    is_verified=False if user is None else user.is_verified,
                )
            )

        return BusinessView(
            id=business.id,
            name=business.name,
            niche_key=business.niche_key,
            country_code=business.country_code,
            city=business.city,
            timezone=business.timezone,
            currency_code=business.currency_code,
            languages=list(business.languages),
            default_language=business.default_language,
            owner_language=business.owner_language,
            plan_key=business.plan_key,
            status=business.status,
            service_mode=business.service_mode,
            data_region=business.data_region,
            recording_retention_days=business.recording_retention_days,
            members=members,
            manager_contacts=[
                ManagerContactView(
                    name=contact.name,
                    channel=contact.channel,
                    address=contact.address,
                    language=contact.language,
                    preferences=contact.preferences,
                    telegram_username=contact.telegram_username,
                )
                for contact in business.manager_contacts
            ],
            published_assistant_version_id=business.published_assistant_version_id,
            revision=business.revision,
            viewer_role=viewer_role,
            created_at=business.created_at,
        )
