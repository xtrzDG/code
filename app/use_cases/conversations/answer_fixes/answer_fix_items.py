"""
The knowledge item behind an assistant answer, and the item an owner's
correction creates or updates: a question and its answer (FAQ), a rule or
an opening-hours line (policies), or the price of an offer.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.schemas.constants.knowledge import (
    AnswerCorrectionScope,
    KnowledgeItemKind,
    KnowledgeItemSource,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.conversation_feed.answer_corrections import (
    AnswerCorrectionRequest,
    CorrectionFactView,
)
from app.schemas.dto.niches import NicheTemplate
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_strings import KnowledgeTag
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.answer_fix_hints import (
    QUESTION_KINDS,
    looked_up_item_ids,
    match_item_by_question,
)
from app.utilities.knowledge.knowledge_item_checks import check_body, check_title
from app.utilities.knowledge.knowledge_items import find_matching_item

TEXT_KINDS: dict[AnswerCorrectionScope, KnowledgeItemKind] = {
    AnswerCorrectionScope.FAQ: KnowledgeItemKind.FAQ,
    AnswerCorrectionScope.RULE: KnowledgeItemKind.POLICY,
    AnswerCorrectionScope.HOURS: KnowledgeItemKind.POLICY,
}
HOURS_TAG: KnowledgeTag = KnowledgeTag("hours")


def to_fact_view(item: KnowledgeItemDocument) -> CorrectionFactView:
    return CorrectionFactView(
        knowledge_item_id=item.id,
        kind=item.kind,
        title=item.title,
        body=item.body,
        price_minor=item.price_minor,
        currency_code=item.currency_code,
    )


def fits_scope(item: KnowledgeItemDocument, scope: AnswerCorrectionScope) -> bool:
    """A priced offer for a price; a question or policy otherwise."""

    if scope is AnswerCorrectionScope.PRICE:
        return item.kind not in QUESTION_KINDS

    return item.kind in QUESTION_KINDS


def find_current_fact(
    knowledge_item_repo: KnowledgeItemRepoContract,
    business_id: BusinessId,
    answer: MessageDocument,
    question: str | None,
    scope: AnswerCorrectionScope,
) -> KnowledgeItemDocument | None:
    """
    The item an earlier correction of this answer made, else the first item
    the assistant looked up that fits the scope, else the item the question
    names.
    """

    corrected: KnowledgeItemDocument | None = knowledge_item_repo.find_by_correction(
        business_id, answer.id
    )
    if corrected is not None:
        return corrected

    item_ids: list[KnowledgeItemId] = []
    for raw_id in looked_up_item_ids(answer.tool_calls):
        try:
            item_ids.append(KnowledgeItemId(raw_id))
        except ValueError:
            continue

    looked_up = knowledge_item_repo.get_many(business_id, item_ids)
    for item_id in item_ids:
        item: KnowledgeItemDocument | None = looked_up.get(item_id)
        if item is not None and fits_scope(item, scope):
            return item

    if question is None:
        return None

    return match_item_by_question(
        knowledge_item_repo.list_by_business(business_id), question, scope
    )


def corrected_text_item(
    business: BusinessDocument,
    request: AnswerCorrectionRequest,
    target: KnowledgeItemDocument | None,
    items: Sequence[KnowledgeItemDocument],
    language: LanguageTag,
    now: Microseconds,
) -> tuple[KnowledgeItemDocument, bool]:
    """
    A question and its answer, a rule or an hours line: the target item
    updated, the item of the same kind and title, or a new one.

    Raises:
        ValidationFailedError: the question or the answer is missing.
    """

    if request.question is None or request.correct_answer is None:
        raise ValidationFailedError("Write the question and the correct answer.")

    title: KnowledgeTitle = check_title(KnowledgeTitle(request.question.strip()))
    body: KnowledgeBody | None = check_body(request.correct_answer)
    if body is None:
        raise ValidationFailedError("Write the correct answer.")

    kind: KnowledgeItemKind = TEXT_KINDS[request.scope]
    tags: list[KnowledgeTag] = (
        [HOURS_TAG] if request.scope is AnswerCorrectionScope.HOURS else []
    )
    item: KnowledgeItemDocument | None = (
        target
        if target is not None and target.kind in QUESTION_KINDS
        else find_matching_item(items, kind, title)
    )
    if item is None:
        return KnowledgeItemDocument(
            business_id=business.id,
            kind=kind,
            title=title,
            body=body,
            tags=tags,
            languages=[language],
            source=KnowledgeItemSource.OWNER,
            created_at=now,
            updated_at=now,
        ), True

    return item.model_copy(
        update={
            "kind": kind,
            "title": title,
            "body": body,
            "tags": list(dict.fromkeys([*item.tags, *tags])),
            "languages": list(dict.fromkeys([*item.languages, language])),
            "is_active": True,
            "updated_at": now,
        }
    ), False


def corrected_price_item(
    business: BusinessDocument,
    niche: NicheTemplate,
    request: AnswerCorrectionRequest,
    target: KnowledgeItemDocument | None,
    language: LanguageTag,
    now: Microseconds,
) -> tuple[KnowledgeItemDocument, bool]:
    """
    The offer with its new price, or a new offer named `question` of the
    niche's first offer kind.

    Raises:
        ValidationFailedError: no price, no offer to price, or a niche
            without a price list.
        NotFoundError: the named offer is not this business's.
    """

    if request.price_minor is None:
        raise ValidationFailedError("Enter the correct price.")

    if target is not None and target.kind in QUESTION_KINDS:
        raise ValidationFailedError("Choose an item of the price list to correct.")

    if target is not None:
        return target.model_copy(
            update={
                "price_minor": request.price_minor,
                "currency_code": business.currency_code,
                "is_active": True,
                "updated_at": now,
            }
        ), False

    offer_kinds: list[KnowledgeItemKind] = [
        kind for kind in niche.knowledge_kinds if kind not in QUESTION_KINDS
    ]
    if not offer_kinds:
        raise ValidationFailedError("This business keeps no price list.")

    if request.question is None:
        raise ValidationFailedError("Name the item whose price is wrong.")

    return KnowledgeItemDocument(
        business_id=business.id,
        kind=offer_kinds[0],
        title=check_title(KnowledgeTitle(request.question.strip())),
        body=check_body(request.correct_answer),
        price_minor=request.price_minor,
        currency_code=business.currency_code,
        languages=[language],
        source=KnowledgeItemSource.OWNER,
        created_at=now,
        updated_at=now,
    ), True


def requested_target(
    knowledge_item_repo: KnowledgeItemRepoContract,
    business_id: BusinessId,
    request: AnswerCorrectionRequest,
    corrected: KnowledgeItemDocument | None,
) -> KnowledgeItemDocument | None:
    """
    The item the owner chose, else the item an earlier correction of the
    same answer made when it fits the scope.

    Raises:
        NotFoundError: the chosen item is not this business's.
    """

    if request.knowledge_item_id is None:
        if corrected is not None and fits_scope(corrected, request.scope):
            return corrected

        return None

    chosen: KnowledgeItemDocument | None = knowledge_item_repo.get(
        business_id, request.knowledge_item_id
    )
    if chosen is None:
        raise NotFoundError(
            f"Knowledge item {request.knowledge_item_id} was not found."
        )

    return chosen
