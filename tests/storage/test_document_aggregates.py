"""Grouped counts of the document store: one answer in memory and on Postgres."""

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import (
    ConversationDocument,
    MessageDocument,
    ToolCallRecord,
)
from app.schemas.dto.storage_aggregates import (
    DocumentAggregation,
    DocumentFieldBuckets,
    DocumentGroupCount,
)
from app.schemas.dto.storage_queries import (
    DocumentFieldAmong,
    DocumentFieldExclusion,
    DocumentFieldMatch,
    DocumentFieldRange,
    DocumentFilter,
)
from app.schemas.exceptions.storage_errors import UndeclaredLookupFieldError
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    LlmToolResultJson,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import DocumentFieldText
from tests.storage.conftest import CollectionFactory
from tests.storage.test_document_lookups import message
from tests.storage.test_document_pages import conversation

pytestmark = pytest.mark.usefixtures("platform_scope")

BUSINESS = DocumentFieldPath("business_id")
CHANNEL = DocumentFieldPath("channel")
LANGUAGE = DocumentFieldPath("language")
IS_SANDBOX = DocumentFieldPath("is_sandbox")
CREATED_AT = DocumentFieldPath("created_at")
AUTHOR = DocumentFieldPath("author")
CONVERSATION = DocumentFieldPath("conversation_id")
COST = DocumentFieldPath("cost_micro_usd")
TOOL_ERRORS = DocumentFieldPath("tool_calls[].is_error")

type GroupRow = tuple[tuple[str | None, ...], int | None, int, int | None, int | None]


def text(value: str) -> DocumentFieldText:
    return DocumentFieldText(value)


def of_business(business_id: BusinessId) -> DocumentFieldMatch:
    return DocumentFieldMatch(field=BUSINESS, value=text(str(business_id)))


def rows(groups: list[DocumentGroupCount]) -> set[GroupRow]:
    return {
        (
            tuple(None if value is None else str(value) for value in group.values),
            None if group.bucket is None else int(group.bucket),
            int(group.count),
            None if group.total is None else int(group.total),
            None if group.latest is None else int(group.latest),
        )
        for group in groups
    }


def test_counts_group_by_fields_and_buckets(collections: CollectionFactory) -> None:
    conversations = collections(ConversationDocument, "conversations")
    business_id = BusinessId()
    stored = [
        conversation(business_id, 15, ChannelKind.TELEGRAM, language="ka"),
        conversation(business_id, 25, ChannelKind.TELEGRAM, language="ka"),
        conversation(business_id, 35, ChannelKind.TELEGRAM),
        conversation(business_id, 45, ChannelKind.WHATSAPP, language="en"),
        conversation(business_id, 55, ChannelKind.WHATSAPP, is_sandbox=True),
        conversation(business_id, 4, ChannelKind.WHATSAPP),
        conversation(BusinessId(), 25, ChannelKind.TELEGRAM),
    ]
    for document in stored:
        conversations.upsert(str(document.id), document)
    real = DocumentFilter(
        matches=(of_business(business_id),),
        excluding=(DocumentFieldExclusion(field=IS_SANDBOX, value=text("true")),),
        ranges=(DocumentFieldRange(field=CREATED_AT, upper=DocumentFieldInteger(45)),),
    )

    by_channel_and_language = conversations.count_by(
        DocumentAggregation(where=real, group_by=(CHANNEL, LANGUAGE))
    )
    by_day = conversations.count_by(
        DocumentAggregation(
            where=real,
            buckets=DocumentFieldBuckets(
                field=CREATED_AT,
                starts=(DocumentFieldInteger(10), DocumentFieldInteger(30)),
            ),
            latest_of=CREATED_AT,
        )
    )
    total = conversations.count_by(DocumentAggregation(where=real))
    nothing = conversations.count_by(
        DocumentAggregation(
            where=DocumentFilter(matches=(of_business(BusinessId()),)),
            latest_of=CREATED_AT,
        )
    )

    assert rows(by_channel_and_language) == {
        (("telegram", "ka"), None, 2, None, None),
        (("telegram", None), None, 1, None, None),
        (("whatsapp", "en"), None, 1, None, None),
        (("whatsapp", None), None, 1, None, None),
    }
    # Created at 10, 20, 30, 40 (and -1, before the first bucket).
    assert rows(by_day) == {((), 0, 2, None, 20), ((), 1, 2, None, 40)}
    assert rows(total) == {((), None, 5, None, None)}
    assert rows(nothing) == {((), None, 0, None, None)}


def test_totals_sum_an_integer_field_per_group(collections: CollectionFactory) -> None:
    messages = collections(MessageDocument, "messages")
    business_id = BusinessId()
    first, second = ConversationId(), ConversationId()
    stored = [
        message(first, 10, business_id=business_id),
        message(first, 20, business_id=business_id),
        message(second, 30, business_id=business_id),
        message(second, 99, business_id=business_id),
    ]
    for document, cost in zip(stored, (100, 250, 7, 1000), strict=True):
        document.cost_micro_usd = CostMicroUsd(cost)
        messages.upsert(str(document.id), document)

    spend = messages.count_by(
        DocumentAggregation(
            where=DocumentFilter(
                matches=(of_business(business_id),),
                ranges=(
                    DocumentFieldRange(
                        field=CREATED_AT, upper=DocumentFieldInteger(50)
                    ),
                ),
            ),
            group_by=(CONVERSATION,),
            total_of=COST,
        )
    )
    customer = messages.count_by(
        DocumentAggregation(
            where=DocumentFilter(
                matches=(
                    of_business(business_id),
                    DocumentFieldMatch(field=AUTHOR, value=text("customer")),
                ),
                among=(
                    DocumentFieldAmong(field=CONVERSATION, values=(text(str(first)),)),
                ),
            ),
            total_of=COST,
        )
    )

    assert rows(spend) == {
        ((str(first),), None, 2, 350, None),
        ((str(second),), None, 1, 7, None),
    }
    assert rows(customer) == {((), None, 2, 350, None)}


def test_list_field_matches_and_platform_wide_groups(
    collections: CollectionFactory,
) -> None:
    messages = collections(MessageDocument, "messages")
    first_business, second_business = BusinessId(), BusinessId()
    failed = ToolCallRecord(
        tool_name=AssistantToolName.CHECK_AVAILABILITY,
        input_json=LlmToolInputJson("{}"),
        result_json=LlmToolResultJson("{}"),
        is_error=True,
    )
    worked = failed.model_copy(update={"is_error": False})
    stored = [
        message(ConversationId(), 10, business_id=first_business),
        message(ConversationId(), 20, business_id=first_business),
        message(ConversationId(), 30, business_id=second_business),
        message(ConversationId(), 40, business_id=second_business),
    ]
    stored[0].tool_calls = [failed, worked]
    stored[1].tool_calls = [worked]
    stored[2].tool_calls = [failed]
    stored[3].tool_calls = [failed]
    stored[3].author = MessageAuthor.ASSISTANT
    for document in stored:
        messages.upsert(str(document.id), document)

    with_errors = messages.count_by(
        DocumentAggregation(
            where=DocumentFilter(
                matches=(DocumentFieldMatch(field=TOOL_ERRORS, value=text("true")),),
                ranges=(
                    DocumentFieldRange(field=CREATED_AT, lower=DocumentFieldInteger(5)),
                ),
            ),
            group_by=(BUSINESS,),
            latest_of=CREATED_AT,
        )
    )
    among_values = messages.count_by(
        DocumentAggregation(
            where=DocumentFilter(
                matches=(of_business(second_business),),
                among=(
                    DocumentFieldAmong(field=TOOL_ERRORS, values=(text("true"),)),
                    DocumentFieldAmong(
                        field=AUTHOR, values=(text("assistant"), text("staff"))
                    ),
                ),
            )
        )
    )

    assert rows(with_errors) == {
        ((str(first_business),), None, 1, None, 10),
        ((str(second_business),), None, 2, None, 40),
    }
    assert rows(among_values) == {((), None, 1, None, None)}


@pytest.mark.parametrize(
    "aggregation",
    [
        DocumentAggregation(group_by=(CREATED_AT,)),
        DocumentAggregation(group_by=(TOOL_ERRORS,)),
        DocumentAggregation(total_of=AUTHOR),
        DocumentAggregation(
            buckets=DocumentFieldBuckets(
                field=AUTHOR, starts=(DocumentFieldInteger(1),)
            )
        ),
        DocumentAggregation(
            where=DocumentFilter(
                matches=(DocumentFieldMatch(field=AUTHOR, value=text("customer")),)
            )
        ),
    ],
    ids=[
        "group by integer",
        "group by list",
        "total of text",
        "text buckets",
        "filter alone",
    ],
)
def test_aggregations_refuse_undeclared_fields(
    collections: CollectionFactory, aggregation: DocumentAggregation
) -> None:
    messages = collections(MessageDocument, "messages")
    with pytest.raises(UndeclaredLookupFieldError, match="lookup field"):
        messages.count_by(aggregation)


def test_buckets_check_their_starts() -> None:
    with pytest.raises(ValueError, match="at least one start"):
        DocumentFieldBuckets(field=CREATED_AT, starts=())
    with pytest.raises(ValueError, match="strictly ascend"):
        DocumentFieldBuckets(
            field=CREATED_AT,
            starts=(DocumentFieldInteger(2), DocumentFieldInteger(2)),
        )
