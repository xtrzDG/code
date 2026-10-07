"""Why a client needs a look, and how urgent it is."""

from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.client_health import ClientHealthIssue, ClientHealthStatus
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.dto.admin import AdminClientSummary
from app.utilities.client_health.guard_activity import is_guard_spike
from app.utilities.client_health.reply_speed import is_slow

MANY_HANDOFFS_THRESHOLD: int = 20
OPEN_QUESTIONS_THRESHOLD: int = 5
CRITICAL_ISSUES: frozenset[ClientHealthIssue] = frozenset(
    {ClientHealthIssue.LEADS_ONLY_MODE, ClientHealthIssue.NEGATIVE_MARGIN}
)


def find_health_issues(
    summary: AdminClientSummary,
    subscription: SubscriptionDocument | None,
) -> list[ClientHealthIssue]:
    """Every reason the client needs a look, most important first."""

    issues: list[ClientHealthIssue] = []
    # A seasonal pause takes requests only by the owner's choice.
    is_paused: bool = (
        subscription is not None and subscription.status is SubscriptionStatus.PAUSED
    )
    if summary.service_mode is ServiceMode.LEADS_ONLY and not is_paused:
        issues.append(ClientHealthIssue.LEADS_ONLY_MODE)

    if is_losing_money(summary, subscription):
        issues.append(ClientHealthIssue.NEGATIVE_MARGIN)

    if subscription is None:
        issues.append(ClientHealthIssue.NO_SUBSCRIPTION)
    elif subscription.status is SubscriptionStatus.INCOMPLETE:
        issues.append(ClientHealthIssue.FIRST_PAYMENT_PENDING)
    elif subscription.status is SubscriptionStatus.PAST_DUE:
        issues.append(ClientHealthIssue.PAYMENT_PAST_DUE)
    elif subscription.status is SubscriptionStatus.CANCELLED:
        issues.append(ClientHealthIssue.SUBSCRIPTION_CANCELLED)

    if subscription is not None and summary.published_version_number is None:
        issues.append(ClientHealthIssue.NOT_PUBLISHED)

    # The active version's own verdict: a run that passed with a scenario
    # or two failed is a passed run, as on the version page.
    if summary.autotest_verdict is not None and not summary.autotest_verdict.is_passed:
        issues.append(ClientHealthIssue.AUTOTESTS_FAILED)

    if int(summary.tool_errors_last_7_days) > 0:
        issues.append(ClientHealthIssue.TOOL_ERRORS)

    if int(summary.handoffs_last_7_days) >= MANY_HANDOFFS_THRESHOLD:
        issues.append(ClientHealthIssue.MANY_HANDOFFS)

    if int(summary.open_unanswered_questions) >= OPEN_QUESTIONS_THRESHOLD:
        issues.append(ClientHealthIssue.OPEN_QUESTIONS)

    # Customers waited: one reply in twenty took over 15 s (last 7 days).
    if is_slow(summary.reply_speed):
        issues.append(ClientHealthIssue.SLOW_REPLIES)

    # The guard held back many replies, or many messages tried injection.
    if is_guard_spike(summary.guard_activity):
        issues.append(ClientHealthIssue.GUARD_SPIKE)

    is_minutes_exceeded: bool = int(summary.included_voice_minutes) > 0 and int(
        summary.used_voice_minutes
    ) > int(summary.included_voice_minutes)
    is_dialogs_exceeded: bool = int(summary.included_dialogs) > 0 and int(
        summary.used_dialogs
    ) > int(summary.included_dialogs)
    if is_minutes_exceeded or is_dialogs_exceeded:
        issues.append(ClientHealthIssue.PACKAGE_EXCEEDED)

    return issues


def judge_health(issues: list[ClientHealthIssue]) -> ClientHealthStatus:
    if any(issue in CRITICAL_ISSUES for issue in issues):
        return ClientHealthStatus.CRITICAL

    if issues != []:
        return ClientHealthStatus.ATTENTION

    return ClientHealthStatus.HEALTHY


def is_losing_money(
    summary: AdminClientSummary,
    subscription: SubscriptionDocument | None,
) -> bool:
    """
    A paying client whose provider costs exceed its revenue. A free trial
    (or no subscription yet) has no revenue by design: its cost is the
    price of the trial, not a loss to act on.
    """

    if subscription is None or subscription.status is SubscriptionStatus.TRIALING:
        return False

    margin = summary.cost.margin
    return margin is not None and int(margin.amount_minor) < 0
