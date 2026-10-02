from app.contracts.transformer_contract import TransformerContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.assistants.assembly_sources import AssistantInstructionSource
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.assistants.strings import SystemPromptText
from app.utilities.assembly.fact_formatting import (
    describe_language,
    describe_languages,
    read_english_rule_lines,
    read_english_text,
    unique_preserving_order,
)
from app.utilities.assembly.instruction_sections import (
    build_answer_format_section,
    build_booking_section,
    build_emergency_section,
    build_fact_section,
    build_handoff_section,
    build_language_section,
    build_niche_rule_section,
    build_prohibition_section,
    build_role_section,
    build_style_section,
    join_sections,
)


class AssistantInstructionTransformer(
    TransformerContract[AssistantInstructionSource, SystemPromptText]
):
    """
    Compose the instruction of an assistant version from the niche template
    and the profile, by code and without a model (concept section 4).

    Sections: role and AI disclosure, languages, style, the fact table,
    bookings (or requests when the version does not book), handoff rules with
    urgency, prohibitions, niche rules, the country's emergency number, and
    the answer format for voice and chat. The text is English for the model
    and contains no current date or random value, so the same source always
    gives the same bytes.
    """

    def transform(self, input_data: AssistantInstructionSource) -> SystemPromptText:
        business: BusinessDocument = input_data.business
        profile: BusinessProfileDocument = input_data.profile
        niche: NicheTemplate = input_data.niche
        location: str = ", ".join(
            part
            for part in (
                str(business.city).strip() if business.city is not None else "",
                str(input_data.country.english_name).strip(),
            )
            if part != ""
        )
        business_handoff_rules: list[str] = unique_preserving_order(
            [str(rule) for rule in profile.handoff_rules]
        )
        known_handoff_rules: set[str] = {
            rule.casefold() for rule in business_handoff_rules
        }
        niche_handoff_rules: list[str] = [
            rule
            for rule in unique_preserving_order(
                read_english_rule_lines(niche.default_handoff_rules)
            )
            if rule.casefold() not in known_handoff_rules
        ]
        forbidden_rules: list[str] = unique_preserving_order(
            [
                *(str(rule) for rule in profile.forbidden),
                *read_english_rule_lines(niche.default_forbidden_rules),
            ]
        )
        sections: list[list[str]] = [
            build_role_section(
                str(business.name),
                read_english_text(niche.names),
                location,
            ),
            build_language_section(
                describe_languages(business.languages, input_data.language_profiles),
                describe_language(
                    business.default_language,
                    input_data.language_profiles,
                ),
            ),
            build_style_section(str(profile.tone) if profile.tone else None),
            build_fact_section(input_data.facts, input_data.tools),
            build_booking_section(
                input_data.tools,
                str(input_data.country.english_name),
                str(business.timezone),
            ),
            build_handoff_section(business_handoff_rules, niche_handoff_rules),
            build_prohibition_section(forbidden_rules),
            build_niche_rule_section(
                unique_preserving_order([str(rule) for rule in niche.prompt_rules])
            ),
            build_emergency_section(str(input_data.country.emergency_number)),
            build_answer_format_section(input_data.tools),
        ]
        return SystemPromptText(join_sections(sections))
