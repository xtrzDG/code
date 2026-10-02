from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.assistants import BusinessFact
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.dto.assistants.assembly_sources import BusinessFactsSource
from app.utilities.assembly.fact_descriptions import (
    KNOWLEDGE_KIND_LABELS,
    LINK_LABELS,
    RESOURCE_KIND_NOUNS,
    describe_booking_rule_rows,
    describe_knowledge_item,
    describe_resource,
    describe_schedule_exception,
    humanize_niche_answer,
)
from app.utilities.assembly.fact_formatting import (
    describe_language,
    describe_languages,
    format_international_phone_number,
    format_weekly_hours,
    read_english_text,
)
from app.utilities.assembly.fact_table import append_fact

MAX_SCHEDULE_EXCEPTIONS: int = 30
KNOWLEDGE_KIND_ORDER: list[KnowledgeItemKind] = list(KnowledgeItemKind)
RESOURCE_KIND_ORDER: list[ResourceKind] = list(ResourceKind)
LINK_KIND_ORDER: list[BusinessLinkKind] = list(BusinessLinkKind)


class BusinessFactsTransformer(
    TransformerContract[BusinessFactsSource, list[BusinessFact]]
):
    """
    Build the fact table of an assistant version (concept section 4).

    Only stored values are used, never invented ones, and the same source
    always gives the same rows in the same order: identity and contacts,
    time zone and weekly hours, upcoming special days, answered niche
    questions, active knowledge items, bookable resources, booking rules,
    links and languages. Texts are English with locale-neutral values
    (24-hour times, ISO dates, "18.00 GEL"); the assistant translates them.
    """

    def transform(self, input_data: BusinessFactsSource) -> list[BusinessFact]:
        facts: list[BusinessFact] = []
        used_keys: set[str] = set()
        self._add_identity(input_data, facts, used_keys)
        self._add_hours(input_data.profile, facts, used_keys)
        self._add_schedule_exceptions(input_data, facts, used_keys)
        self._add_niche_answers(input_data, facts, used_keys)
        self._add_knowledge_items(input_data, facts, used_keys)
        self._add_resources(input_data, facts, used_keys)
        self._add_booking_rules(input_data, facts, used_keys)
        self._add_links(input_data.profile, facts, used_keys)
        self._add_languages(input_data, facts, used_keys)
        return facts

    def _add_identity(
        self,
        source: BusinessFactsSource,
        facts: list[BusinessFact],
        used_keys: set[str],
    ) -> None:
        business: BusinessDocument = source.business
        profile: BusinessProfileDocument = source.profile
        append_fact(facts, used_keys, "business_name", "Business name", business.name)
        append_fact(
            facts,
            used_keys,
            "business_type",
            "Type of business",
            read_english_text(source.niche.names),
        )
        if business.city is not None:
            append_fact(facts, used_keys, "city", "City", business.city)

        append_fact(facts, used_keys, "country", "Country", source.country.english_name)
        if profile.address is not None:
            append_fact(facts, used_keys, "address", "Address", profile.address.text)
            if profile.address.maps_url is not None:
                append_fact(
                    facts,
                    used_keys,
                    "maps_link",
                    "Location on the map",
                    profile.address.maps_url,
                )

        if profile.contacts.public_phone_number is not None:
            append_fact(
                facts,
                used_keys,
                "public_phone",
                "Public phone number",
                format_international_phone_number(profile.contacts.public_phone_number),
            )

        append_fact(facts, used_keys, "time_zone", "Time zone", business.timezone)

    def _add_hours(
        self,
        profile: BusinessProfileDocument,
        facts: list[BusinessFact],
        used_keys: set[str],
    ) -> None:
        if not profile.hours:
            return

        for weekday_name, hours_text in format_weekly_hours(profile.hours):
            append_fact(
                facts,
                used_keys,
                f"hours_{weekday_name.lower()}",
                f"Opening hours on {weekday_name}",
                hours_text,
            )

    def _add_schedule_exceptions(
        self,
        source: BusinessFactsSource,
        facts: list[BusinessFact],
        used_keys: set[str],
    ) -> None:
        resource_names: dict[str, str] = {
            str(resource.id): str(resource.name)
            for resource in source.resources
            if resource.is_active
        }
        upcoming_exceptions: list[ScheduleExceptionDocument] = sorted(
            (
                exception
                for exception in source.schedule_exceptions
                if exception.date >= source.today
                and (
                    exception.resource_id is None
                    or str(exception.resource_id) in resource_names
                )
            ),
            key=lambda exception: (
                str(exception.date),
                exception.resource_id is not None,
                resource_names.get(str(exception.resource_id), "").casefold(),
                str(exception.id),
            ),
        )
        for ordinal, exception in enumerate(
            upcoming_exceptions[:MAX_SCHEDULE_EXCEPTIONS],
            start=1,
        ):
            value: str = describe_schedule_exception(exception)
            if exception.resource_id is not None:
                value += f" (applies to {resource_names[str(exception.resource_id)]})"

            append_fact(
                facts,
                used_keys,
                f"special_day_{ordinal}",
                f"Special day {exception.date}",
                value,
            )

    def _add_niche_answers(
        self,
        source: BusinessFactsSource,
        facts: list[BusinessFact],
        used_keys: set[str],
    ) -> None:
        answers: dict[str, str] = {
            str(answer.question_key): str(answer.answer)
            for answer in source.profile.niche_answers
        }
        for question in source.niche.questions:
            answer_text: str | None = answers.get(str(question.key))
            if answer_text is None or answer_text.strip() == "":
                continue

            append_fact(
                facts,
                used_keys,
                str(question.fact_key),
                read_english_text(question.labels),
                humanize_niche_answer(question, answer_text),
            )

    def _add_knowledge_items(
        self,
        source: BusinessFactsSource,
        facts: list[BusinessFact],
        used_keys: set[str],
    ) -> None:
        active_items: list[KnowledgeItemDocument] = sorted(
            (item for item in source.knowledge_items if item.is_active),
            key=lambda item: (
                KNOWLEDGE_KIND_ORDER.index(item.kind),
                str(item.title).casefold(),
                str(item.id),
            ),
        )
        ordinals: dict[KnowledgeItemKind, int] = {}
        for item in active_items:
            ordinals[item.kind] = ordinals.get(item.kind, 0) + 1
            append_fact(
                facts,
                used_keys,
                f"{item.kind.value}_{ordinals[item.kind]}",
                f"{KNOWLEDGE_KIND_LABELS[item.kind]}: {item.title}",
                describe_knowledge_item(item, source.business.currency_code),
            )

    def _add_resources(
        self,
        source: BusinessFactsSource,
        facts: list[BusinessFact],
        used_keys: set[str],
    ) -> None:
        active_resources: list[ResourceDocument] = sorted(
            (resource for resource in source.resources if resource.is_active),
            key=lambda resource: (
                RESOURCE_KIND_ORDER.index(resource.kind),
                str(resource.name).casefold(),
                str(resource.id),
            ),
        )
        for ordinal, resource in enumerate(active_resources, start=1):
            append_fact(
                facts,
                used_keys,
                f"resource_{ordinal}",
                f"Bookable {RESOURCE_KIND_NOUNS[resource.kind]}: {resource.name}",
                describe_resource(resource, source.profile.booking_rules),
            )

    def _add_booking_rules(
        self,
        source: BusinessFactsSource,
        facts: list[BusinessFact],
        used_keys: set[str],
    ) -> None:
        if source.profile.booking_rules is None:
            return

        for key, label, value in describe_booking_rule_rows(
            source.profile.booking_rules,
            source.business.currency_code,
        ):
            append_fact(facts, used_keys, key, label, value)

    def _add_links(
        self,
        profile: BusinessProfileDocument,
        facts: list[BusinessFact],
        used_keys: set[str],
    ) -> None:
        for link in sorted(
            profile.links,
            key=lambda link: (LINK_KIND_ORDER.index(link.kind), str(link.url)),
        ):
            append_fact(
                facts,
                used_keys,
                f"link_{link.kind.value}",
                LINK_LABELS[link.kind],
                link.url,
            )

    def _add_languages(
        self,
        source: BusinessFactsSource,
        facts: list[BusinessFact],
        used_keys: set[str],
    ) -> None:
        append_fact(
            facts,
            used_keys,
            "languages",
            "Languages the business serves",
            describe_languages(source.business.languages, source.language_profiles),
        )
        append_fact(
            facts,
            used_keys,
            "default_language",
            "Default language",
            describe_language(
                source.business.default_language,
                source.language_profiles,
            ),
        )
