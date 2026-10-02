from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import (
    BookingRules,
    BusinessAddress,
    BusinessContacts,
    BusinessLink,
    BusinessProfileDocument,
    OpeningInterval,
    ProfileAnswer,
)
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.profiles.business_profile import BusinessProfileView
from app.schemas.dto.setup.profile_patch import PatchProfileCommand, ProfilePatch
from app.schemas.typings.profiles.constrained_strings import QuestionKey
from app.schemas.typings.profiles.strings import (
    ForbiddenRuleText,
    HandoffRuleText,
    ToneText,
)
from app.utilities.knowledge.opening_hours import validate_opening_intervals
from app.utilities.knowledge.profile_sections import (
    build_booking_rules,
    check_address,
    check_rules,
    check_tone,
    validate_links,
)
from app.utilities.knowledge.profile_views import (
    build_contacts_audit_entry,
    new_profile,
    to_profile_view,
)
from app.utilities.setup.profile_patching import (
    apply_answer_changes,
    build_stale_profile_error,
    next_revision_time,
    normalize_answer_changes,
    patch_contacts,
)


class PatchProfileUseCase(UseCaseContract[PatchProfileCommand, BusinessProfileView]):
    """
    Autosave of the business profile: only the fields present in the patch
    change, so the cabinet can save every field as the owner edits it.

    Every field is validated like a wizard step before anything is stored.
    The change is made on the profile as stored at that moment (two fields
    saved at once never undo each other); with `expected_updated_at` an
    edit made from an older profile is refused (409 stale_revision).
    Niche answers change one question at a time, contacts one phone at a
    time; a change of contact phones is written to the audit log.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        business_profile_repo: BusinessProfileRepoContract,
        audit_log_repo: AuditLogRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        phone_number_parser: PhoneNumberParserContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PatchProfileCommand) -> BusinessProfileView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.actor_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        template: NicheTemplate = self._niche_template_registry.get(business.niche_key)
        patch: ProfilePatch = input_data.patch
        provided: set[str] = patch.model_fields_set
        # Validated up front: a rejected field changes nothing.
        address: BusinessAddress | None = check_address(patch.address)
        hours: list[OpeningInterval] = validate_opening_intervals(
            patch.hours or [], subject="Opening hours"
        )
        booking_rules: BookingRules | None = build_booking_rules(
            patch.booking_rules, template, business
        )
        handoff_rules: list[HandoffRuleText] = check_rules(
            patch.handoff_rules or [], subject="handoff"
        )
        forbidden: list[ForbiddenRuleText] = check_rules(
            patch.forbidden or [], subject="forbidden"
        )
        tone: ToneText | None = check_tone(patch.tone)
        links: list[BusinessLink] = validate_links(patch.links or [])
        answer_changes: dict[QuestionKey, ProfileAnswer | None] = (
            normalize_answer_changes(
                template, patch.answers or [], self._phone_number_parser, business
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._business_profile_repo.insert_if_absent(new_profile(business, now))
        previous_contacts: list[BusinessContacts] = []

        def change(stored: BusinessProfileDocument) -> BusinessProfileDocument:
            if (
                patch.expected_updated_at is not None
                and stored.updated_at != patch.expected_updated_at
            ):
                raise build_stale_profile_error(stored.updated_at)

            previous_contacts[:] = [stored.contacts.model_copy()]
            stored.niche_key = business.niche_key
            if patch.answers_language is not None:
                stored.answers_language = patch.answers_language
            if "address" in provided:
                stored.address = address
            if "hours" in provided:
                stored.hours = hours
            if patch.contacts is not None:
                stored.contacts = patch_contacts(
                    stored.contacts, patch.contacts, self._phone_number_parser, business
                )
            if "booking_rules" in provided:
                stored.booking_rules = booking_rules
            if "handoff_rules" in provided:
                stored.handoff_rules = handoff_rules
            if "forbidden" in provided:
                stored.forbidden = forbidden
            if "tone" in provided:
                stored.tone = tone
            if "links" in provided:
                stored.links = links
            if answer_changes:
                stored.niche_answers = apply_answer_changes(
                    template, stored.niche_answers, answer_changes
                )
            if patch.is_recording_notice_enabled is not None:
                stored.is_recording_notice_enabled = patch.is_recording_notice_enabled

            stored.updated_at = next_revision_time(now, stored.updated_at)
            return stored

        saved: BusinessProfileDocument | None = self._business_profile_repo.modify(
            business.id, change
        )
        if saved is not None and previous_contacts != [saved.contacts]:
            self._audit_log_repo.append(
                build_contacts_audit_entry(business.id, input_data.actor_id, now)
            )

        return to_profile_view(business, saved)
