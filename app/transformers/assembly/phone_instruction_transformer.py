from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.assistants.assembly_sources import AssistantInstructionSource
from app.schemas.typings.assistants.strings import SystemPromptText
from app.utilities.assembly.example_sections import build_example_section
from app.utilities.assembly.instruction_parts import (
    InstructionParts,
    collect_instruction_parts,
)
from app.utilities.assembly.instruction_sections import (
    build_booking_section,
    build_emergency_section,
    build_handoff_section,
    build_language_section,
    build_niche_rule_section,
    build_prohibition_section,
    build_style_section,
    join_sections,
)
from app.utilities.assembly.phone_instruction_sections import (
    build_phone_answer_format_section,
    build_phone_role_section,
    build_spoken_fact_section,
)


class PhoneInstructionTransformer(
    TransformerContract[AssistantInstructionSource, SystemPromptText]
):
    """
    Compose the phone instruction of an assistant version: the voice agent's
    prompt (concept section 7, "the same instruction and tools as the chat").

    It has the sections of the chat instruction with three differences: the
    greeting of the call carries the AI disclosure, the fact table is
    written the way it is said (prices with the currency name, spoken hours
    and dates, no links), and answers are short spoken sentences that never
    read a link aloud (send_link texts it when it can). Like the chat
    instruction it has no current date: the voice platform adds the call's
    date, time and caller in a "Current call" block per call.
    """

    def transform(self, input_data: AssistantInstructionSource) -> SystemPromptText:
        parts: InstructionParts = collect_instruction_parts(input_data)
        sections: list[list[str]] = [
            build_phone_role_section(
                parts.business_name, parts.business_type, parts.location
            ),
            build_language_section(parts.language_names, parts.default_language_name),
            build_style_section(parts.tone),
            build_spoken_fact_section(parts.facts, input_data.tools),
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
            build_phone_answer_format_section(input_data.tools),
            build_example_section(input_data.niche.example_exchanges, input_data.tools),
        ]
        return SystemPromptText(join_sections(sections))
