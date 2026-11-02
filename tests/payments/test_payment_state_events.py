"""
Payment state changes are structured log lines (`app.payments`): the
order opened and every provider notification applied, with ids, the
provider and the statuses before and after; never card data.
"""

import logging

import pytest

from app.use_cases.billing.payment_state_events import (
    PAYMENT_ORDER_OPENED,
    PAYMENT_STATE_CHANGED,
)
from tests.billing.paid_world import build_trial, checkout, payment_order

CARD_FIELDS: frozenset[str] = frozenset(
    {"masked_card", "card_type", "rectoken", "card", "last_digits", "brand"}
)


def payment_lines(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    return [
        getattr(record, "log_fields")
        for record in caplog.records
        if record.name == "app.payments"
    ]


def test_an_opened_order_and_its_approval_are_logged_without_card_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = build_trial()
    with caplog.at_level(logging.INFO, logger="app.payments"):
        session = checkout(world)
        order = payment_order(world, session)
        parameters = world.testbed.callback_parameters(order, "approved", payment_id=9)
        parameters["masked_card"] = "444455XXXXXX1111"
        world.testbed.deliver_flitt_callback(parameters)

    opened, changed = payment_lines(caplog)
    assert opened["payment_event"] == PAYMENT_ORDER_OPENED
    assert opened["payment_order_id"] == str(order.id)
    assert opened["status_after"] == "created"
    assert changed["payment_event"] == PAYMENT_STATE_CHANGED
    assert changed["payment_order_id"] == str(order.id)
    assert changed["business_id"] == str(world.business.id)
    assert (changed["status_before"], changed["status_after"]) == (
        "created",
        "approved",
    )
    assert changed["notified_status"] == "approved"
    assert changed["outcome"] == "applied"
    for fields in (opened, changed):
        assert not CARD_FIELDS & set(fields)
        assert "1111" not in " ".join(str(value) for value in fields.values())
