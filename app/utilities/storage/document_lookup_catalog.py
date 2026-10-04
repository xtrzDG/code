"""
The declared lookup fields of the document collections, by collection.

Each TEXT, FILTER_TEXT and INTEGER field is a generated column
`doc_<field>` (migrations 1010, 1040, 1042, 1043, 1051, 1052, 1061, 1062,
1074, 1081, 1082, 1090, 1093, 1094, 1100 and 1102), each ELEMENT_TEXT field
a trigger over `workshop.document_lookup_keys`; `document_lookup_fields`
explains the kinds and checks queries against this catalog.
"""

from collections.abc import Mapping

from app.schemas.constants.storage import LookupFieldKind
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)


def _text(path: str) -> DocumentLookupField:
    return DocumentLookupField(path=DocumentFieldPath(path), kind=LookupFieldKind.TEXT)


def _filter(path: str) -> DocumentLookupField:
    return DocumentLookupField(
        path=DocumentFieldPath(path), kind=LookupFieldKind.FILTER_TEXT
    )


def _integer(path: str) -> DocumentLookupField:
    return DocumentLookupField(
        path=DocumentFieldPath(path), kind=LookupFieldKind.INTEGER
    )


def _element(path: str) -> DocumentLookupField:
    return DocumentLookupField(
        path=DocumentFieldPath(path), kind=LookupFieldKind.ELEMENT_TEXT
    )


DOCUMENT_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    # Sign-in: a user by phone or e-mail, a session by its token hash (every
    # signed-in request), expired sessions and old login codes for the purge.
    # The accounts created in a period (the founder's sign-up cohorts, 1074).
    DocumentCollectionName("users"): (
        _text("phone_number"),
        _text("email"),
        _integer("created_at"),
    ),
    DocumentCollectionName("user_sessions"): (
        _text("token_hash"),
        _integer("expires_at"),
    ),
    DocumentCollectionName("otp_challenges"): (_integer("created_at"),),
    # Two-factor sign-in (1082): authenticators (stored under their user's
    # id) in creation order for the key rotation's batches; a user's
    # recovery codes; old second steps of a sign-in for the purge.
    DocumentCollectionName("totp_factors"): (_integer("created_at"),),
    DocumentCollectionName("recovery_codes"): (_text("user_id"),),
    DocumentCollectionName("mfa_challenges"): (_integer("created_at"),),
    # The businesses of a signed-in user.
    DocumentCollectionName("businesses"): (_element("members[].user_id"),),
    # Webhook routing: the channel of an incoming message; channels in
    # error (a navigation badge, migration 1040; the admin system page,
    # 1093) and Meta tokens that run out soon (1093).
    DocumentCollectionName("channels"): (
        _filter("kind"),
        _text("external_id"),
        _text("status"),
        _integer("credential_expires_at"),
    ),
    # Every customer message: the contact, its open conversation, the
    # hourly message count and the transcript.
    DocumentCollectionName("contacts"): (
        _text("phone_number"),
        _text("verified_phone_number"),
        _element("channel_identities[].channel_user_id"),
    ),
    # The feed newest first (keyset pages), its filters, and the dashboard's
    # counts by channel, language and local day; the team inbox's views by
    # status, open request, waiting for the team and assignee (1053).
    DocumentCollectionName("conversations"): (
        _text("contact_id"),
        _text("channel_user_id"),
        _text("status"),
        _text("has_open_request"),
        _text("awaits_team"),
        _text("assignee_user_id"),
        _filter("channel"),
        _filter("language"),
        _filter("is_after_hours"),
        _filter("is_sandbox"),
        # Where customers came from, counted per period (Reports, 1100).
        _filter("acquisition_source"),
        _integer("last_message_at"),
        _integer("created_at"),
    ),
    # The transcript (pages of older messages), the customer messages of a
    # period, the model usage per conversation and the tool errors.
    DocumentCollectionName("messages"): (
        _text("conversation_id"),
        _filter("direction"),
        _filter("author"),
        _integer("created_at"),
        _integer("input_tokens"),
        _integer("output_tokens"),
        _integer("cost_micro_usd"),
        _element("tool_calls[].is_error"),
        # Reply latency per channel (admin client health, 1090).
        _filter("channel"),
        _integer("reply_latency_ms"),
        # What the reply guard did and flagged (admin health, the injection
        # brake of a contact, 1102).
        _filter("guard_verdict"),
        _filter("injection_flag"),
    ),
    DocumentCollectionName("llm_turns"): (
        _text("conversation_id"),
        _integer("sequence_number"),
    ),
    DocumentCollectionName("calls"): (
        _text("provider_call_id"),
        _text("conversation_id"),
    ),
    # Customer files past their retention, oldest first (1081).
    DocumentCollectionName("message_media"): (_integer("created_at"),),
    # Bookings by start (list pages, availability: the ones not over yet),
    # by creation (dashboard), by status (badges, migration 1040), and those
    # of one conversation; their value per currency (dashboard and value
    # model sums, 1083).
    DocumentCollectionName("bookings"): (
        _text("conversation_id"),
        _text("status"),
        _filter("resource_id"),
        _filter("is_sandbox"),
        _filter("currency_code"),
        _integer("starts_at"),
        _integer("ends_at"),
        _integer("created_at"),
        _integer("value_minor"),
    ),
    DocumentCollectionName("leads"): (
        _text("conversation_id"),
        _text("status"),
        _filter("is_sandbox"),
        _integer("created_at"),
    ),
    # Open handoffs by urgency and age, resolved ones by resolution time.
    DocumentCollectionName("handoffs"): (
        _text("conversation_id"),
        _text("status"),
        _filter("urgency"),
        _filter("reason"),
        _filter("is_sandbox"),
        _integer("created_at"),
        _integer("resolved_at"),
    ),
    # The notes of one conversation, newest first (1053).
    DocumentCollectionName("conversation_notes"): (
        _text("conversation_id"),
        _integer("created_at"),
    ),
    DocumentCollectionName("unanswered_questions"): (
        _text("is_resolved"),
        _filter("is_sandbox"),
        _integer("occurrence_count"),
        _integer("last_seen_at"),
    ),
    # The audit log newest first, filtered by operation, entity and person.
    DocumentCollectionName("audit_log_entries"): (
        _text("actor_id"),
        _filter("action"),
        _filter("entity"),
        _integer("created_at"),
    ),
    # Usage of a billing period.
    DocumentCollectionName("usage_events"): (_integer("occurred_at"),),
    # Webhook redelivery receipts (unique per message) and their purge.
    DocumentCollectionName("channel_message_receipts"): (
        _filter("channel"),
        _text("provider_message_id"),
        _integer("created_at"),
    ),
    # The inbox and the outbox: their purge; one recipient's messages that
    # still wait (they go out in order).
    # The inbox by arrival (the purge) and by status and arrival (the
    # sweeper of stale events, 1094).
    DocumentCollectionName("inbound_events"): (
        _integer("created_at"),
        _text("status"),
    ),
    DocumentCollectionName("outbound_messages"): (
        _text("recipient_key"),
        _filter("status"),
        _integer("created_at"),
    ),
    # "/start <code>" of the platform bot.
    DocumentCollectionName("manager_telegram_links"): (_text("code_hash"),),
    # The freshest worker pulse (GET /readyz) and the purge of old ones.
    DocumentCollectionName("worker_heartbeats"): (_integer("beat_at"),),
    # The admin system page and the platform alerts (1093): queued jobs
    # counted by state and lane (and by name), the oldest due job of a
    # lane; the incident log newest first; the last backup and drill.
    DocumentCollectionName("queued_jobs"): (
        _text("status"),
        _text("lane"),
        _filter("name"),
        _integer("run_at"),
    ),
    DocumentCollectionName("incidents"): (_integer("created_at"),),
    DocumentCollectionName("maintenance_runs"): (
        _text("kind"),
        _integer("finished_at"),
    ),
    # The newest rate of a currency pair (1071).
    DocumentCollectionName("exchange_rates"): (_text("pair"), _integer("rate_day")),
    # The devices of one user in a business (Settings, "this device").
    DocumentCollectionName("push_subscriptions"): (_text("user_id"),),
    # The text-backs of a business newest first (Settings → Calls) and the
    # retention purge (1051).
    DocumentCollectionName("missed_calls"): (_integer("created_at"),),
    # The FAQ of a business: the website chat's starter questions (1052).
    DocumentCollectionName("knowledge_items"): (_text("kind"),),
    # The stored digests and monthly reports of a business, newest period
    # first, of one kind (1061).
    DocumentCollectionName("value_reports"): (_text("kind"), _integer("starts_at")),
    # Feedback after visits (1062): the businesses that ask (the periodic
    # job, across businesses); a customer's request waiting for a rating;
    # a review link by its public token (across businesses); the requests
    # of a business newest first, and their counts, rating and link-visit
    # sums by status for the statistics.
    DocumentCollectionName("review_settings"): (_text("is_feedback_enabled"),),
    DocumentCollectionName("feedback_requests"): (
        _text("contact_id"),
        _text("status"),
        _text("review_token"),
        _integer("created_at"),
        _integer("score"),
        _integer("review_clicks"),
    ),
    # Growth analytics (1074): owners' steps by name within a time range;
    # Web Vitals counted per vital within a time range, grouped by route
    # and device and bucketed by value, and purged by age.
    DocumentCollectionName("product_events"): (
        _text("name"),
        _integer("occurred_at"),
    ),
    DocumentCollectionName("web_vital_samples"): (
        _text("metric"),
        _filter("route"),
        _filter("device_class"),
        _integer("value"),
        _integer("created_at"),
    ),
}
