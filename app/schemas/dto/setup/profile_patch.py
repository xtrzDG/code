"""Autosave of the profile: change only the fields sent, on every edit."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.domain.profiles import BusinessAddress, BusinessLink, OpeningInterval
from app.schemas.dto.profiles.business_profile import (
    BookingRulesInput,
    ContactsInput,
    ProfileAnswerInput,
)
from app.schemas.typings.businesses.booleans import IsRecordingNoticeEnabled
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.profiles.strings import (
    ForbiddenRuleText,
    HandoffRuleText,
    ToneText,
)
from app.schemas.typings.users.prefixed_id import UserId


class ProfilePatch(ImmutableDTO):
    """
    Partial change of the business profile (PATCH, for autosave).

    Only the fields present in the body change; an explicit null clears
    an optional section (address, booking rules, tone). `answers` changes
    only the questions it names (an empty answer clears that question);
    `contacts` only the phones it names. With `expected_updated_at` (the
    `updated_at` the cabinet last saw) a change made from an older profile
    is refused with 409 stale_revision instead of overwriting newer edits.

    Example: {"hours": [{"weekday": 1, "opens_at": 540, "closes_at": 1080}]}.
    """

    expected_updated_at: Microseconds | None = None
    answers_language: LanguageTag | None = None
    address: BusinessAddress | None = None
    hours: list[OpeningInterval] | None = None
    contacts: ContactsInput | None = None
    booking_rules: BookingRulesInput | None = None
    handoff_rules: list[HandoffRuleText] | None = None
    forbidden: list[ForbiddenRuleText] | None = None
    tone: ToneText | None = None
    links: list[BusinessLink] | None = None
    answers: list[ProfileAnswerInput] | None = None
    is_recording_notice_enabled: IsRecordingNoticeEnabled | None = None


class PatchProfileCommand(ImmutableDTO):
    """
    Save the fields of a profile patch; `actor_id` is recorded when contact
    phones change.
    """

    business_id: BusinessId
    actor_id: UserId
    patch: ProfilePatch
