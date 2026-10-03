"""
The declared lookup fields of the document collections, by collection.

Each TEXT, FILTER_TEXT and INTEGER field is a generated column
`doc_<field>` (migrations 1010, 1040, 1042, 1043, 1051 and 1052), each
ELEMENT_TEXT field a trigger over `workshop.document_lookup_keys`;
`document_lookup_fields` explains the kinds and checks queries against
this catalog.
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
    DocumentCollectionName("users"): (_text("phone_number"), _text("email")),
    DocumentCollectionName("user_sessions"): (
        _text("token_hash"),
        _integer("expires_at"),
    ),
    DocumentCollectionName("otp_challenges"): (_integer("created_at"),),
    # The businesses of a signed-in user.
    DocumentCollectionName("businesses"): (_element("members[].user_id"),),
    # Webhook routing: the channel of an incoming message; channels in
    # error (a navigation badge, migration 1040).
    DocumentCollectionName("channels"): (
        _filter("kind"),
        _text("external_id"),
        _text("status"),
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
    ),
    DocumentCollectionName("llm_turns"): (
        _text("conversation_id"),
        _integer("sequence_number"),
    ),
    DocumentCollectionName("calls"): (
        _text("provider_call_id"),
        _text("conversation_id"),
    ),
    # Bookings by start (list pages, availability: the ones not over yet),
    # by creation (dashboard), by status (badges, migration 1040), and those
    # of one conversation.
    DocumentCollectionName("bookings"): (
        _text("conversation_id"),
        _text("status"),
        _filter("resource_id"),
        _filter("is_sandbox"),
        _integer("starts_at"),
        _integer("ends_at"),
        _integer("created_at"),
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
    DocumentCollectionName("inbound_events"): (_integer("created_at"),),
    DocumentCollectionName("outbound_messages"): (
        _text("recipient_key"),
        _filter("status"),
        _integer("created_at"),
    ),
    # "/start <code>" of the platform bot.
    DocumentCollectionName("manager_telegram_links"): (_text("code_hash"),),
    # The freshest worker pulse (GET /readyz) and the purge of old ones.
    DocumentCollectionName("worker_heartbeats"): (_integer("beat_at"),),
    # The devices of one user in a business (Settings, "this device").
    DocumentCollectionName("push_subscriptions"): (_text("user_id"),),
    # The text-backs of a business newest first (Settings → Calls) and the
    # retention purge (1051).
    DocumentCollectionName("missed_calls"): (_integer("created_at"),),
    # The FAQ of a business: the website chat's starter questions (1052).
    DocumentCollectionName("knowledge_items"): (_text("kind"),),
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
}
