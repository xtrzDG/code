"""
The explicit tables of the authorization matrix. Every other business
operation is held to the default rules: a stranger gets 404, a caller
without a token 401, staff are let through, and the request runs only in
the storage scope of its business.
"""

from tests.platform.authorization_requests import BUSINESS_PREFIX as B

# Operations only owners may use; staff get 403 (AuthorizeBusinessAccess
# with required_role=OWNER): settings, team, billing, publishing, channels,
# the customers' personal data and the audit log.
OWNER_ONLY_OPERATIONS: frozenset[str] = frozenset(
    {
        f"PATCH {B}",
        f"POST {B}/assistant-versions",
        f"POST {B}/assistant-versions/{{version_id}}/autotests",
        f"POST {B}/assistant-versions/{{version_id}}/publish",
        f"POST {B}/assistant-versions/{{version_id}}/rollback",
        f"POST {B}/assistant/apply",
        f"GET {B}/audit-log",
        f"GET {B}/billing",
        f"POST {B}/billing/cancel",
        f"POST {B}/billing/checkout",
        f"POST {B}/billing/plan",
        f"POST {B}/billing/subscribe",
        f"POST {B}/billing/trial",
        f"GET {B}/call-settings",
        f"PUT {B}/call-settings",
        f"PUT {B}/channels/whatsapp/staff-template",
        f"PUT {B}/channels/{{channel}}",
        f"DELETE {B}/channels/{{channel}}",
        f"GET {B}/contacts",
        f"GET {B}/contacts/{{contact_id}}",
        f"DELETE {B}/contacts/{{contact_id}}",
        f"GET {B}/contacts/{{contact_id}}/export",
        f"POST {B}/dpa",
        f"PUT {B}/inbox/settings",
        f"DELETE {B}/integrations/google-calendar",
        f"GET {B}/integrations/google-calendar/connect-url",
        f"POST {B}/manager-contacts/telegram-link",
        f"POST {B}/members",
        f"POST {B}/notification-contacts/{{contact_key}}/test",
        f"PATCH {B}/members/{{user_id}}",
        f"DELETE {B}/members/{{user_id}}",
        f"PUT {B}/profile",
        f"POST {B}/quick-replies",
        f"PUT {B}/quick-replies/{{quick_reply_id}}",
        f"DELETE {B}/quick-replies/{{quick_reply_id}}",
        f"PATCH {B}/profile",
        f"PUT {B}/profile/steps/{{step}}",
        f"PUT {B}/public-slug",
        f"POST {B}/setup/starter-answers/apply",
        f"PUT {B}/setup/skipped-steps/{{setup_step}}",
        f"DELETE {B}/setup/skipped-steps/{{setup_step}}",
        f"GET {B}/text-backs",
        f"POST {B}/unanswered-questions/{{question_id}}/answer",
    }
)

# Operations that may look across businesses inside a business request,
# each explicitly with platform_wide(), and why.
PLATFORM_WIDE_LOOKUPS: dict[str, str] = {
    f"PUT {B}/channels/{{channel}}": (
        "a messaging account may serve only one business: the connect "
        "checks every business for it"
    ),
}

# Deviations from the default refusals (status for a stranger or without a
# token), each with its reason. Keep it empty unless a route truly cannot
# follow the rules.
REFUSAL_EXCEPTIONS: dict[str, str] = {}

# Reads whose record of business B has nothing to show even to its owner
# (the matrix still proves strangers get 404 there).
READS_WITHOUT_CONTENT: dict[str, str] = {
    f"GET {B}/calls/{{call_id}}/recording": (
        "the demo calls keep no recording (callers did not agree to one)"
    ),
}
