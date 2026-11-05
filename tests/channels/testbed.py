"""Fakes and an in-memory wiring of the channels slice, shared by its tests.

Platforms are reached through the real HTTP clients over recording
`httpx.MockTransport`s; the conversation engine, the voice tool runner and
the greeting builder are fakes implementing their contracts. Phone numbers,
languages and texts use the real localization utilities (no network).
The wiring is layered: infrastructure, then use cases; this module adds the
HTTP client and the data builders.
"""

from fastapi.testclient import TestClient

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.strings import ChannelExternalId, ChannelSecret
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.users.prefixed_id import UserId
from tests.channels.channels_deliveries import ChannelsDeliveries
from tests.channels.channels_http import build_channels_http_client
from tests.channels.channels_settings import GEORGIA, CountrySetup


class ChannelsTestbed(ChannelsDeliveries):
    """
    Repositories, fakes and every channels component, wired in memory, with
    a background worker (`run_worker`) for the inbox and the outbox.
    """

    # --- HTTP -----------------------------------------------------------

    def build_http_client(self) -> TestClient:
        return build_channels_http_client(self)

    # --- Data builders --------------------------------------------------

    def add_user(self, token: str, locale: str = "en") -> UserId:
        user = UserDocument(
            login_method=LoginMethod.PHONE,
            locale=LanguageTag(locale),
            is_verified=True,
        )
        self.user_repo.save(user)
        self.authentication.users_by_token[token] = user.id
        return user.id

    def add_business(
        self,
        owner_id: UserId,
        country: CountrySetup = GEORGIA,
        name: str = "Funicular VR",
        staff_ids: list[UserId] | None = None,
        owner_language: str | None = None,
    ) -> BusinessDocument:
        members: list[BusinessMember] = [
            BusinessMember(user_id=owner_id, role=BusinessMemberRole.OWNER)
        ]
        members.extend(
            BusinessMember(user_id=staff_id, role=BusinessMemberRole.STAFF)
            for staff_id in staff_ids or []
        )
        languages: list[LanguageTag] = [LanguageTag(tag) for tag in country.languages]
        business = BusinessDocument(
            name=BusinessName(name),
            niche_key=NicheKey.ENTERTAINMENT,
            country_code=CountryCode(country.country_code),
            timezone=TimezoneName(country.timezone),
            currency_code=CurrencyCode(country.currency_code),
            languages=languages,
            default_language=languages[0],
            owner_language=LanguageTag(owner_language or country.languages[0]),
            plan_key=PlanKey.VOICE_AND_CHAT,
            data_region=DataRegion.EU,
            members=members,
        )
        self.business_repo.save(business)
        return business

    def add_channel(
        self,
        business_id: BusinessId,
        kind: ChannelKind,
        external_id: str | None = None,
        secret: str | None = None,
        status: ChannelStatus = ChannelStatus.CONNECTED,
    ) -> ChannelDocument:
        channel = ChannelDocument(
            business_id=business_id,
            kind=kind,
            external_id=None if external_id is None else ChannelExternalId(external_id),
            encrypted_secret=(
                None
                if secret is None
                else self.secret_cipher.encrypt(ChannelSecret(secret))
            ),
            status=status,
        )
        self.channel_repo.save(channel)
        return channel

    def audit_actions(self, business_id: BusinessId) -> list[tuple[str, str]]:
        return [
            (entry.action.value, str(entry.entity))
            for entry in self.audit_log_repo.list_by_business(business_id)
        ]
