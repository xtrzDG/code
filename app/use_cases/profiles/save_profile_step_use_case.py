from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.knowledge import KnowledgeItemSource
from app.schemas.constants.niches import ProfileWizardStep
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessContacts, BusinessProfileDocument
from app.schemas.dto.knowledge_admin import KnowledgeItemUpsertInput
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.profiles import (
    BookingRulesStepInput,
    ChannelsStepInput,
    ContactsAndHoursStepInput,
    FaqAndHandoffStepInput,
    NicheAndLanguagesStepInput,
    OfferStepInput,
    ProfileStepInput,
    ProfileStepSaveResult,
    SaveProfileStepCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.knowledge.knowledge_items import (
    faq_entry_to_upsert_input,
    to_item_details,
    upsert_knowledge_items,
)
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


class SaveProfileStepUseCase(
    UseCaseContract[SaveProfileStepCommand, ProfileStepSaveResult]
):
    """
    Save one step of the profile wizard and keep the others (partial progress).

    Each step replaces only its own sections and its own niche answers. The
    offer and FAQ steps upsert knowledge items. Everything is validated
    before anything is stored, so a rejected step changes nothing. Changes
    of contact phones (often a manager's personal mobile) are written to the
    audit log. Moving the business to testing is assembly's job, not this one.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        audit_log_repo: AuditLogRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        phone_number_parser: PhoneNumberParserContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SaveProfileStepCommand) -> ProfileStepSaveResult:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        now: Microseconds = self._wall_clock.now_unix()
        template: NicheTemplate = self._niche_template_registry.get(business.niche_key)
        profile: BusinessProfileDocument = self._business_profile_repo.get_by_business(
            business.id
        ) or new_profile(business, now)
        previous_contacts: BusinessContacts = profile.contacts.model_copy()
        profile.niche_key = business.niche_key
        knowledge_inputs: list[KnowledgeItemUpsertInput] = []

        step_input: ProfileStepInput = input_data.step_input
        step: ProfileWizardStep
        match step_input:
            case NicheAndLanguagesStepInput():
                step = ProfileWizardStep.NICHE_AND_LANGUAGES
                if step_input.answers_language is not None:
                    profile.answers_language = step_input.answers_language
            case ContactsAndHoursStepInput():
                step = ProfileWizardStep.CONTACTS_AND_HOURS
                profile.address = check_address(step_input.address)
                profile.hours = validate_opening_intervals(
                    step_input.hours,
                    subject="Opening hours",
                )
                profile.contacts = parse_contacts(
                    step_input.contacts,
                    self._phone_number_parser,
                    business,
                )
            case OfferStepInput():
                step = ProfileWizardStep.OFFER
                knowledge_inputs = list(step_input.items)
            case BookingRulesStepInput():
                step = ProfileWizardStep.BOOKING_RULES
                profile.booking_rules = build_booking_rules(
                    step_input.booking_rules,
                    template,
                    business,
                )
            case FaqAndHandoffStepInput():
                step = ProfileWizardStep.FAQ_AND_HANDOFF
                knowledge_inputs = [
                    faq_entry_to_upsert_input(entry) for entry in step_input.faq
                ]
                profile.handoff_rules = check_rules(
                    step_input.handoff_rules, subject="handoff"
                )
                profile.forbidden = check_rules(
                    step_input.forbidden, subject="forbidden"
                )
                profile.tone = check_tone(step_input.tone)
            case ChannelsStepInput():
                step = ProfileWizardStep.CHANNELS
                profile.links = validate_links(step_input.links)
                profile.is_recording_notice_enabled = (
                    step_input.is_recording_notice_enabled
                )

        profile.niche_answers = merge_niche_answers(
            template=template,
            current_answers=profile.niche_answers,
            answer_inputs=step_input.answers,
            step=step,
            phone_number_parser=self._phone_number_parser,
            country_code=business.country_code,
        )
        saved_items: list[KnowledgeItemDocument] = upsert_knowledge_items(
            business=business,
            template=template,
            existing_items=self._knowledge_item_repo.list_by_business(business.id),
            item_inputs=knowledge_inputs,
            source=KnowledgeItemSource.PROFILE,
            now=now,
        )
        profile.updated_at = now

        for item in saved_items:
            self._knowledge_item_repo.save(item)

        self._business_profile_repo.save(profile)
        if profile.contacts != previous_contacts:
            self._audit_log_repo.append(
                build_contacts_audit_entry(business.id, input_data.actor_id, now)
            )

        return ProfileStepSaveResult(
            step=step,
            profile=to_profile_view(business, profile),
            saved_knowledge_items=[
                to_item_details(item, business.currency_code, business.owner_language)
                for item in saved_items
            ],
        )
