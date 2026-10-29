"""
Handoffs the platform creates itself: staff read them in their own
language (the stored summary in the owner language, notifications in each
contact's, and the code, quote and values for the cabinet).
"""

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import (
    HandoffReason,
    HandoffSummaryCode,
    HandoffUrgency,
)
from app.schemas.dto.handoffs import CodedHandoffSummary, HandoffCommand
from app.schemas.dto.operations.handoffs import HandoffListItem, ListHandoffsQuery
from app.schemas.typings.conversations.strings import UnverifiedReplyValue
from app.schemas.typings.handoffs.strings import HandoffQuotedText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from tests.operations.handoff_fixture import HandoffFixture

QUESTION: str = "Сколько стоит пломба?"
ENGLISH_SUMMARY: str = (
    "The assistant held back an answer with figures or statements that are not "
    f"in your business details (250 ₪, 19:30). The customer's message: “{QUESTION}”"
)
ITALIAN_SUMMARY: str = (
    "L'assistente non ha inviato una risposta con cifre o affermazioni che non "
    "risultano nei dati della tua attività (250 ₪, 19:30). "
    f"Il messaggio del cliente: “{QUESTION}”"
)


def hand_off_coded(fixture: HandoffFixture) -> None:
    fixture.world.handoff_to_human().run(
        HandoffCommand(
            business_id=fixture.business.id,
            conversation_id=fixture.conversation.id,
            contact_id=fixture.contact.id,
            reason=HandoffReason.UNVERIFIED_NUMBERS,
            summary=CodedHandoffSummary(
                code=HandoffSummaryCode.UNVERIFIED_VALUES,
                quoted_text=HandoffQuotedText(QUESTION),
                flagged_values=[
                    UnverifiedReplyValue("250 ₪"),
                    UnverifiedReplyValue("19:30"),
                ],
            ),
            urgency=HandoffUrgency.NORMAL,
            source_channel=ChannelKind.TELEGRAM,
            language=LanguageTag("ru"),
        )
    )


def only_item(fixture: HandoffFixture) -> HandoffListItem:
    page = fixture.world.list_handoffs().run(
        ListHandoffsQuery(business_id=fixture.business.id, actor_id=UserId())
    )
    [item] = page.items
    return item


def test_the_cabinet_gets_the_code_the_quote_and_the_values() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")

    hand_off_coded(fixture)

    item = only_item(fixture)
    assert item.summary_code is HandoffSummaryCode.UNVERIFIED_VALUES
    assert item.quoted_text == QUESTION
    assert item.flagged_values == ["250 ₪", "19:30"]
    # The owner writes in Hebrew, which the catalog lacks: the summary is
    # stored in English, with the values and the quote in their place.
    assert str(item.summary) == ENGLISH_SUMMARY


def test_the_stored_summary_is_written_in_the_staff_language() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    fixture.business.owner_language = LanguageTag("it")
    fixture.world.business_repo.save(fixture.business)

    hand_off_coded(fixture)

    assert str(only_item(fixture).summary) == ITALIAN_SUMMARY


def test_every_staff_contact_reads_it_in_their_own_language() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    nino, daniel, anna = fixture.business.manager_contacts
    fixture.business.manager_contacts = [
        nino.model_copy(update={"language": LanguageTag("it")}),
        daniel,
        anna,
    ]
    fixture.world.business_repo.save(fixture.business)

    hand_off_coded(fixture)

    texts = {
        str(contact.language): str(text)
        for contact, text in fixture.world.notifier.sent
    }
    assert ITALIAN_SUMMARY in texts["it"].splitlines()
    # Russian is not in the catalog: that contact reads the English summary.
    assert ENGLISH_SUMMARY in texts["ru"].splitlines()
    assert "The AI model" not in texts["ru"] + texts["it"]


def test_the_models_own_summary_is_kept_as_written() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")

    fixture.hand_off()

    item = only_item(fixture)
    assert item.summary_code is None
    assert item.quoted_text is None
    assert item.flagged_values == []
    assert str(item.summary) == "Tooth still hurts after the filling."
