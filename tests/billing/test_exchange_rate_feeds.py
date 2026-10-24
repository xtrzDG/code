"""The NBG and ECB rate feeds, read from fixture files through a fake fetcher."""

import json

import pytest

from app.clients.ecb.ecb_rates_client import ECB_RATES_URL, parse_ecb_rates
from app.clients.nbg.nbg_rates_client import NBG_RATES_URL, parse_nbg_rates
from app.schemas.constants.billing import ExchangeRateSource
from app.schemas.dto.billing_exchange_rates import ExchangeRateSheet
from app.schemas.exceptions.exchange_rate_errors import ExchangeRateFeedError
from tests.billing.rate_feed_fakes import (
    ECB_FIXTURE,
    NBG_FIXTURE,
    fixture_fetcher,
    fixture_rate_clients,
)


def rates_of(sheet: ExchangeRateSheet) -> dict[str, str]:
    return {
        f"{rate.base_currency_code}/{rate.quote_currency_code}": str(rate.rate)
        for rate in sheet.rates
    }


def test_the_nbg_sheet_is_lari_per_one_unit_of_each_currency() -> None:
    sheet = parse_nbg_rates(NBG_FIXTURE)

    assert sheet.source is ExchangeRateSource.NBG
    assert str(sheet.rate_date) == "2026-10-03"
    assert rates_of(sheet) == {
        "AMD/GEL": "0.006884",
        "AZN/GEL": "1.5321",
        "EUR/GEL": "2.9563",
        "GBP/GEL": "3.3932",
        "JPY/GEL": "0.017584",
        "KZT/GEL": "0.005012",
        "TRY/GEL": "0.06237",
        "UAH/GEL": "0.06302",
        "USD/GEL": "2.6045",
    }
    assert not any(rate.is_derived for rate in sheet.rates)


def test_the_ecb_sheet_is_units_of_each_currency_per_euro() -> None:
    sheet = parse_ecb_rates(ECB_FIXTURE)

    assert sheet.source is ExchangeRateSource.ECB
    assert str(sheet.rate_date) == "2026-10-02"
    assert rates_of(sheet)["EUR/USD"] == "1.1351"
    assert rates_of(sheet)["EUR/GBP"] == "0.87123"
    assert rates_of(sheet)["EUR/ILS"] == "4.219"
    assert len(sheet.rates) == 8


def test_the_clients_read_through_the_guarded_fetcher_with_limits() -> None:
    fetcher = fixture_fetcher()
    lari, euro = fixture_rate_clients(fetcher)

    assert len(lari.fetch_latest().rates) == 9
    assert len(euro.fetch_latest().rates) == 8
    assert [str(request.url) for request in fetcher.requests] == [
        str(NBG_RATES_URL),
        str(ECB_RATES_URL),
    ]
    assert all(int(request.max_bytes) == 512 * 1024 for request in fetcher.requests)
    assert {str(media) for media in fetcher.requests[1].accepted_media_types} == {
        "text/xml",
        "application/xml",
    }


def test_an_unreachable_feed_is_a_feed_error() -> None:
    lari, euro = fixture_rate_clients(fixture_fetcher(nbg=None, ecb=None))

    with pytest.raises(ExchangeRateFeedError):
        lari.fetch_latest()
    with pytest.raises(ExchangeRateFeedError):
        euro.fetch_latest()


@pytest.mark.parametrize(
    "body",
    [
        b"<html>maintenance</html>",
        b"[]",
        json.dumps([{"date": "soon", "currencies": []}]).encode(),
        # A day with two currencies is a broken feed, not a quiet day.
        json.dumps(
            [
                {
                    "date": "2026-10-03T00:00:00.000Z",
                    "currencies": [
                        {"code": "USD", "quantity": 1, "rateFormated": "2.6045"},
                        {"code": "EUR", "quantity": 1, "rateFormated": "2.9563"},
                    ],
                }
            ]
        ).encode(),
    ],
)
def test_a_broken_nbg_feed_is_refused(body: bytes) -> None:
    with pytest.raises(ExchangeRateFeedError):
        parse_nbg_rates(body)


def test_odd_nbg_entries_are_skipped_and_numbers_are_read_exactly() -> None:
    currencies: list[dict[str, object]] = [
        {"code": code, "quantity": 1, "rateFormated": rate}
        for code, rate in (
            ("USD", "2.6045"),
            ("EUR", "2.9563"),
            ("GBP", "3.3932"),
            ("AZN", "1.5321"),
        )
    ]
    odd: list[dict[str, object]] = [
        {"code": "CHF", "quantity": 1, "rate": 3.0712},
        {"code": "GEL", "quantity": 1, "rateFormated": "1"},
        {"code": "usd", "quantity": 1, "rateFormated": "2.6"},
        {"code": "XAU", "quantity": 1, "rateFormated": "-5"},
        {"code": "BYN", "quantity": True, "rateFormated": "0.8"},
        {"code": "RUB", "quantity": 100, "rateFormated": "n/a"},
    ]
    sheet = parse_nbg_rates(
        json.dumps({"date": "2026-10-03", "currencies": currencies + odd}).encode()
    )

    assert rates_of(sheet) == {
        "USD/GEL": "2.6045",
        "EUR/GEL": "2.9563",
        "GBP/GEL": "3.3932",
        "AZN/GEL": "1.5321",
        "CHF/GEL": "3.0712",
        # A quantity that is not a count is one unit.
        "BYN/GEL": "0.8",
    }


@pytest.mark.parametrize(
    "body",
    [
        b"not xml at all",
        ECB_FIXTURE.replace(b"time='2026-10-02'", b"time='yesterday'"),
        b"<Cube time='2026-10-02'><Cube currency='USD' rate='1.1351'/></Cube>",
    ],
)
def test_a_broken_ecb_feed_is_refused(body: bytes) -> None:
    with pytest.raises(ExchangeRateFeedError):
        parse_ecb_rates(body)


def test_ecb_entries_that_are_not_rates_are_skipped() -> None:
    body: bytes = ECB_FIXTURE.replace(
        b"<Cube currency='INR' rate='96.4410'/>",
        b"<Cube currency='INR' rate='96.4410'/>"
        b"<Cube currency='XXX' rate='0'/>"
        b"<Cube currency='EUR' rate='1'/>"
        b"<Cube currency='abc' rate='2'/>"
        b"<!DOCTYPE x [<!ENTITY e SYSTEM 'file:///etc/passwd'>]>",
    )

    sheet = parse_ecb_rates(body)

    assert len(sheet.rates) == 8
    assert "EUR/XXX" not in rates_of(sheet)
