from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories import (
    AuditLogRepoContract,
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessContacts, BusinessProfileDocument
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.profiles import (
    BusinessProfileView,
    ProfileInput,
    SaveProfileCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.knowledge.niche_answers import merge_niche_answers
from app.utilities.knowledge.opening_hours import validate_opening_intervals
from app.utilities.knowledge.profile_sections import (
    build_booking_rules,
    check_address,
    check_rules,
    check_tone,
    parse_contacts,
    validate_links,
)
from app.utilities.knowledge.profile_views import (
    build_contacts_audit_entry,
    new_profile,
    to_profile_view,
)


class SaveProfileUseCase(UseCaseContract[SaveProfileCommand, BusinessProfileView]):
    """
    Replace the whole business profile (everything except the knowledge base).

    Applies the same validation as the wizard steps: niche answers, hours
    without overlaps, phones of any country in E.164, booking rules with the
    deposit in the business currency, one link per kind. Contact phone
    changes are written to the audit log.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        audit_log_repo: AuditLogRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        phone_number_parser: PhoneNumberParserContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SaveProfileCommand) -> BusinessProfileView:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        now: Microseconds = self._wall_clock.now_unix()
        template: NicheTemplate = self._niche_template_registry.get(business.niche_key)
        profile_input: ProfileInput = input_data.profile
        profile: BusinessProfileDocument = self._business_profile_repo.get_by_business(
            business.id
        ) or new_profile(business, now)
        previous_contacts: BusinessContacts = profile.contacts.model_copy()

        profile.niche_key = business.niche_key
        if profile_input.answers_language is not None:
            profile.answers_language = profile_input.answers_language

        profile.address = check_address(profile_input.address)
        profile.hours = validate_opening_intervals(
            profile_input.hours,
            subject="Opening hours",
        )
        profile.contacts = parse_contacts(
            profile_input.contacts,
            self._phone_number_parser,
            business,
        )
        profile.booking_rules = build_booking_rules(
            profile_input.booking_rules,
            template,
            business,
        )
        profile.handoff_rules = check_rules(
            profile_input.handoff_rules, subject="handoff"
        )
        profile.forbidden = check_rules(profile_input.forbidden, subject="forbidden")
        profile.tone = check_tone(profile_input.tone)
        profile.links = validate_links(profile_input.links)
        profile.niche_answers = merge_niche_answers(
            template=template,
            current_answers=[],
            answer_inputs=profile_input.answers,
            step=None,
            phone_number_parser=self._phone_number_parser,
            country_code=business.country_code,
        )
        profile.is_recording_notice_enabled = profile_input.is_recording_notice_enabled
        profile.updated_at = now

        self._business_profile_repo.save(profile)
        if profile.contacts != previous_contacts:
            self._audit_log_repo.append(
                build_contacts_audit_entry(business.id, input_data.actor_id, now)
            )

        return to_profile_view(business, profile)
