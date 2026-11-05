"""
The outbox delivers a request for feedback: free text inside the 24-hour
window, else the approved WhatsApp template with the business name (in
English when Meta has no translation), metered as a template; the request
notes the delivery, or fails with the platform's reason.
"""

from typing import Any

from typed_time_provider import Microseconds

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.feedback import FeedbackRequestStatus
from tests.feedback.feedback_setup import WHATSAPP_USER, FeedbackSetup

TEMPLATE_MISSING: dict[str, Any] = {
    "error": {"code": 132001, "message": "(#132001) Template name does not exist"}
}
SENT: dict[str, Any] = {"messages": [{"id": "wamid.feedback"}]}


def template_usage(setup: FeedbackSetup) -> int:
    return sum(
        int(event.quantity)
        for event in setup.testbed.usage_event_repo.list_by_business_between(
            setup.business.id,
            Microseconds(0),
            Microseconds(int(setup.testbed.clock.now_microseconds()) + 1),
        )
        if event.kind is UsageKind.WHATSAPP_TEMPLATE
    )


def test_inside_the_window_the_request_goes_as_text() -> None:
    setup = FeedbackSetup()
    contact = setup.add_customer()
    setup.customer_wrote(contact, ChannelKind.WHATSAPP, 2)
    setup.add_visit(contact)
    setup.run()

    setup.testbed.run_worker()

    [sent] = setup.whatsapp_sends()
    assert sent["type"] == "text"
    assert sent["to"] == WHATSAPP_USER
    assert "Café Rustaveli" in sent["text"]["body"]
    request = setup.only_request()
    assert request.status is FeedbackRequestStatus.SENT
    assert request.delivered_at == setup.testbed.clock.now_microseconds()
    assert template_usage(setup) == 0


def test_outside_the_window_the_template_carries_the_business_name() -> None:
    setup = FeedbackSetup()
    setup.add_visit(setup.add_customer(language="ka"))
    setup.run()

    setup.testbed.run_worker()

    [sent] = setup.whatsapp_sends()
    assert sent["type"] == "template"
    assert sent["template"] == {
        "name": "visit_feedback",
        "language": {"code": "ka"},
        "components": [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": "Café Rustaveli"}],
            }
        ],
    }
    assert setup.only_request().delivered_at is not None
    assert template_usage(setup) == 1


def test_a_template_without_the_translation_goes_in_english() -> None:
    setup = FeedbackSetup()
    setup.testbed.meta_transport.respond_in_turn(
        "POST", r"/messages$", [(404, TEMPLATE_MISSING), (200, SENT)]
    )
    setup.add_visit(setup.add_customer(language="ka"))
    setup.run()

    setup.testbed.run_worker()

    sends = setup.whatsapp_sends()
    assert [sent["template"]["language"]["code"] for sent in sends] == ["ka", "en"]
    assert setup.only_request().delivered_at is not None
    assert template_usage(setup) == 1


def test_a_refused_template_fails_the_request_without_a_handoff() -> None:
    setup = FeedbackSetup()
    setup.testbed.meta_transport.respond(
        "POST", r"/messages$", TEMPLATE_MISSING, status_code=404
    )
    setup.add_visit(setup.add_customer(language="ka"))
    setup.run()

    setup.testbed.run_worker()

    request = setup.only_request()
    assert request.status is FeedbackRequestStatus.FAILED
    assert request.last_error is not None
    assert "132001" in str(request.last_error)
    assert request.delivered_at is None
    assert setup.testbed.handoffs_to_human.commands == []
    assert template_usage(setup) == 0
