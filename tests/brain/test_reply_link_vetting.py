"""
The reply guard's readers of links and team notes: which links a reply has
and which of them the business, the platform or a well-known map or
payment service covers; which team notes a transcript showed the model and
which of them a reply quotes.
"""

import json

import pytest

from app.utilities.conversations.untrusted_text import wrap_team_note
from app.utilities.reply_guard.reply_links import (
    find_foreign_links,
    find_links,
    platform_link_hosts,
)
from app.utilities.reply_guard.team_note_quotes import (
    find_quoted_notes,
    find_transcript_notes,
)

FACTS: list[str] = ["Website: https://www.trattoria-da-mario.it/menu"]
PLATFORM_HOSTS: list[str] = platform_link_hosts(
    ["https://app.workshop.example", None, "not a url ::"]
)


def test_links_are_found_with_a_scheme_with_www_and_as_bare_domains() -> None:
    links = find_links(
        "Menu: https://www.Trattoria-da-Mario.it/menu. Or www.example.org, "
        "or trattoria-da-mario.it/prenota! Mail info@trattoria-da-mario.it"
    )

    assert [(link.text, link.host, link.path) for link in links] == [
        ("https://www.Trattoria-da-Mario.it/menu", "trattoria-da-mario.it", "/menu"),
        ("www.example.org", "example.org", ""),
        ("trattoria-da-mario.it/prenota", "trattoria-da-mario.it", "/prenota"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "We open at 12.30 and close at 23.00.",
        "See the menu.pdf we sent, e.g. the pasta.",
        "Write to info@trattoria-da-mario.it",
        "https://",
        "http://[::1",
    ],
)
def test_no_link_is_read_where_there_is_none(text: str) -> None:
    assert find_foreign_links(text, []) == []


@pytest.mark.parametrize(
    "link",
    [
        "https://trattoria-da-mario.it/prenota",
        "https://prenota.trattoria-da-mario.it",
        "https://app.workshop.example/r/AbC123",
        "https://maps.google.com/?q=Via+Roma+1",
        "https://www.google.com/maps/place/Trattoria",
        "https://buy.stripe.com/test_123",
        "https://paypal.me/trattoria",
    ],
)
def test_published_platform_and_well_known_links_pass(link: str) -> None:
    assert find_foreign_links(f"Here: {link}", FACTS, PLATFORM_HOSTS) == []


@pytest.mark.parametrize(
    "link",
    [
        "https://trattoria-mario-offerte.com/promo",
        "https://www.google.com/search?q=trattoria",
        "https://app.workshop.example.evil.com/r/1",
        "mario-sconti.it",
    ],
)
def test_other_links_are_foreign(link: str) -> None:
    assert find_foreign_links(f"See {link} now", FACTS, PLATFORM_HOSTS) == [link]


def test_the_platform_hosts_come_from_its_configured_addresses() -> None:
    assert PLATFORM_HOSTS == ["app.workshop.example"]


def test_notes_are_read_from_json_payloads_and_plain_text() -> None:
    note = "Prefers the quiet corner table near the fireplace"
    payload = json.dumps(
        {
            "role": "user",
            "content": [{"type": "text", "text": f"Notes: {wrap_team_note(note)}"}],
        },
        ensure_ascii=True,
    )

    notes = find_transcript_notes(
        [payload, f"plain {wrap_team_note('Pays by card')}", '{"no": "notes"}']
    )

    assert notes == [note, "Pays by card"]


def test_five_words_of_a_note_in_a_row_quote_it() -> None:
    note = "Prefers the quiet corner table near the fireplace"

    assert find_quoted_notes(
        "We kept the QUIET corner table, near the fireplace!", [note]
    ) == [note]
    assert find_quoted_notes("A quiet table near the fireplace?", [note]) == []
    assert find_quoted_notes("", [note]) == []
    assert find_quoted_notes("Pays by card, as always.", ["Pays by card"]) == []
