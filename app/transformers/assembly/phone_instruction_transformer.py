from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.assistants.assembly_sources import AssistantInstructionSource
from app.schemas.typings.assistants.strings import SystemPromptText
from app.utilities.assembly.example_sections import build_example_section
from app.utilities.assembly.instruction_parts import (
    InstructionParts,
    collect_instruction_parts,
)
from app.utilities.assembly.instruction_rule_sections import (
    build_emergency_section,
    build_handoff_section,
    build_niche_rule_section,
    build_prohibition_section,
)
from app.utilities.assembly.instruction_sections import (
    build_language_section,
    build_style_section,
    join_sections,
)
from app.utilities.assembly.phone_instruction_sections import (
    build_phone_answer_format_section,
    build_phone_booking_section,
    build_phone_role_section,
    build_spoken_fact_section,
)
from app.utilities.channels.voice_service import CALLER_ID_BOUND_TOOLS


class PhoneInstructionTransformer(
    TransformerContract[AssistantInstructionSource, SystemPromptText]
):
    """
    Compose the phone instruction of an assistant version: the voice agent's
    prompt (concept section 7, "the same instruction and tools as the chat").

    It has the sections of the chat instruction with four differences: the
    greeting of the call carries the AI disclosure, the fact table is
    written the way it is said (prices with the currency name, spoken hours
    and dates, no links), answers are short spoken sentences that never
    read a link aloud and never promise a text no tool result announced,
    and it names only the voice agent's tools: none that read or change a
    caller's bookings (CALLER_ID_BOUND_TOOLS), so existing bookings go to a
    colleague. Like the chat instruction it has no current date: the voice
    platform adds the call's date and time in a "Current call" block per
    call, and nothing about the caller (a caller id proves nobody's
    identity).
    """

    def transform(self, input_data: AssistantInstructionSource) -> SystemPromptText:
        parts: InstructionParts = collect_instruction_parts(input_data)
        tools: list[AssistantToolName] = [
            tool for tool in input_data.tools if tool not in CALLER_ID_BOUND_TOOLS
        ]
        sections: list[list[str]] = [
            build_phone_role_section(
                parts.business_name, parts.business_type, parts.location
            ),
            build_language_section(parts.language_names, parts.default_language_name),
            build_style_section(parts.tone),
            build_spoken_fact_section(parts.facts, tools),
            build_phone_booking_section(
                tools,
                parts.country_name,
                parts.timezone_name,
                has_sister_locations=input_data.business.brand_id is not None,
            ),
            build_handoff_section(
                parts.business_handoff_rules,
                parts.niche_handoff_rules,
                parts.staff_language_name,
            ),
            build_prohibition_section(
                parts.owner_forbidden_rules, parts.niche_forbidden_rules
            ),
            build_niche_rule_section(parts.niche_rules),
            build_emergency_section(parts.emergency_number),
            build_phone_answer_format_section(tools),
            build_example_section(input_data.niche.example_exchanges, tools),
        ]
        return SystemPromptText(join_sections(sections))
