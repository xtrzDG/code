"""
The `refresh_whatsapp_tokens` job on the real container, as the batch
worker runs it: a WhatsApp number connected through Embedded Signup whose
token ends within META_TOKEN_REFRESH_DAYS gets Meta's renewed token (the
real OAuth client behind the `provider:meta` circuit, Meta's token
endpoints scripted), sealed with the platform's key and noted in the
business's audit log without an actor; when Meta refuses, the old token
stays and the owner's account e-mail is queued once. Nothing leaves the
test.
"""

from collections.abc import Iterator
from typing import cast

import pytest
from typed_time_provider import Microseconds

from app.clients.meta.meta_oauth_client import MetaOAuthClient
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.gateways.worker.periodic.channel_credentials import (
    REFRESH_WHATSAPP_TOKENS_JOB,
)
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelExternalId, ChannelSecret
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
)
from app.schemas.typings.users.prefixed_id import UserId
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.workshop_container import replace_provider
from tests.meta_connection.token_refresh_fakes import WABA_ID, ScriptedMetaTokens

OWNER_EMAIL: str = "owner@funicular.example"
OLD_TOKEN: str = "EAAfake-token-1"
NEW_TOKEN: str = "EAAfake-token-2"
SECOND: int = 1_000_000
DAY: int = 24 * 60 * 60 * SECOND
META_APP_ENVIRONMENT: dict[str, str] = {
    **E2E_ENVIRONMENT,
    "META_APP_ID": "1234567890",
    "META_APP_SECRET": "e2e-meta-app-secret-0000",  # gitleaks:allow
}


@pytest.fixture
def meta() -> ScriptedMetaTokens:
    return ScriptedMetaTokens()


@pytest.fixture
def workshop(meta: ScriptedMetaTokens) -> Iterator[Workshop]:
    running = start_workshop(
        META_APP_ENVIRONMENT,
        prepare=lambda container: replace_provider(
            container.clients.meta_oauth_client,
            MetaOAuthClient(transport=meta.build()),
        ),
    )
    with running.client:
        yield running


def now(workshop: Workshop) -> Microseconds:
    return workshop.container.time_provider.microsecond_wall_clock().now_unix()


def days_from_now(workshop: Workshop, days: int) -> Microseconds:
    """A whole second, as Meta's `debug_token` names the end."""

    return Microseconds(int(now(workshop)) // SECOND * SECOND + days * DAY)


def connect_whatsapp(workshop: Workshop, ends_at: Microseconds) -> ChannelDocument:
    """An owner's business whose number came through Embedded Signup."""

    token, _ = workshop.sign_in_with_email(OWNER_EMAIL)
    created = workshop.client.post(
        "/v1/businesses",
        json={"name": "Funicular", "niche_key": "restaurant", "country_code": "IT"},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    container = workshop.container
    moment: Microseconds = now(workshop)
    channel = ChannelDocument(
        business_id=BusinessId(str(created.json()["id"])),
        kind=ChannelKind.WHATSAPP,
        status=ChannelStatus.CONNECTED,
        external_id=ChannelExternalId("106540352242922"),
        encrypted_secret=container.adapters.secret_cipher().encrypt(
            ChannelSecret(OLD_TOKEN)
        ),
        whatsapp_business_account_id=WhatsAppBusinessAccountId(WABA_ID),
        credential_expires_at=ends_at,
        credential_checked_at=moment,
        created_at=moment,
        updated_at=moment,
    )
    with container.utilities.storage_scope().platform_wide():
        container.repositories.channel_repo().save(channel)
    return channel


def run_the_job(workshop: Workshop) -> int:
    """One run of the job the worker registered under its name."""

    jobs = cast(list[PeriodicJobSpec], workshop.container.gateways.periodic_jobs())
    job: PeriodicJobSpec = next(
        job for job in jobs if job.name == REFRESH_WHATSAPP_TOKENS_JOB
    )
    report = job.operator.operate(
        JobTick(job_name=job.name, scheduled_at=now(workshop))
    )
    return int(report.processed_count)


def token_of(workshop: Workshop, channel: ChannelDocument) -> tuple[str, str]:
    """The stored token, opened with the platform's key, and its sealing."""

    container = workshop.container
    with container.utilities.storage_scope().platform_wide():
        stored = container.repositories.channel_repo().get(channel.id)
    assert stored is not None and stored.encrypted_secret is not None
    opened = container.adapters.secret_cipher().decrypt(stored.encrypted_secret)
    return str(opened), str(stored.encrypted_secret)


def channel_audit(
    workshop: Workshop, channel: ChannelDocument
) -> list[tuple[AuditAction, UserId | None]]:
    """What the business's audit log says happened to the channel, and who."""

    entries = workshop.container.adapters.collections.audit_log_entry_collection()
    with workshop.container.utilities.storage_scope().platform_wide():
        stored: list[AuditLogEntryDocument] = entries.list_all()
    return [
        (entry.action, entry.actor_id)
        for entry in stored
        if entry.business_id == channel.business_id
        and str(entry.entity_id) == str(channel.id)
    ]


def token_notices(workshop: Workshop, channel: ChannelDocument) -> list[str]:
    """The addresses the outbox holds a WhatsApp token notice for."""

    messages = workshop.container.adapters.collections.outbound_message_collection()
    with workshop.container.utilities.storage_scope().platform_wide():
        stored: list[OutboundMessageDocument] = messages.list_all()
    return [
        str(message.staff_contact.address)
        for message in stored
        if message.business_id == channel.business_id
        and message.kind is OutboundMessageKind.STAFF_NOTIFICATION
        and message.staff_contact is not None
        and f"whatsapp_token:{channel.id}-" in str(message.idempotency_key)
    ]


def test_the_batch_worker_renews_a_token_that_ends_soon(
    workshop: Workshop, meta: ScriptedMetaTokens
) -> None:
    channel = connect_whatsapp(workshop, days_from_now(workshop, 10))
    renewed_end = days_from_now(workshop, 60)
    meta.renew(OLD_TOKEN, NEW_TOKEN, renewed_end)

    processed = run_the_job(workshop)
    token, sealing = token_of(workshop, channel)

    assert processed == 1
    assert meta.renewed() == [OLD_TOKEN]
    assert token == NEW_TOKEN
    assert NEW_TOKEN not in sealing
    assert channel_audit(workshop, channel) == [(AuditAction.UPDATE, None)]
    assert token_notices(workshop, channel) == []
    with workshop.container.utilities.storage_scope().platform_wide():
        stored = workshop.container.repositories.channel_repo().get(channel.id)
    assert stored is not None
    assert stored.credential_expires_at == renewed_end
    assert stored.status is ChannelStatus.CONNECTED


def test_a_refused_renewal_keeps_the_token_and_mails_the_owner_once(
    workshop: Workshop, meta: ScriptedMetaTokens
) -> None:
    channel = connect_whatsapp(workshop, days_from_now(workshop, 10))
    meta.refuse(OLD_TOKEN)

    first = run_the_job(workshop)
    second = run_the_job(workshop)
    token, _ = token_of(workshop, channel)

    assert meta.renewed() == [OLD_TOKEN, OLD_TOKEN]
    assert token == OLD_TOKEN
    assert channel_audit(workshop, channel) == []
    assert (first, second) == (1, 1)
    assert token_notices(workshop, channel) == [OWNER_EMAIL]
