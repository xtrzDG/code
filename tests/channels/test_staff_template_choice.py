"""Which WhatsApp template carries a staff reply: one per language."""

import pytest

from app.adapters.storage.channel_upgrades import upgrade_channels_from_v3
from app.adapters.storage.document_upgrades import upcasters_of, upgrade_stored_json
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.channels import ChannelDocument, WhatsAppStaffTemplate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.storage.constrained_integers import (
    DocumentSchemaVersionNumber,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.channels.staff_templates import (
    channel_staff_templates,
    choose_staff_template,
    fallback_staff_template,
)


def template(language: str, name: str = "staff_reply") -> WhatsAppStaffTemplate:
    return WhatsAppStaffTemplate(
        name=WhatsAppTemplateName(name),
        language_code=WhatsAppTemplateLanguageCode(language),
    )


RUSSIAN, HEBREW, ARABIC = template("ru"), template("he", "staff_he"), template("ar")
GEORGIAN = template("ka")
TEMPLATES: list[WhatsAppStaffTemplate] = [GEORGIAN, RUSSIAN, HEBREW, ARABIC]


def choose(
    templates: list[WhatsAppStaffTemplate],
    conversation: str | None,
    default: str = "ka",
) -> WhatsAppStaffTemplate | None:
    return choose_staff_template(
        templates,
        None if conversation is None else LanguageTag(conversation),
        LanguageTag(default),
    )


@pytest.mark.parametrize(
    ("conversation", "expected"),
    [("he", HEBREW), ("ar", ARABIC), ("ru", RUSSIAN), ("ka", GEORGIAN)],
)
def test_a_reply_takes_the_template_of_the_conversation_language(
    conversation: str, expected: WhatsAppStaffTemplate
) -> None:
    assert choose(TEMPLATES, conversation) == expected


def test_a_language_without_a_template_takes_the_business_default() -> None:
    assert choose(TEMPLATES, "fr") == GEORGIAN
    assert choose(TEMPLATES, None) == GEORGIAN
    assert choose([RUSSIAN, HEBREW], "fr", default="he") == HEBREW


def test_without_either_language_the_first_template_still_carries_it() -> None:
    # A reply that could go out before templates had languages still can.
    assert choose([RUSSIAN, ARABIC], "he", default="ka") == RUSSIAN
    assert choose([], "he") is None


def test_regional_codes_match_exactly_first_then_by_base_language() -> None:
    american, british = template("en_US"), template("en_GB")
    brazilian, portuguese = template("pt_BR"), template("pt")

    assert choose([american, british], "en-GB") == british
    assert choose([american, british], "en") == american
    assert choose([portuguese, brazilian], "pt-BR") == brazilian
    assert choose([brazilian], "pt") == brazilian


def test_the_single_template_the_previous_release_reads() -> None:
    assert fallback_staff_template(TEMPLATES, LanguageTag("ru")) == RUSSIAN
    assert fallback_staff_template([HEBREW, ARABIC], LanguageTag("ka")) == HEBREW
    assert fallback_staff_template([], LanguageTag("ka")) is None


def test_a_channel_saved_with_only_the_single_template_still_has_it() -> None:
    legacy = ChannelDocument(
        business_id=BusinessId(),
        kind=ChannelKind.WHATSAPP,
        whatsapp_staff_template=RUSSIAN,
    )
    current = ChannelDocument(
        business_id=BusinessId(),
        kind=ChannelKind.WHATSAPP,
        whatsapp_staff_template=GEORGIAN,
        whatsapp_staff_templates=[GEORGIAN, HEBREW],
    )
    empty = ChannelDocument(business_id=BusinessId(), kind=ChannelKind.WHATSAPP)

    assert channel_staff_templates(legacy) == [RUSSIAN]
    assert channel_staff_templates(current) == [GEORGIAN, HEBREW]
    assert channel_staff_templates(empty) == []


def test_a_version_3_channel_reads_its_template_as_a_one_template_list() -> None:
    stored: dict[str, object] = {
        "schema_version": "3",
        "kind": "whatsapp",
        "whatsapp_staff_template": {"name": "staff_reply", "language_code": "ru"},
    }

    upgraded = upgrade_stored_json(
        stored,
        upcasters_of(DocumentCollectionName("channels")),
        DocumentSchemaVersionNumber(4),
    )

    assert upgraded["whatsapp_staff_templates"] == [
        {"name": "staff_reply", "language_code": "ru"}
    ]
    assert upgraded["whatsapp_staff_template"] == stored["whatsapp_staff_template"]
    assert upgraded["schema_version"] == "4"
    assert "whatsapp_staff_templates" not in stored


@pytest.mark.parametrize(
    "stored",
    [
        {"kind": "telegram"},
        {"kind": "whatsapp", "whatsapp_staff_template": None},
        {
            "kind": "whatsapp",
            "whatsapp_staff_template": {"name": "a", "language_code": "ru"},
            "whatsapp_staff_templates": [{"name": "b", "language_code": "ka"}],
        },
    ],
)
def test_the_upcaster_leaves_channels_without_a_single_template_alone(
    stored: dict[str, object],
) -> None:
    assert upgrade_channels_from_v3(stored) is stored
