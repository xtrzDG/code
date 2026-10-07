"""
An endpoint switched off on its own is news for the business: one staff
alert per switch-off on every staff contact and the owners' devices, with
a link to Settings → Integrations, an audit entry without an actor and a
live event for the open cabinets. A retried attempt never repeats it; an
endpoint switched on and failing again is announced again.
"""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.business_repositories import BusinessRepository
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.integrations import (
    WebhookDeliveryProblem,
    WebhookEndpointOrigin,
    WebhookEndpointStatus,
)
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.notifications.constrained_strings import StaffLinkToken
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from tests.integrations.webhook_notice_world import (
    FAILURES_BEFORE_DISABLE,
    NoticeWorld,
)
from tests.live_events.recording_event_publisher import PublishedLiveEvent
from tests.notifications.staff_alert_fakes import TEST_ENCRYPTION_KEY

CONTACTS: int = 3


def test_the_switch_off_is_announced_once_on_every_contact() -> None:
    world = NoticeWorld()
    endpoint = world.add_endpoint(label="CRM")

    world.fail(endpoint, times=FAILURES_BEFORE_DISABLE - 1)
    before = list(world.alerts.notifier.sent)
    world.fail(endpoint)
    stored = world.stored(endpoint)

    assert before == []
    assert stored.status is WebhookEndpointStatus.DISABLED
    messages = {
        contact.channel: str(text) for contact, text in world.alerts.notifier.sent
    }
    assert set(messages) == {
        ManagerContactChannel.TELEGRAM,
        ManagerContactChannel.EMAIL,
        ManagerContactChannel.SMS,
    }
    english = messages[ManagerContactChannel.EMAIL]
    assert "A webhook was switched off · Salobie Bia" in english
    assert "The address CRM gets no more events after 3 failed attempts" in english
    assert "ვებჰუკი გამოირთო" in messages[ManagerContactChannel.TELEGRAM]
    assert "Вебхук отключён" in messages[ManagerContactChannel.SMS]
    assert len(set(world.subjects())) == 1


def test_the_audit_log_and_the_open_cabinets_hear_of_it() -> None:
    world = NoticeWorld()
    endpoint = world.add_endpoint()

    world.fail(endpoint, times=FAILURES_BEFORE_DISABLE)

    [entry] = world.audit.list_by_business(world.business.id)
    assert entry.action is AuditAction.UPDATE
    assert str(entry.entity) == "webhook_endpoint"
    assert str(entry.entity_id) == str(endpoint.id)
    assert entry.actor_id is None
    assert world.live.events == [
        PublishedLiveEvent(
            world.business.id, LiveEventKind.WEBHOOK_CHANGED, (str(endpoint.id),)
        )
    ]


def test_only_the_owners_devices_hear_it_with_a_link_to_integrations() -> None:
    world = NoticeWorld()
    owner_device = world.alerts.add_device(world.alerts.owner, "de")
    world.alerts.add_device(world.alerts.staff, "en")
    endpoint = world.add_endpoint()

    world.fail(endpoint, times=FAILURES_BEFORE_DISABLE)

    [push] = world.alerts.push_queue.queued
    assert push.subscription_id == owner_device.id
    assert "Ein Webhook wurde abgeschaltet" in str(push.brief.title)
    # No label: the host names the address, never its path (a secret).
    assert "hooks.example.com" in str(push.brief.detail)
    assert "secret-hook-id" not in str(push.brief.detail)
    assert push.link is not None
    claims = StaffLinkSigner(TEST_ENCRYPTION_KEY).read(
        StaffLinkToken(str(push.link).rsplit("/", 1)[-1])
    )
    assert claims is not None and claims.target is StaffLinkTarget.INTEGRATIONS


def test_a_retried_attempt_and_later_failures_never_announce_it_again() -> None:
    world = NoticeWorld()
    endpoint = world.add_endpoint()
    world.fail(endpoint, times=FAILURES_BEFORE_DISABLE - 1)
    last = world.attempt(world.delivery(endpoint))

    world.recorder.run(last)
    switched_off_at = world.stored(endpoint).disabled_at
    # The job runs the same attempt again, and later events still fail.
    world.recorder.run(last)
    world.fail(endpoint, times=2)

    assert world.stored(endpoint).disabled_at == switched_off_at
    assert len(world.alerts.notifier.sent) == CONTACTS
    assert len(world.audit.list_by_business(world.business.id)) == 1
    assert len(world.live.events) == 1


def test_an_endpoint_switched_on_and_off_again_is_announced_again() -> None:
    world = NoticeWorld()
    endpoint = world.add_endpoint()
    world.fail(endpoint, times=FAILURES_BEFORE_DISABLE)
    first_switch_off = world.stored(endpoint).disabled_at

    world.switch_on(endpoint)
    world.fail(endpoint, times=FAILURES_BEFORE_DISABLE)

    second_switch_off = world.stored(endpoint).disabled_at
    assert first_switch_off != second_switch_off
    assert len(world.alerts.notifier.sent) == 2 * CONTACTS
    assert len(set(world.subjects())) == 2
    assert len(world.audit.list_by_business(world.business.id)) == 2
    assert [event.event for event in world.live.events] == [
        LiveEventKind.WEBHOOK_CHANGED,
        LiveEventKind.WEBHOOK_CHANGED,
    ]


def test_gone_says_why_and_an_unsubscribed_api_hook_goes_quietly() -> None:
    world = NoticeWorld()
    owned = world.add_endpoint(label="CRM")
    subscribed = world.add_endpoint(origin=WebhookEndpointOrigin.API)

    for endpoint in (owned, subscribed):
        world.recorder.run(
            world.attempt(world.delivery(endpoint), 410, WebhookDeliveryProblem.GONE)
        )

    assert world.stored(owned).status is WebhookEndpointStatus.DISABLED
    assert world.endpoints.get(world.business.id, subscribed.id) is None
    english = [
        str(text)
        for contact, text in world.alerts.notifier.sent
        if contact.channel is ManagerContactChannel.EMAIL
    ]
    assert len(english) == 1
    assert "answered that it is gone (410)" in english[0]


class UnreadableBusinesses(BusinessRepository):
    def get(self, business_id: BusinessId) -> BusinessDocument | None:
        raise RuntimeError(f"The database is gone ({business_id}).")


def test_a_failing_notice_never_breaks_the_recording() -> None:
    world = NoticeWorld(
        UnreadableBusinesses(InMemoryDocumentCollectionAdapter(BusinessDocument))
    )
    endpoint = world.add_endpoint()

    world.fail(endpoint, times=FAILURES_BEFORE_DISABLE)

    assert world.stored(endpoint).status is WebhookEndpointStatus.DISABLED
    assert world.alerts.notifier.sent == []
    assert len(world.audit.list_by_business(world.business.id)) == 1
