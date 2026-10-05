"""
The declared lookup fields of the document collections, by collection.

Each TEXT, FILTER_TEXT and INTEGER field is a column `doc_<field>`: a
stored generated one up to migration 1120 (1010, 1040, 1042, 1043, 1051,
1052, 1061, 1062, 1074, 1081, 1082, 1090, 1093, 1094, 1100, 1102, 1103,
1112, 1113 and 1120, the last on a new table), a plain one filled by the
`<table>_lookup_columns` trigger from 1122 on, new tables (1134) too (the
online-safe pattern of migrations/README.md); each
ELEMENT_TEXT field a trigger over `workshop.document_lookup_keys`;
`document_lookup_fields` explains the kinds and checks queries against this
catalog. The platform's own collections (jobs, incidents, the status
page, analytics, admin access) are in `platform_lookup_catalog`.
"""

from collections.abc import Mapping

from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.client_care_collections import CLIENT_CARE_LOOKUP_FIELDS
from app.utilities.storage.lookup_field_builders import (
    element_field,
    filter_field,
    integer_field,
    text_field,
)
from app.utilities.storage.platform_lookup_catalog import PLATFORM_LOOKUP_FIELDS
from app.utilities.storage.quality_collections import QUALITY_LOOKUP_FIELDS

DOCUMENT_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    # Sign-in: a user by phone or e-mail, a session by its token hash (every
    # signed-in request), expired sessions and old login codes for the purge.
    # The accounts created in a period (the founder's sign-up cohorts, 1074).
    DocumentCollectionName("users"): (
        text_field("phone_number"),
        text_field("email"),
        integer_field("created_at"),
    ),
    # A user's sessions (Account → Security, ending the others) and the
    # purge of sessions unused too long (1103).
    DocumentCollectionName("user_sessions"): (
        text_field("token_hash"),
        integer_field("expires_at"),
        text_field("user_id"),
        integer_field("idle_expires_at"),
    ),
    DocumentCollectionName("otp_challenges"): (integer_field("created_at"),),
    # Two-factor sign-in (1082): authenticators (stored under their user's
    # id) in creation order for the key rotation's batches; a user's
    # recovery codes; old second steps of a sign-in for the purge.
    DocumentCollectionName("totp_factors"): (integer_field("created_at"),),
    DocumentCollectionName("recovery_codes"): (text_field("user_id"),),
    DocumentCollectionName("mfa_challenges"): (integer_field("created_at"),),
    # The businesses of a signed-in user. Periodic jobs walk every business
    # in first-write order, which needs no lookup column (1122).
    DocumentCollectionName("businesses"): (element_field("members[].user_id"),),
    # Webhook routing: the channel of an incoming message; channels in
    # error (a navigation badge, migration 1040; the admin system page,
    # 1093) and Meta tokens that run out soon (1093).
    DocumentCollectionName("channels"): (
        filter_field("kind"),
        text_field("external_id"),
        text_field("status"),
        integer_field("credential_expires_at"),
    ),
    # Every customer message: the contact, its open conversation, the
    # hourly message count and the transcript.
    # The CSV and full exports page through them by first contact (1113).
    # The customer list by last activity and the exact-name search (1122).
    DocumentCollectionName("contacts"): (
        text_field("phone_number"),
        text_field("verified_phone_number"),
        element_field("channel_identities[].channel_user_id"),
        integer_field("created_at"),
        integer_field("last_seen_at"),
        text_field("display_name_folded"),
    ),
    # The feed newest first (keyset pages), its filters, and the dashboard's
    # counts by channel, language and local day; the team inbox's views by
    # status, open request, waiting for the team and assignee (1053).
    DocumentCollectionName("conversations"): (
        text_field("contact_id"),
        text_field("channel_user_id"),
        text_field("status"),
        text_field("has_open_request"),
        text_field("awaits_team"),
        text_field("assignee_user_id"),
        filter_field("channel"),
        filter_field("language"),
        filter_field("is_after_hours"),
        filter_field("is_sandbox"),
        # Where customers came from, counted per period (Reports, 1100).
        filter_field("acquisition_source"),
        # Rated bad and not acted on yet ("Answers worth improving", 1112).
        text_field("awaits_improvement"),
        integer_field("last_message_at"),
        integer_field("created_at"),
    ),
    # The transcript (pages of older messages), the customer messages of a
    # period, the model usage per conversation and the tool errors.
    DocumentCollectionName("messages"): (
        text_field("conversation_id"),
        filter_field("direction"),
        filter_field("author"),
        integer_field("created_at"),
        integer_field("input_tokens"),
        integer_field("output_tokens"),
        integer_field("cost_micro_usd"),
        element_field("tool_calls[].is_error"),
        # Reply latency per channel (admin client health, 1090).
        filter_field("channel"),
        integer_field("reply_latency_ms"),
        # What the reply guard did and flagged (admin health, the injection
        # brake of a contact, 1102).
        filter_field("guard_verdict"),
        filter_field("injection_flag"),
    ),
    DocumentCollectionName("llm_turns"): (
        text_field("conversation_id"),
        integer_field("sequence_number"),
    ),
    DocumentCollectionName("calls"): (
        text_field("provider_call_id"),
        text_field("conversation_id"),
    ),
    # Customer files past their retention, oldest first (1081).
    DocumentCollectionName("message_media"): (integer_field("created_at"),),
    # Bookings by start (list pages, availability: the ones not over yet),
    # by creation (dashboard), by status (badges, migration 1040), and those
    # of one conversation; their value per currency (dashboard and value
    # model sums, 1083).
    DocumentCollectionName("bookings"): (
        text_field("conversation_id"),
        text_field("status"),
        filter_field("resource_id"),
        filter_field("is_sandbox"),
        filter_field("currency_code"),
        integer_field("starts_at"),
        integer_field("ends_at"),
        integer_field("created_at"),
        integer_field("value_minor"),
        # A page of customers' bookings, counted per channel (1122).
        text_field("contact_id"),
        filter_field("source_channel"),
    ),
    DocumentCollectionName("leads"): (
        text_field("conversation_id"),
        text_field("status"),
        filter_field("is_sandbox"),
        integer_field("created_at"),
        # A page of customers' leads, counted per channel (1122).
        text_field("contact_id"),
        filter_field("source_channel"),
    ),
    # Open handoffs by urgency and age, resolved ones by resolution time.
    DocumentCollectionName("handoffs"): (
        text_field("conversation_id"),
        text_field("status"),
        filter_field("urgency"),
        filter_field("reason"),
        filter_field("is_sandbox"),
        integer_field("created_at"),
        integer_field("resolved_at"),
    ),
    # The notes of one conversation, newest first (1053).
    DocumentCollectionName("conversation_notes"): (
        text_field("conversation_id"),
        integer_field("created_at"),
    ),
    DocumentCollectionName("unanswered_questions"): (
        text_field("is_resolved"),
        filter_field("is_sandbox"),
        integer_field("occurrence_count"),
        integer_field("last_seen_at"),
    ),
    # The audit log newest first, filtered by operation, entity and person.
    DocumentCollectionName("audit_log_entries"): (
        text_field("actor_id"),
        filter_field("action"),
        filter_field("entity"),
        integer_field("created_at"),
    ),
    # Usage of a billing period.
    DocumentCollectionName("usage_events"): (integer_field("occurred_at"),),
    # Webhook redelivery receipts (unique per message) and their purge.
    DocumentCollectionName("channel_message_receipts"): (
        filter_field("channel"),
        text_field("provider_message_id"),
        integer_field("created_at"),
    ),
    # The inbox and the outbox: their purge; one recipient's messages that
    # still wait (they go out in order).
    # The inbox by arrival (the purge) and by status and arrival (the
    # sweeper of stale events, 1094).
    # A customer's events by their account and conversations (erasure, 1113).
    DocumentCollectionName("inbound_events"): (
        integer_field("created_at"),
        text_field("status"),
        text_field("customer_channel_user_id"),
        text_field("conversation_id"),
    ),
    DocumentCollectionName("outbound_messages"): (
        text_field("recipient_key"),
        filter_field("status"),
        integer_field("created_at"),
    ),
    # "/start <code>" of the platform bot.
    DocumentCollectionName("manager_telegram_links"): (text_field("code_hash"),),
    # The devices of one user in a business (Settings, "this device").
    DocumentCollectionName("push_subscriptions"): (text_field("user_id"),),
    # The text-backs of a business newest first (Settings → Calls) and the
    # retention purge (1051).
    # A caller's missed calls by their number (erasure, 1113).
    DocumentCollectionName("missed_calls"): (
        integer_field("created_at"),
        text_field("caller_phone_number"),
    ),
    # The FAQ of a business: the website chat's starter questions (1052);
    # the item that corrected an assistant answer (1112); the knowledge
    # list, last changed first, of one kind and state (1122).
    DocumentCollectionName("knowledge_items"): (
        text_field("kind"),
        text_field("correction_of"),
        integer_field("updated_at"),
        filter_field("is_active"),
    ),
    # The stored digests and monthly reports of a business, newest period
    # first, of one kind (1061).
    DocumentCollectionName("value_reports"): (
        text_field("kind"),
        integer_field("starts_at"),
    ),
    # Feedback after visits (1062): the businesses that ask (the periodic
    # job, across businesses); a customer's request waiting for a rating;
    # a review link by its public token (across businesses); the requests
    # of a business newest first, and their counts, rating and link-visit
    # sums by status for the statistics.
    DocumentCollectionName("review_settings"): (text_field("is_feedback_enabled"),),
    DocumentCollectionName("feedback_requests"): (
        text_field("contact_id"),
        text_field("status"),
        text_field("review_token"),
        integer_field("created_at"),
        integer_field("score"),
        integer_field("review_clicks"),
    ),
    # A business's full exports newest first, the purge of expired ones (1113).
    DocumentCollectionName("business_exports"): (
        integer_field("created_at"),
        integer_field("expires_at"),
    ),
    # The hourly purge of expired one-time export download links (1134).
    DocumentCollectionName("export_download_links"): (integer_field("expires_at"),),
    # The judge's scores of real conversations (1120).
    **QUALITY_LOOKUP_FIELDS,
    **CLIENT_CARE_LOOKUP_FIELDS,
    # The platform's own records.
    **PLATFORM_LOOKUP_FIELDS,
}
