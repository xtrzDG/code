"""Texts for customers: confirmations, policies, handoff replies and fallbacks."""

from datetime import date

import pytest

from app.schemas.constants.bookings import (
    BookingUnit,
)
from app.schemas.dto.operations.message_texts import (
    HandoffCustomerMessageInput,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
)
from app.transformers.notifications.booking_confirmation_transformer import (
    TIME_SLOT_CONFIRMATION,
    BookingConfirmationTransformer,
)
from app.transformers.notifications.cancellation_confirmation_transformer import (
    CancellationConfirmationTransformer,
)
from app.transformers.notifications.handoff_customer_message_transformer import (
    HandoffCustomerMessageTransformer,
)
from app.transformers.notifications.reschedule_confirmation_transformer import (
    RescheduleConfirmationTransformer,
)
from app.utilities.scheduling.localized_formatting import (
    FIRST_STRONG_ISOLATE,
    choose_template_language,
    find_locale,
    is_right_to_left,
)
from tests.operations.message_text_helpers import (
    CUSTOMER_LANGUAGES,
    RESOLVER,
    booking_view,
    full_date,
    message_input,
)


@pytest.mark.parametrize("language", CUSTOMER_LANGUAGES)
def test_booking_confirmation_repeats_date_time_name_and_party(language: str) -> None:
    text = str(
        BookingConfirmationTransformer(RESOLVER).transform(message_input(language))
    )

    assert full_date(date(2026, 10, 6), language) in text
    for value in ("19:30", "Nino Kapanadze", "Salobie Bia", "5"):
        assert value in text

    assert "{" not in text
    assert (FIRST_STRONG_ISOLATE in text) is is_right_to_left(LanguageTag(language))


@pytest.mark.parametrize("language", CUSTOMER_LANGUAGES)
def test_stay_confirmation_has_check_in_and_check_out(language: str) -> None:
    stay = booking_view(
        day="2026-10-12", time="14:00", end_day="2026-10-15", end_time="12:00"
    )

    text = str(
        BookingConfirmationTransformer(RESOLVER).transform(
            message_input(language, stay, BookingUnit.NIGHT)
        )
    )

    assert full_date(date(2026, 10, 12), language) in text
    assert full_date(date(2026, 10, 15), language) in text
    assert "14:00" in text and "12:00" in text and "{" not in text


@pytest.mark.parametrize("language", CUSTOMER_LANGUAGES)
def test_cancellation_and_reschedule_quote_the_policy(language: str) -> None:
    policy = "Free cancellation up to 2 hours before."
    cancelled = str(
        CancellationConfirmationTransformer(RESOLVER).transform(
            message_input(language, policy=policy)
        )
    )
    moved = str(
        RescheduleConfirmationTransformer(RESOLVER).transform(
            message_input(language, policy=policy)
        )
    )
    without_policy = str(
        CancellationConfirmationTransformer(RESOLVER).transform(message_input(language))
    )

    for text in (cancelled, moved):
        assert full_date(date(2026, 10, 6), language) in text
        assert "19:30" in text and policy in text and "{" not in text
        assert len(text.splitlines()) == 2

    assert "Nino Kapanadze" in moved
    assert len(without_policy.splitlines()) == 1


@pytest.mark.parametrize("language", CUSTOMER_LANGUAGES)
def test_handoff_customer_message_in_and_out_of_hours(language: str) -> None:
    transformer = HandoffCustomerMessageTransformer(RESOLVER)

    soon = str(
        transformer.transform(
            HandoffCustomerMessageInput(language=LanguageTag(language))
        )
    )
    later = str(
        transformer.transform(
            HandoffCustomerMessageInput(
                language=LanguageTag(language),
                reopens_on=LocalDate("2026-10-11"),
                reopens_at=LocalTimeOfDay("09:00"),
            )
        )
    )

    assert "{" not in soon and "09:00" not in soon
    assert full_date(date(2026, 10, 11), language) in later
    assert "09:00" in later
    assert soon != later


def test_fallbacks_regional_tags_and_unknown_locales() -> None:
    transformer = BookingConfirmationTransformer(RESOLVER)

    swiss_german = str(transformer.transform(message_input("de-CH")))
    brazilian = str(transformer.transform(message_input("pt-BR")))
    klingon = str(transformer.transform(message_input("tlh")))

    assert swiss_german.startswith("Ihre Reservierung bei Salobie Bia")
    assert brazilian.startswith("Your booking at Salobie Bia")
    assert "Tuesday, October 6, 2026" in brazilian
    assert "Tuesday, October 6, 2026" in klingon
    assert str(find_locale(LanguageTag("tlh"))) == "en"


def test_template_language_choice() -> None:
    assert choose_template_language(TIME_SLOT_CONFIRMATION, LanguageTag("ka")) == "ka"
    assert (
        choose_template_language(TIME_SLOT_CONFIRMATION, LanguageTag("uk-UA")) == "uk"
    )
    assert choose_template_language(TIME_SLOT_CONFIRMATION, LanguageTag("ja")) == "en"
