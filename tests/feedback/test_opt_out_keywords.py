"""STOP and START, as the whole message, in the customer's language."""

import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.feedback import CustomerSignalKind
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.channels.opt_out import (
    is_opted_out,
    normalize_command,
    read_messaging_preference,
    with_opt_out,
)


@pytest.mark.parametrize(
    "text",
    [
        "STOP",
        "stop",
        " Stop! ",
        "Stop.",
        "UNSUBSCRIBE",
        "opt-out",
        "СТОП",
        "Стоп",
        "отписаться",
        "სტოპ",
        "ՍՏՈՊ",
        "STOPP",
        "Arrêt",
        "PARAR",
        "dur",
        "עצור",
        "توقف",
        "退订",
        "«стоп»",
    ],
)
def test_stop_words_opt_out(text: str) -> None:
    assert read_messaging_preference(text) is CustomerSignalKind.OPT_OUT


@pytest.mark.parametrize("text", ["START", "start", "Старт", "სტარტი", "başla"])
def test_start_words_opt_back_in(text: str) -> None:
    assert read_messaging_preference(text) is CustomerSignalKind.OPT_IN


@pytest.mark.parametrize(
    "text",
    [
        "Stop the booking for tomorrow please",
        "cancel",
        "/start",
        "can you stop by at 5?",
        "",
        "   ",
        "stop " * 30,
    ],
)
def test_sentences_and_commands_are_not_keywords(text: str) -> None:
    assert read_messaging_preference(text) is None


def test_normalization_drops_marks_and_dashes() -> None:
    assert normalize_command("  OPT—OUT!!  ") == "opt out"
    assert normalize_command("Stop️") == "stop"


def test_an_opt_out_in_any_channel_counts() -> None:
    contact = ContactDocument(business_id=BusinessId())

    assert is_opted_out(contact) is False
    assert is_opted_out(None) is False

    contact.opted_out_channels = with_opt_out(contact, ChannelKind.TELEGRAM)
    again = with_opt_out(contact, ChannelKind.TELEGRAM)

    assert is_opted_out(contact) is True
    assert again == [ChannelKind.TELEGRAM]
    assert with_opt_out(contact, ChannelKind.WHATSAPP) == [
        ChannelKind.TELEGRAM,
        ChannelKind.WHATSAPP,
    ]
