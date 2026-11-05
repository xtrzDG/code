"""
The English message of the daily digest of clients that newly turned
critical. The team works in English (the runbooks are English); a line
names the business, its country, why it is critical and its admin page.
"""

from collections.abc import Sequence

from app.schemas.constants.client_health import ClientHealthIssue
from app.schemas.domain.client_standings import ClientStandingDocument
from app.schemas.typings.monitoring.strings import PlatformAlertMessage
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl

CLIENT_PAGE_PATH: str = "/admin/clients/"
ISSUE_WORDS: dict[ClientHealthIssue, str] = {
    ClientHealthIssue.NO_SUBSCRIPTION: "no subscription",
    ClientHealthIssue.FIRST_PAYMENT_PENDING: "first payment pending",
    ClientHealthIssue.PAYMENT_PAST_DUE: "payment past due",
    ClientHealthIssue.SUBSCRIPTION_CANCELLED: "subscription cancelled",
    ClientHealthIssue.LEADS_ONLY_MODE: "leads only",
    ClientHealthIssue.NOT_PUBLISHED: "assistant not published",
    ClientHealthIssue.AUTOTESTS_FAILED: "checks failed",
    ClientHealthIssue.TOOL_ERRORS: "tool errors",
    ClientHealthIssue.MANY_HANDOFFS: "many handoffs",
    ClientHealthIssue.OPEN_QUESTIONS: "open questions",
    ClientHealthIssue.PACKAGE_EXCEEDED: "package exceeded",
    ClientHealthIssue.NEGATIVE_MARGIN: "losing money",
    ClientHealthIssue.SLOW_REPLIES: "slow replies",
    ClientHealthIssue.GUARD_SPIKE: "reply guard spike",
}


def compose_critical_digest(
    clients: Sequence[tuple[ClientStandingDocument, Sequence[ClientHealthIssue]]],
    cabinet_base_url: CabinetBaseUrl | None,
) -> PlatformAlertMessage:
    """
    "Clients that turned critical since yesterday's digest: 2", then a
    line per client (A to Z): name (country): issues, and its page.
    """

    count: int = len(clients)
    lines: list[str] = [f"Clients that turned critical since the last digest: {count}"]
    for standing, issues in sorted(clients, key=lambda item: str(item[0].name)):
        words: str = ", ".join(ISSUE_WORDS[issue] for issue in issues) or "critical"
        line: str = f"• {standing.name} ({standing.country_code}): {words}"
        if cabinet_base_url is not None:
            base: str = str(cabinet_base_url).rstrip("/")
            line += f"\n  {base}{CLIENT_PAGE_PATH}{standing.business_id}"

        lines.append(line)

    return PlatformAlertMessage("\n".join(lines))
