from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.assistants.assembly_sources import AssistantInstructionSource
from app.schemas.typings.assistants.strings import SystemPromptText
from app.utilities.assembly.answer_format_sections import (
    build_answer_format_section,
)
from app.utilities.assembly.example_sections import build_example_section
from app.utilities.assembly.instruction_parts import (
    InstructionParts,
    collect_instruction_parts,
)
from app.utilities.assembly.instruction_sections import (
    build_booking_section,
    build_emergency_section,
    build_fact_section,
    build_handoff_section,
    build_language_section,
    build_message_section,
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
    Compose the chat instruction of an assistant version from the niche
    template and the profile, by code and without a model (concept
    section 4).

    Sections: role and AI disclosure, languages, style, the fact table (an
    overview and the first items for a big catalog), bookings (or requests
    when the version does not book), handoff rules with urgency,
    prohibitions, niche rules, the country's emergency number, how a
    message is built (the customer's words are fenced and never pose as the
    platform), the answer format and the niche's example exchanges. Every
    platform rule is stated once. The text is English for the model and
    contains no current date or random value, so the same source always
    gives the same bytes.
    """

    def transform(self, input_data: AssistantInstructionSource) -> SystemPromptText:
        parts: InstructionParts = collect_instruction_parts(input_data)
        sections: list[list[str]] = [
            build_role_section(
                parts.business_name, parts.business_type, parts.location
            ),
            build_language_section(parts.language_names, parts.default_language_name),
            build_style_section(parts.tone),
            build_fact_section(parts.facts, input_data.tools),
            build_booking_section(
                input_data.tools, parts.country_name, parts.timezone_name
            ),
            build_handoff_section(
                parts.business_handoff_rules,
                parts.niche_handoff_rules,
                parts.staff_language_name,
            ),
            build_prohibition_section(parts.forbidden_rules),
            build_niche_rule_section(parts.niche_rules),
            build_emergency_section(parts.emergency_number),
            build_message_section(),
            build_answer_format_section(input_data.tools),
            build_example_section(input_data.niche.example_exchanges, input_data.tools),
        ]
        return SystemPromptText(join_sections(sections))
