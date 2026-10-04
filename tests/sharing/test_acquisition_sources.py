"""Reading where a customer came from out of what their channel carried."""

import pytest

from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.sharing.constrained_strings import ShareSourceTag
from app.utilities.sharing.acquisition_sources import (
    called_number_source,
    greeting_with_code,
    normalize_source,
    read_greeting_code,
    read_referral_source,
    read_start_payload,
    start_parameter,
)
from app.utilities.sharing.share_greetings import greeting_in


class TestNormalizing:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("qr", "qr"),
            ("  QR Tables ", "qr-tables"),
            ("instagram_bio", "instagram_bio"),
            ("flyer #2 (Batumi)", "flyer-2-batumi"),
            ("--qr--", "qr"),
            ("x" * 40, "x" * 32),
            ("Тбилиси qr", "qr"),
        ],
    )
    def test_any_text_becomes_a_tag(self, text: str, expected: str) -> None:
        assert normalize_source(text) == expected

    @pytest.mark.parametrize("text", [None, "", "   ", "!!!", "Тбилиси"])
    def test_nothing_readable_is_no_source(self, text: str | None) -> None:
        assert normalize_source(text) is None


class TestTelegramStart:
    def test_the_tag_of_a_start_link_is_read_and_left_out_of_the_text(self) -> None:
        assert read_start_payload("/start src_qr-tables") == ("qr-tables", "/start")
        assert read_start_payload("/start@cafe_bot src_qr") == ("qr", "/start@cafe_bot")

    @pytest.mark.parametrize(
        "text",
        ["/start", "/start promo42", "Hello /start src_qr", "start src_qr", ""],
    )
    def test_other_messages_stay_as_they_are(self, text: str) -> None:
        assert read_start_payload(text) == (None, text)

    def test_the_link_parameter_round_trips(self) -> None:
        parameter = start_parameter(ShareSourceTag("qr"))

        assert read_start_payload(f"/start {parameter}") == ("qr", "/start")


class TestWhatsAppGreetingCode:
    def test_the_code_after_the_greeting_is_read_and_removed(self) -> None:
        text = greeting_with_code(greeting_in(LanguageTag("ru")), ShareSourceTag("qr"))

        assert text == "Здравствуйте! (#qr)"
        assert read_greeting_code(text) == ("qr", "Здравствуйте!")
        assert read_greeting_code("Hi! (#QR-Tables)  ") == ("qr-tables", "Hi!")

    def test_a_message_that_is_only_the_code_keeps_its_text(self) -> None:
        assert read_greeting_code("(#qr)") == ("qr", "(#qr)")

    @pytest.mark.parametrize(
        "text",
        ["Table for 2 (#)", "Room #12 please", "(#qr) is in the middle", "Hello"],
    )
    def test_other_texts_carry_no_code(self, text: str) -> None:
        assert read_greeting_code(text) == (None, text)

    def test_greetings_fall_back_to_english(self) -> None:
        assert greeting_in(LanguageTag("ka-GE")) == "გამარჯობა!"
        assert greeting_in(LanguageTag("sw")) == "Hello!"
        assert greeting_in(None) == "Hello!"


class TestMetaReferral:
    def test_the_ref_of_a_link_wins(self) -> None:
        referral = {"ref": "Instagram Bio", "source": "SHORTLINK", "ad_id": "42"}

        assert read_referral_source(referral) == "instagram-bio"

    def test_an_ad_is_named_by_its_id(self) -> None:
        assert read_referral_source({"source": "ADS", "ad_id": 6045246247433}) == (
            "ad-6045246247433"
        )
        # WhatsApp's click-to-chat ads.
        whatsapp_ad = {"source_type": "ad", "source_id": "120208", "ctwa_clid": "x"}
        assert read_referral_source(whatsapp_ad) == "ad-120208"
        assert read_referral_source({"source": "ADS"}) == "ad"

    def test_anything_else_is_no_source(self) -> None:
        assert read_referral_source(None) is None
        assert read_referral_source({"source": "SHORTLINK"}) is None
        assert read_referral_source({"source_type": "post", "source_id": "1"}) is None


class TestCalledNumber:
    def test_the_line_dialled_is_the_source(self) -> None:
        assert called_number_source(E164PhoneNumber("+995322000111")) == (
            "tel-995322000111"
        )
        assert called_number_source(None) is None
