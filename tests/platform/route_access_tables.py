"""
The reviewed list of operations outside /v1/businesses/{business_id} that
answer without a cabinet token or an API key, each with what protects it
instead. tests/platform/test_route_authentication.py refuses every other
operation without credentials; adding a public operation means adding it
here with its reason.
"""

# Operations open to anyone, by "METHOD path", and why that is safe.
PUBLIC_OPERATIONS: dict[str, str] = {
    "GET /v1/auth/login-options": "which sign-in methods exist; no account data",
    "POST /v1/auth/otp/start": "starts a sign-in; per-address and per-number caps",
    "POST /v1/auth/otp/verify": "checks a code; attempts are counted atomically",
    "POST /v1/auth/mfa/verify": "second factor of a sign-in challenge it names",
    "POST /v1/auth/mfa/enroll": "enrolment during a sign-in challenge it names",
    "GET /v1/catalog/countries": "public reference data",
    "GET /v1/catalog/countries/{country_code}": "public reference data",
    "GET /v1/catalog/languages": "public reference data",
    "GET /v1/catalog/plans": "public price list",
    "GET /v1/catalog/niches": "public reference data",
    "GET /v1/catalog/niches/{niche_key}": "public reference data",
    "POST /v1/phone-numbers/parse": "formats a number the caller typed",
    "GET /v1/legal/dpa/{version}": "published legal text",
    "GET /v1/legal/subprocessors": "published sub-processor list",
    "GET /v1/legal/overview": "published legal texts",
    "GET /v1/legal/{document}": "published legal text",
    "GET /v1/help/{language}": "public help centre",
    "GET /v1/help/{language}/search": "public help centre",
    "GET /v1/help/{language}/{slug}": "public help centre",
    "GET /v1/support/contacts": "published support contacts",
    "GET /v1/platform/status": "public status page",
    "GET /v1/public-demos": "the landing page's demo assistants",
    "POST /v1/public-demos/{business_id}/messages": "demo sandbox, rate limited",
    "GET /v1/public/chat/{address}": "a business's published hosted chat",
    "GET /v1/public/bookings/{token}": "a signed manage link (HMAC token)",
    "GET /v1/public/bookings/{token}/calendar.ics": "a signed manage link",
    "GET /v1/public/bookings/{token}/slots": "a signed manage link",
    "POST /v1/public/bookings/{token}/cancel": "a signed manage link",
    "POST /v1/public/bookings/{token}/reschedule": "a signed manage link",
    "GET /v1/public/reviews/{token}": "a signed review link",
    "GET /v1/public/ical/{token}.ics": "an unguessable feed token of a resource",
    "GET /v1/widget/{business_id}/config": "website chat; allowed origins, limits",
    "POST /v1/widget/{business_id}/messages": "website chat; visitor limits",
    "GET /v1/widget/{business_id}/messages": "website chat; the visitor's own",
    "GET /v1/widget/{business_id}/events": "website chat; a signed stream ticket",
    "POST /v1/widget/{business_id}/handoff": "website chat; the visitor's own",
    "POST /v1/widget/errors": "the widget's error beacon, rate limited",
    "POST /v1/channels/telegram/{channel_id}/webhook": "Telegram's secret token",
    "GET /v1/channels/meta/webhook": "Meta's verify token handshake",
    "POST /v1/channels/meta/webhook": "Meta's app-secret signature",
    "POST /v1/channels/telegram-platform/webhook": "Telegram's secret token",
    "POST /v1/voice/tools/{tool_name}": "the voice platform's shared secret",
    "POST /v1/voice/webhooks/conversation-initiation": "voice platform secret",
    "POST /v1/voice/webhooks/post-call": "the voice platform's HMAC signature",
    "POST /v1/payments/flitt/webhook": "Flitt's signature",
    "GET /v1/telephony/zadarma/notifications": "Zadarma's echo handshake",
    "POST /v1/telephony/zadarma/notifications": "Zadarma's signature",
    "GET /v1/integrations/google-calendar/callback": "a signed OAuth state",
}
# Prefixes whose operations need the platform admin role on top of a token.
ADMIN_PREFIX: str = "/v1/admin/"
# Operations that take a public API key, never a cabinet token.
PUBLIC_API_PREFIX: str = "/v1/public-api/"
A: str = ADMIN_PREFIX + "clients/{business_id}"
REASON: str = "Matrix check"
# Valid bodies and queries of admin operations, so that the refusal of a
# business owner does not depend on a malformed request.
ADMIN_BODIES: dict[str, dict[str, object]] = {
    "POST /v1/admin/announcements": {
        "level": "info",
        "messages": [{"language": "en", "text": "Planned maintenance"}],
    },
    "PATCH /v1/admin/announcements/{announcement_id}": {"resolve": True},
    "POST /v1/admin/incidents": {
        "kind": "outage",
        "severity": "sev3",
        "title": "Matrix check",
        "started_at": 1_790_000_000_000_000,
        "scope": "all_businesses",
    },
    "POST /v1/admin/team": {"email": "someone@example.com", "role": "billing"},
    "PATCH /v1/admin/team/{admin_id}": {"role": "billing"},
    "POST /v1/admin/partners": {
        "name": "Agency",
        "commission_rate_basis_points": 1000,
        "code": "AGENCY",
    },
    "PATCH /v1/admin/partners/{partner_id}": {"status": "paused"},
    "POST /v1/admin/partners/{partner_id}/codes": {"code": "AGENCY2"},
    "POST /v1/admin/partners/{partner_id}/payouts": {
        "month": "2026-09",
        "reference": "Transfer 1",
    },
    f"POST {A}/open": {"reason": REASON},
    f"POST {A}/trial-extension": {"days": 7, "reason": REASON},
    f"POST {A}/discount": {"percent": 10, "last_day": "2026-12-31", "reason": REASON},
    f"POST {A}/credits": {"amount_minor": 100, "reason": REASON},
    f"POST {A}/setup-fee-waiver": {"reason": REASON},
    f"POST {A}/invoices/{{invoice_id}}/manual-payment": {
        "method": "cash",
        "reference": "Receipt 1",
        "reason": REASON,
    },
    f"POST {A}/plan": {"plan_key": "chat", "reason": REASON},
    f"POST {A}/notes": {"text": REASON},
    f"PATCH {A}/notes/{{note_id}}": {"text": REASON},
}
ADMIN_QUERIES: dict[str, dict[str, str]] = {
    "GET /v1/admin/partners/payouts": {"month": "2026-09"},
}
