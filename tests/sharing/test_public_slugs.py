"""Public chat addresses suggested from business names, and reserved words."""

import pytest

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.sharing.constrained_strings import BusinessPublicSlug
from app.utilities.sharing.public_slugs import (
    is_reserved_slug,
    shorten,
    spell_in_latin,
    suggest_slugs,
)

BUSINESS_ID = BusinessId("business_0b6c2f5e-1d1a-4c55-9a3e-2f1d5b7c9e01")


@pytest.mark.parametrize(
    ("name", "spelled"),
    [
        ("Café Batumi", "cafe-batumi"),
        ("Сакартвело", "sakartvelo"),
        ("Ресторан «Хинкали №1»", "restoran-khinkali-no1"),
        ("მწვანე ბოსტანი", "mtsvane-bostani"),
        ("ჭაჭა & ღვინო", "chacha-ghvino"),
        ("Աբովյան 12", "abovyan-12"),
        ("Straße & Söhne", "strasse-sohne"),
        ("Їжак і Ґава", "yizhak-i-gava"),
        ("Pizza Roma — Tbilisi!!", "pizza-roma-tbilisi"),
        ("  --  ", ""),
        ("שלום", ""),
    ],
)
def test_names_are_spelled_in_latin_letters(name: str, spelled: str) -> None:
    assert spell_in_latin(name) == spelled


def test_long_names_are_cut_after_a_whole_word() -> None:
    assert shorten("a-very-long-business-name", 12) == "a-very-long"
    assert shorten("abcdefghijklmnop", 8) == "abcdefgh"
    assert shorten("short", 8) == "short"


def test_suggestions_start_with_the_name_then_number_it() -> None:
    suggestions = [
        str(slug) for slug in suggest_slugs(BusinessName("Café Batumi"), BUSINESS_ID)
    ]

    assert suggestions[:3] == ["cafe-batumi", "cafe-batumi-2", "cafe-batumi-3"]
    assert suggestions[-3:] == [
        "chat-0b6c2f5e",
        "chat-0b6c2f5e1d1a4c55",
        "chat-0b6c2f5e1d1a4c559a3e2f1d5b7c9e01",
    ]


def test_a_name_without_latin_spelling_gets_the_id_based_address() -> None:
    suggestions = suggest_slugs(BusinessName("שלום"), BUSINESS_ID)

    assert [str(slug) for slug in suggestions][0] == "chat-0b6c2f5e"


def test_a_reserved_name_is_only_offered_numbered() -> None:
    suggestions = [
        str(slug) for slug in suggest_slugs(BusinessName("Privacy"), BUSINESS_ID)
    ]

    assert "privacy" not in suggestions
    assert suggestions[0] == "privacy-2"


def test_every_suggestion_is_a_valid_address() -> None:
    long_name = BusinessName("The Grand Old Georgian Wine Cellar and Supra Hall")

    for slug in suggest_slugs(long_name, BUSINESS_ID):
        assert BusinessPublicSlug(str(slug)) == slug
        assert len(str(slug)) <= 40


@pytest.mark.parametrize(
    ("slug", "is_reserved"),
    [
        ("privacy", True),
        ("api", True),
        ("chat-0b6c2f5e", True),
        ("chat-0b6c2f5e1d1a4c55", True),
        ("chat-noir", False),
        ("cafe-batumi", False),
    ],
)
def test_platform_words_and_id_addresses_are_reserved(
    slug: str, is_reserved: bool
) -> None:
    assert is_reserved_slug(BusinessPublicSlug(slug)) is is_reserved


@pytest.mark.parametrize(
    "slug", ["ab", "Cafe", "cafe--batumi", "-cafe", "cafe-", "café", "a" * 41]
)
def test_malformed_addresses_are_refused(slug: str) -> None:
    with pytest.raises(ValueError):
        BusinessPublicSlug(slug)
