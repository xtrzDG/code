from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.starter_registries import StarterAnswerRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.knowledge import KnowledgeItemSource
from app.schemas.constants.setup import StarterSection
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.resources import ResourceInput
from app.schemas.dto.setup.starter_answers import (
    ApplyStarterAnswersCommand,
    StarterAnswersApplied,
)
from app.schemas.dto.setup.starter_catalog import StarterAnswers
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.knowledge_item_views import to_item_details
from app.utilities.knowledge.knowledge_items import upsert_knowledge_items
from app.utilities.knowledge.profile_views import new_profile, to_profile_view
from app.utilities.knowledge.resource_rules import build_resource, to_resource_view
from app.utilities.setup.starter_profile import (
    PROFILE_SECTIONS,
    StarterProfileValues,
    build_starter_profile_values,
    fill_empty_sections,
)
from app.utilities.setup.starter_views import (
    faq_views,
    missing_faq_inputs,
    offered_sections,
    resource_input,
)

STARTER_AUDIT_ENTITY: AuditEntityName = AuditEntityName(
    "business_profile.starter_answers"
)


class ApplyStarterAnswersUseCase(
    UseCaseContract[ApplyStarterAnswersCommand, StarterAnswersApplied]
):
    """
    The owner accepts the niche's starter answers in one call.

    Only empty sections are filled (hours, booking rules, handoff and
    forbidden rules, tone), changed on the profile as stored at that moment
    so an edit saved meanwhile is never overwritten; a section the owner
    has filled is kept. Frequent questions with a ready answer become FAQ
    items unless the business already has that question; the first resource
    is created only for a business without any. Offer examples and prices
    are never applied: the profile keeps asking for prices. The acceptance
    is written to the audit log.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        audit_log_repo: AuditLogRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        starter_answer_registry: StarterAnswerRegistryContract,
        localized_text_resolver: LocalizedTextResolverContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._starter_answer_registry: StarterAnswerRegistryContract = (
            starter_answer_registry
        )
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ApplyStarterAnswersCommand) -> StarterAnswersApplied:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
                # Done-for-you setup: support may, with the owner's consent.
                support_may_change=True,
            )
        )
        language: LanguageTag = input_data.request.language or business.owner_language
        template: NicheTemplate = self._niche_template_registry.get(business.niche_key)
        starters: StarterAnswers = self._starter_answer_registry.get(
            business.niche_key, business.country_code
        )
        sections: list[StarterSection] = self._choose_sections(
            input_data, template, starters
        )
        # Everything is built and validated before anything is stored.
        values: StarterProfileValues = build_starter_profile_values(
            business, template, starters, language, self._resolver
        )
        now: Microseconds = self._wall_clock.now_unix()
        applied: list[StarterSection] = []
        profile: BusinessProfileDocument | None = self._fill_profile(
            business, sections, values, applied, now
        )
        saved_items: list[KnowledgeItemDocument] = []
        if StarterSection.FAQ in sections:
            saved_items = self._add_faq(business, template, starters, input_data, now)
            if saved_items:
                applied.append(StarterSection.FAQ)

        resource: ResourceDocument | None = None
        if StarterSection.RESOURCE in sections:
            resource = self._add_resource(business, template, starters, language, now)
            if resource is not None:
                applied.append(StarterSection.RESOURCE)

        if applied:
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    actor_id=input_data.user_id,
                    action=AuditAction.UPDATE,
                    entity=STARTER_AUDIT_ENTITY,
                    entity_id=AuditEntityReference(str(business.id)),
                    created_at=now,
                    updated_at=now,
                )
            )

        return StarterAnswersApplied(
            applied_sections=[section for section in sections if section in applied],
            kept_sections=[section for section in sections if section not in applied],
            profile=to_profile_view(business, profile),
            saved_knowledge_items=[
                to_item_details(item, business.currency_code, business.owner_language)
                for item in saved_items
            ],
            resource=None if resource is None else to_resource_view(resource),
        )

    def _choose_sections(
        self,
        command: ApplyStarterAnswersCommand,
        template: NicheTemplate,
        starters: StarterAnswers,
    ) -> list[StarterSection]:
        offered: list[StarterSection] = offered_sections(template, starters)
        requested: list[StarterSection] = (
            offered if command.request.sections is None else command.request.sections
        )
        unknown: list[str] = [
            section.value for section in requested if section not in offered
        ]
        if unknown:
            raise ValidationFailedError(
                f"Niche {template.key} has no starter answers for: "
                + ", ".join(unknown)
                + "."
            )

        return [section for section in offered if section in requested]

    def _fill_profile(
        self,
        business: BusinessDocument,
        sections: list[StarterSection],
        values: StarterProfileValues,
        applied: list[StarterSection],
        now: Microseconds,
    ) -> BusinessProfileDocument | None:
        profile_sections: list[StarterSection] = [
            section for section in sections if section in PROFILE_SECTIONS
        ]
        if profile_sections == []:
            return self._business_profile_repo.get_by_business(business.id)

        self._business_profile_repo.insert_if_absent(new_profile(business, now))

        def fill(stored: BusinessProfileDocument) -> BusinessProfileDocument | None:
            applied.clear()
            applied.extend(fill_empty_sections(stored, profile_sections, values))
            if applied == []:
                return None

            stored.updated_at = now
            return stored

        filled: BusinessProfileDocument | None = self._business_profile_repo.modify(
            business.id, fill
        )
        return filled or self._business_profile_repo.get_by_business(business.id)

    def _add_faq(
        self,
        business: BusinessDocument,
        template: NicheTemplate,
        starters: StarterAnswers,
        command: ApplyStarterAnswersCommand,
        now: Microseconds,
    ) -> list[KnowledgeItemDocument]:
        language: LanguageTag = command.request.language or business.owner_language
        existing: list[KnowledgeItemDocument] = (
            self._knowledge_item_repo.list_by_business(business.id)
        )
        items: list[KnowledgeItemDocument] = upsert_knowledge_items(
            business=business,
            template=template,
            existing_items=existing,
            item_inputs=missing_faq_inputs(
                faq_views(starters, language, self._resolver),
                existing,
                language,
                command.request.faq_keys,
            ),
            source=KnowledgeItemSource.PROFILE,
            now=now,
        )
        for item in items:
            self._knowledge_item_repo.save(item)

        return items

    def _add_resource(
        self,
        business: BusinessDocument,
        template: NicheTemplate,
        starters: StarterAnswers,
        language: LanguageTag,
        now: Microseconds,
    ) -> ResourceDocument | None:
        suggested: ResourceInput | None = resource_input(
            template, starters, language, self._resolver
        )
        existing: list[ResourceDocument] = self._resource_repo.list_by_business(
            business.id
        )
        if suggested is None or existing != []:
            return None

        resource: ResourceDocument = build_resource(
            business, template, suggested, existing, now
        )
        self._resource_repo.save(resource)
        return resource
