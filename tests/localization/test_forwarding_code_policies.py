"""
Rules every country's forwarding guide follows: no code that forwards every
call (staff answer first), a carrier choice only where the carriers take
different codes (the United States), and a carrier with codes of its own
explains them in a note that names it.
"""

import pytest

from app.registries.localization.call_forwarding_carriers import (
    CARRIER_GUIDES_BY_COUNTRY,
    COUNTRY_FORWARDING_TEXTS,
)
from app.registries.localization.call_forwarding_guide_registry import (
    CallForwardingGuideRegistry,
    has_standard_codes,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.localization.country_registry_helpers import REGISTRY

# Codes of forwarding every call, never listed: Verizon's *72, the GSM *21*,
# **21* and #21#, and the all-forwarding *002* and **002*.
EVERY_CALL_CODE_PREFIXES: tuple[str, ...] = (
    "*72",
    "*21",
    "**21",
    "#21",
    "*002*",
    "**002*",
)


def test_no_guide_of_any_country_has_a_code_that_forwards_every_call() -> None:
    registry = CallForwardingGuideRegistry()
    countries = {profile.country_code for profile in REGISTRY.list_all()}
    countries.update(CARRIER_GUIDES_BY_COUNTRY, COUNTRY_FORWARDING_TEXTS)
    templates: set[str] = set()
    for country_code in countries:
        guide = registry.get(country_code)
        templates.update(str(item.dial_code_template) for item in guide.code_templates)
        for carrier in guide.carriers:
            templates.update(str(t.dial_code_template) for t in carrier.code_templates)
            templates.update(
                str(t.dial_code_template) for t in carrier.star_code_templates
            )

    assert {"**61*{number}#", "*71{number}", "*73", "##004#"} <= templates
    assert sorted(t for t in templates if t.startswith(EVERY_CALL_CODE_PREFIXES)) == []


@pytest.mark.parametrize(
    ("code", "forwards_every_call"),
    [
        ("*72{number}", True),
        ("*21*{number}#", True),
        ("**21*{number}#", True),
        ("#21#", True),
        ("*002*{number}#", True),
        ("**002*{number}#", True),
        ("*71{number}", False),
        ("**61*{number}#", False),
        ("##002#", False),
        ("##004#", False),
    ],
)
def test_the_check_tells_every_call_codes_apart(
    code: str, forwards_every_call: bool
) -> None:
    assert code.startswith(EVERY_CALL_CODE_PREFIXES) is forwards_every_call


def test_only_the_united_states_needs_a_carrier_choice() -> None:
    registry = CallForwardingGuideRegistry()

    choosing = {
        str(profile.country_code)
        for profile in REGISTRY.list_all()
        if registry.get(profile.country_code).is_carrier_choice_needed
    }

    assert choosing == {"US"}


def test_a_carrier_with_codes_of_its_own_names_itself_in_its_note() -> None:
    # The unconfirmed note of a carrier's own codes does not name the
    # carrier, so the carrier's note must.
    english = LanguageTag("en")
    own_codes = [
        carrier
        for carriers in CARRIER_GUIDES_BY_COUNTRY.values()
        for carrier in carriers
        if not has_standard_codes(carrier)
    ]

    assert [str(carrier.carrier_name) for carrier in own_codes] == [
        "Verizon",
        "T-Mobile",
    ]
    for carrier in own_codes:
        assert carrier.notes is not None
        assert str(carrier.carrier_name) in carrier.notes.values[english]
