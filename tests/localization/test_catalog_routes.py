"""Catalog routes: countries, country profiles, languages and plan quotes."""

import pytest
from fastapi.testclient import TestClient

from tests.localization.catalog_routes_client import read_json


def test_countries_are_listed_in_the_requested_language(client: TestClient) -> None:
    response = client.get("/v1/catalog/countries", params={"language": "ka"})

    assert response.status_code == 200
    body = read_json(response)
    assert body["display_language"] == "ka"
    assert len(body["countries"]) >= 200
    georgia = next(c for c in body["countries"] if c["country_code"] == "GE")
    assert georgia["display_name"] == "საქართველო"
    assert georgia["calling_code"] == 995
    assert georgia["onboarding_status"] == "pilot"


def test_language_defaults_to_english_and_is_normalized(client: TestClient) -> None:
    default_response = client.get("/v1/catalog/countries")
    normalized_response = client.get(
        "/v1/catalog/countries", params={"language": "PT_br"}
    )

    assert read_json(default_response)["display_language"] == "en"
    assert read_json(normalized_response)["display_language"] == "pt-BR"


@pytest.mark.parametrize("language", ["english", "xx", "en-US-x-private"])
def test_bad_language_is_a_validation_error(client: TestClient, language: str) -> None:
    response = client.get("/v1/catalog/countries", params={"language": language})

    assert response.status_code == 422
    assert read_json(response)["error"] == "validation_failed"


def test_country_profile_route_accepts_lowercase_codes(client: TestClient) -> None:
    response = client.get("/v1/catalog/countries/ge", params={"language": "ru"})

    assert response.status_code == 200
    body = read_json(response)
    assert body["display_name"] == "Грузия"
    assert body["profile"]["currency_code"] == "GEL"
    assert body["profile"]["default_customer_languages"] == ["ka", "ru", "en"]
    assert body["profile"]["on_request_customer_languages"] == ["tr", "he", "ar", "hy"]
    assert body["default_timezone"]["display_name"] == "Asia/Tbilisi (UTC+04:00)"
    hebrew = next(
        option
        for option in body["on_request_customer_languages"]
        if option["tag"] == "he"
    )
    assert hebrew["direction"] == "rtl"
    assert hebrew["native_name"] == "עברית"


@pytest.mark.parametrize("country_code", ["ZZ", "GEO", "1"])
def test_unknown_country_is_a_validation_error(
    client: TestClient, country_code: str
) -> None:
    response = client.get(f"/v1/catalog/countries/{country_code}")

    assert response.status_code == 422


def test_languages_route_lists_right_to_left_languages(client: TestClient) -> None:
    response = client.get("/v1/catalog/languages", params={"language": "he"})

    assert response.status_code == 200
    by_tag = {item["profile"]["tag"]: item for item in read_json(response)["languages"]}
    assert by_tag["ar"]["profile"]["direction"] == "rtl"
    assert by_tag["ka"]["profile"]["voice_support"] == "needs_pilot_check"
    assert by_tag["he"]["display_name"] == "עברית"


def test_plans_route_quotes_lari_for_georgia_and_estimated_dollars_for_the_usa(
    client: TestClient,
) -> None:
    georgia = read_json(
        client.get("/v1/catalog/plans", params={"country_code": "GE", "language": "ru"})
    )
    usa = read_json(client.get("/v1/catalog/plans", params={"country_code": "us"}))

    voice = next(q for q in georgia["quotes"] if q["plan_key"] == "voice_and_chat")
    assert voice["name"] == "Голос + чат"
    assert voice["local_monthly_price"]["money"] == {
        "amount_minor": 51700,
        "currency_code": "GEL",
    }
    assert voice["local_monthly_price"]["is_estimated"] is False
    assert georgia["exchange_rate"]["rate"] == 2.9552
    assert georgia["exchange_rate"]["rate_value"] == "2.9552"
    assert usa["local_currency_code"] == "USD"
    assert all(quote["local_monthly_price"]["is_estimated"] for quote in usa["quotes"])
    assert usa["exchange_rate"]["rate_date"] == "2026-10-01"
    assert usa["exchange_rate"]["source"] == "Platform planning rate"


def test_plans_route_requires_a_country(client: TestClient) -> None:
    assert client.get("/v1/catalog/plans").status_code == 422


def test_plans_route_prices_both_setup_options(client: TestClient) -> None:
    georgia = read_json(
        client.get("/v1/catalog/plans", params={"country_code": "GE", "language": "en"})
    )

    chat = next(q for q in georgia["quotes"] if q["plan_key"] == "chat")
    options = {row["option"]: row for row in chat["setup_options"]}
    assert options["self_serve"]["fee"]["money"]["amount_minor"] == 0
    assert options["self_serve"]["local_fee"]["money"] == {
        "amount_minor": 0,
        "currency_code": "GEL",
    }
    assert options["done_for_you"]["fee"]["money"] == {
        "amount_minor": 15000,
        "currency_code": "EUR",
    }
    assert options["done_for_you"]["local_fee"]["money"]["amount_minor"] == 44300
    assert chat["setup_fee"]["money"]["amount_minor"] == 15000
