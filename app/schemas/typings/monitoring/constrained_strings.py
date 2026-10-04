"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class AlertChatId(BaseConstrainedTypedString):
    """
    A Telegram chat the platform bot posts platform alerts to
    (PLATFORM_ALERT_TELEGRAM_CHAT_IDS): a person's chat id, or a group's
    (negative, `-100…` for a supergroup). The bot must be a member.

    Example:
        chat_id = AlertChatId("-1001234567890")
    """

    min_length = 1
    max_length = 21
    pattern = r"^-?[1-9][0-9]{0,19}\Z"


class AlertRunbookPath(BaseConstrainedTypedString):
    """
    The runbook a platform alert points the team to: a Markdown file of the
    repository under docs/operations/.

    Example:
        runbook = AlertRunbookPath("docs/operations/runbooks/stuck-worker.md")
    """

    min_length = 20
    max_length = 160
    pattern = r"^docs/operations/[a-z0-9/-]+\.md\Z"


# Keep abc order for all non example types, if possible.
