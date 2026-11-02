"""The access classes of the entry-point inventory and what each one means."""

from dataclasses import dataclass

PUBLIC: str = "public"
SIGNED_WEBHOOK: str = "signed_webhook"
CUSTOMER: str = "customer"
ACCOUNT: str = "account"
STAFF: str = "staff"
OWNER: str = "owner"
PLATFORM_ADMIN: str = "platform_admin"
API_KEY: str = "api_key"
OPERATOR_TOKEN: str = "operator_token"
AS_API: str = "as_api"
WORKER: str = "worker"
OPERATOR_SHELL: str = "operator_shell"

# Who may use an entry point of each class, from the least to the most
# trusted caller. The API's tests prove each class (the permission matrix
# names them).
ACCESS_CLASSES: dict[str, str] = {
    PUBLIC: "Anyone on the internet; the entry point's own limits protect it.",
    SIGNED_WEBHOOK: (
        "A provider (messaging, voice, telephony, payments) proving itself "
        "with its signature, secret token or handshake before anything is "
        "parsed."
    ),
    CUSTOMER: (
        "A business's customer: the website chat (the visitor's own key and "
        "the business's allowed origins), the hosted chat, or a signed link "
        "from a message (manage booking, review, calendar feed)."
    ),
    ACCOUNT: (
        "Any signed-in person, on their own account only (profile, sessions, "
        "authenticators, their businesses and brands, creating one)."
    ),
    STAFF: (
        "A member of the business: staff, an agency the owner let in, a "
        "brand's regional manager on their locations, and the owner."
    ),
    OWNER: "The business's owner (or the brand's owner); staff get 403.",
    PLATFORM_ADMIN: (
        "A platform admin signed in with two factors, holding the permission "
        "of their admin role (super, support_readonly, billing)."
    ),
    API_KEY: "A business's public API key; a cabinet session token is refused.",
    OPERATOR_TOKEN: "The platform's METRICS_TOKEN (the metrics scraper).",
    AS_API: (
        "The cabinet's proxy: forwards /v1/* with the session's token, so the "
        "API operation's own class applies."
    ),
    WORKER: (
        "Run by the background worker on its schedule, or from the queue the "
        "platform's own use cases fill after authorizing the request; no "
        "outside caller."
    ),
    OPERATOR_SHELL: (
        "A command of the backend image, run by Render (service start, cron) "
        "or by a person with shell access to the service."
    ),
}


@dataclass(frozen=True)
class HttpEntryPoint:
    """One HTTP method of one route and who may call it."""

    method: str
    path: str
    access: str
    scope: str
    protected_by: str
    in_production: bool = True

    @property
    def key(self) -> str:
        return f"{self.method} {self.path}"

    @property
    def changes_state(self) -> bool:
        return self.method not in ("GET", "HEAD", "OPTIONS")

    def as_json(self) -> dict[str, object]:
        entry: dict[str, object] = {
            "method": self.method,
            "path": self.path,
            "access": self.access,
            "scope": self.scope,
            "changes_state": self.changes_state,
            "protected_by": self.protected_by,
        }
        if not self.in_production:
            entry["in_production"] = False
        return entry
