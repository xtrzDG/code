"""
The declared lookup fields of the platform's own collections: the worker's
pulse and queue, incidents and maintenance runs, the status page, exchange
rates, growth analytics and platform access. Part of DOCUMENT_LOOKUP_FIELDS
(`document_lookup_catalog`), which explains the columns and triggers.
"""

from collections.abc import Mapping

from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.lookup_field_builders import (
    filter_field,
    integer_field,
    text_field,
)

PLATFORM_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    # The freshest worker pulse (GET /readyz) and the purge of old ones.
    DocumentCollectionName("worker_heartbeats"): (integer_field("beat_at"),),
    # The admin system page and the platform alerts (1093): queued jobs
    # counted by state and lane (and by name), the oldest due job of a
    # lane; the incident log newest first; the last backup and drill.
    DocumentCollectionName("queued_jobs"): (
        text_field("status"),
        text_field("lane"),
        filter_field("name"),
        integer_field("run_at"),
    ),
    DocumentCollectionName("incidents"): (integer_field("created_at"),),
    # The platform admin's client list (1122): a keyset page in one of its
    # orders (each client's position among all of them), filtered and
    # counted by status, health, country and niche.
    DocumentCollectionName("client_standings"): (
        text_field("business_status"),
        text_field("health_status"),
        text_field("country_code"),
        text_field("niche_key"),
        filter_field("is_losing_money"),
        integer_field("health_position"),
        integer_field("name_position"),
        integer_field("usage_position"),
        integer_field("margin_position"),
        integer_field("cost_position"),
        integer_field("revenue_position"),
    ),
    # The status page (1111): the announcements in effect, those resolved
    # in the last ninety days, the admin's pages newest first.
    DocumentCollectionName("platform_announcements"): (
        text_field("status"),
        integer_field("resolved_at"),
        integer_field("created_at"),
    ),
    DocumentCollectionName("maintenance_runs"): (
        text_field("kind"),
        integer_field("finished_at"),
    ),
    # The newest rate of a currency pair (1071).
    DocumentCollectionName("exchange_rates"): (
        text_field("pair"),
        integer_field("rate_day"),
    ),
    # Growth analytics (1074): owners' steps by name within a time range;
    # Web Vitals counted per vital within a time range, grouped by route
    # and device and bucketed by value, and purged by age.
    DocumentCollectionName("product_events"): (
        text_field("name"),
        integer_field("occurred_at"),
    ),
    DocumentCollectionName("web_vital_samples"): (
        text_field("metric"),
        filter_field("route"),
        filter_field("device_class"),
        integer_field("value"),
        integer_field("created_at"),
    ),
    # Platform access (1103): an admin by sign-in phone or e-mail, the
    # admins of a role (is a SUPER admin recorded?); the open support
    # grants of a business (its banner) or of everywhere (the job that
    # ends expired ones), and one admin's grant in a business.
    DocumentCollectionName("platform_admins"): (
        text_field("phone_number"),
        text_field("email"),
        text_field("role"),
    ),
    DocumentCollectionName("support_access_grants"): (
        text_field("status"),
        text_field("admin_user_id"),
    ),
    # The SLIs (1163): a series' slots of a window (burn rates), the hourly
    # rows of the last 28 days (the error budget), both purged by age.
    DocumentCollectionName("service_level_slots"): (
        text_field("series"),
        integer_field("slot_start"),
    ),
    DocumentCollectionName("service_level_hours"): (integer_field("hour_start"),),
}
