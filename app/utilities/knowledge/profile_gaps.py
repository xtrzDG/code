"""Find what is missing in a business profile (concept section 4, "what to add").

Blocking gaps stop going live because the assistant cannot work without
them: required niche answers, opening hours, a manager contact that gets
handoffs, bookings and leads, and for niches that take bookings also the
address, the booking rules and at least one active resource. Missing prices
and FAQ only make the assistant weaker.
"""

from collections.abc import Sequence

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import ProfileWizardStep
from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.profiles.profile_gaps import ProfileGapFinding
from app.schemas.typings.profiles.constrained_strings import QuestionKey
from app.utilities.knowledge.profile_texts import WIZARD_STEP_ORDER


def find_profile_gaps(
    template: NicheTemplate,
    business: BusinessDocument,
    profile: BusinessProfileDocument | None,
    knowledge_items: Sequence[KnowledgeItemDocument],
    resources: Sequence[ResourceDocument],
) -> list[ProfileGapFinding]:
    """Gaps ordered: blocking first, then by wizard step, then by question order."""

    findings: list[ProfileGapFinding] = []
    answered_keys: set[QuestionKey] = (
        set()
        if profile is None
        else {answer.question_key for answer in profile.niche_answers}
    )
    for question in template.questions:
        if question.is_required and question.key not in answered_keys:
            findings.append(
                ProfileGapFinding(
                    kind=ProfileGapKind.MISSING_REQUIRED_ANSWER,
                    step=question.step,
                    is_blocking=True,
                    question_key=question.key,
                )
            )

    if profile is None or profile.hours == []:
        findings.append(
            ProfileGapFinding(
                kind=ProfileGapKind.NO_OPENING_HOURS,
                step=ProfileWizardStep.CONTACTS_AND_HOURS,
                is_blocking=True,
            )
        )

    if profile is None or profile.address is None:
        findings.append(
            ProfileGapFinding(
                kind=ProfileGapKind.NO_ADDRESS,
                step=ProfileWizardStep.CONTACTS_AND_HOURS,
                is_blocking=template.takes_bookings,
            )
        )

    # Handoffs, bookings and leads reach staff only through manager contacts;
    # the profile's handoff phone is told to customers but notifies nobody.
    if business.manager_contacts == []:
        findings.append(
            ProfileGapFinding(
                kind=ProfileGapKind.NO_HANDOFF_CONTACT,
                step=ProfileWizardStep.CONTACTS_AND_HOURS,
                is_blocking=True,
            )
        )

    if template.takes_bookings:
        if profile is None or profile.booking_rules is None:
            findings.append(
                ProfileGapFinding(
                    kind=ProfileGapKind.NO_BOOKING_RULES,
                    step=ProfileWizardStep.BOOKING_RULES,
                    is_blocking=True,
                )
            )

        if not any(resource.is_active for resource in resources):
            findings.append(
                ProfileGapFinding(
                    kind=ProfileGapKind.NO_RESOURCES,
                    step=ProfileWizardStep.BOOKING_RULES,
                    is_blocking=True,
                )
            )

    active_items: list[KnowledgeItemDocument] = [
        item for item in knowledge_items if item.is_active
    ]
    if not any(item.price_minor is not None for item in active_items):
        findings.append(
            ProfileGapFinding(
                kind=ProfileGapKind.NO_PRICED_ITEMS,
                step=ProfileWizardStep.OFFER,
                is_blocking=False,
            )
        )

    if not any(item.kind is KnowledgeItemKind.FAQ for item in active_items):
        findings.append(
            ProfileGapFinding(
                kind=ProfileGapKind.NO_FAQ,
                step=ProfileWizardStep.FAQ_AND_HANDOFF,
                is_blocking=False,
            )
        )

    return sorted(
        findings,
        key=lambda finding: (
            not finding.is_blocking,
            WIZARD_STEP_ORDER.index(finding.step),
        ),
    )


def blocking_steps(findings: Sequence[ProfileGapFinding]) -> set[ProfileWizardStep]:
    """Steps that still miss something required."""

    return {finding.step for finding in findings if finding.is_blocking}
