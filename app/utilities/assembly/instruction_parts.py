"""
What the chat and the phone instruction of a version are both made of.

The two instructions differ only in how facts are written and how answers
look; everything else (who the assistant is, languages, rules, handoffs,
prohibitions, emergencies, examples) comes from the same source here, so a
rule is never stated differently on the phone than in chat.
"""

from dataclasses import dataclass

from app.schemas.domain.assistants import BusinessFact
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.assistants.assembly_sources import AssistantInstructionSource
from app.schemas.dto.niches import NicheTemplate
from app.utilities.assembly.fact_formatting import (
    describe_language,
    describe_languages,
    read_english_rule_lines,
    read_english_text,
    unique_preserving_order,
)
from app.utilities.assembly.fact_table_limits import limit_knowledge_facts


@dataclass(frozen=True)
class InstructionParts:
    """Plain texts the sections are composed from (technical record)."""

    business_name: str
    business_type: str
    location: str
    language_names: str
    default_language_name: str
    staff_language_name: str
    tone: str | None
    facts: list[BusinessFact]
    business_handoff_rules: list[str]
    niche_handoff_rules: list[str]
    forbidden_rules: list[str]
    niche_rules: list[str]
    country_name: str
    timezone_name: str
    emergency_number: str


def collect_instruction_parts(source: AssistantInstructionSource) -> InstructionParts:
    """
    The texts of both instructions. Handoff rules of the niche that the
    owner already lists are dropped; the fact table is limited for a big
    catalog (`limit_knowledge_facts`).
    """

    business: BusinessDocument = source.business
    profile: BusinessProfileDocument = source.profile
    niche: NicheTemplate = source.niche
    business_handoff_rules: list[str] = unique_preserving_order(
        [str(rule) for rule in profile.handoff_rules]
    )
    known_handoff_rules: set[str] = {rule.casefold() for rule in business_handoff_rules}
    return InstructionParts(
        business_name=str(business.name),
        business_type=read_english_text(niche.names),
        location=", ".join(
            part
            for part in (
                str(business.city).strip() if business.city is not None else "",
                str(source.country.english_name).strip(),
            )
            if part != ""
        ),
        language_names=describe_languages(business.languages, source.language_profiles),
        default_language_name=describe_language(
            business.default_language, source.language_profiles
        ),
        staff_language_name=describe_language(
            business.owner_language, source.language_profiles
        ),
        tone=str(profile.tone) if profile.tone else None,
        facts=limit_knowledge_facts(source.facts, source.knowledge_items),
        business_handoff_rules=business_handoff_rules,
        niche_handoff_rules=[
            rule
            for rule in unique_preserving_order(
                read_english_rule_lines(niche.default_handoff_rules)
            )
            if rule.casefold() not in known_handoff_rules
        ],
        forbidden_rules=unique_preserving_order(
            [
                *(str(rule) for rule in profile.forbidden),
                *read_english_rule_lines(niche.default_forbidden_rules),
            ]
        ),
        niche_rules=unique_preserving_order([str(rule) for rule in niche.prompt_rules]),
        country_name=str(source.country.english_name),
        timezone_name=str(business.timezone),
        emergency_number=str(source.country.emergency_number),
    )
