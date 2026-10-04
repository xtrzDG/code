"""
Every message to a customer goes through the outbox: it is stored with an
idempotency key, sent by the worker with retries, and has a delivery state.

So no use case calls a channel's `send` or a WhatsApp template's
`send_template` (the sending contracts of `app/contracts/channels.py`)
itself: it queues an `OutboundMessageDocument` instead. Only the outbox
(`app/use_cases/channels/outbox/`) sends, and the channel connection
checks (`app/use_cases/channels/connection/`) may try a credential.
"""

import ast
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
USE_CASES_ROOT: Path = PROJECT_ROOT / "app" / "use_cases"
ALLOWED_PACKAGES: tuple[Path, ...] = (
    USE_CASES_ROOT / "channels" / "outbox",
    USE_CASES_ROOT / "channels" / "connection",
)
SENDER_CONTRACTS: frozenset[str] = frozenset(
    {"ChannelAdapterContract", "WhatsAppTemplateAdapterContract"}
)
SEND_METHODS: frozenset[str] = frozenset({"send", "send_template"})


def find_direct_sends(source: str) -> list[int]:
    """
    Lines of `source` that call `send` or `send_template` in a module that
    depends on a channel sending contract (imports it by name).
    """

    tree: ast.Module = ast.parse(source)
    imported: set[str] = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.name in SENDER_CONTRACTS
    }
    if not imported:
        return []

    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in SEND_METHODS
    )


def is_allowed(path: Path) -> bool:
    return any(path.is_relative_to(package) for package in ALLOWED_PACKAGES)


def test_no_use_case_sends_to_a_channel_outside_the_outbox() -> None:
    violations: list[str] = []
    for path in sorted(USE_CASES_ROOT.rglob("*.py")):
        if is_allowed(path):
            continue

        for line in find_direct_sends(path.read_text(encoding="utf-8")):
            violations.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}:{line}")

    assert violations == [], (
        "A use case sends to a customer's channel directly, without retries, "
        "idempotency or a delivery state. Queue an OutboundMessageDocument "
        "with `queue_outbound_message` (app/use_cases/shared/outbox_queue.py) "
        "and let the outbox send it. Direct sends: " + ", ".join(violations)
    )


def test_the_outbox_itself_is_where_channels_are_sent_to() -> None:
    """The policy looks at the right code: the outbox does send."""

    outbox_sends: list[int] = []
    for path in sorted(ALLOWED_PACKAGES[0].rglob("*.py")):
        outbox_sends.extend(find_direct_sends(path.read_text(encoding="utf-8")))

    assert outbox_sends != []


def test_a_direct_send_is_found() -> None:
    source = (
        "from app.contracts.channels import ChannelAdapterContract\n"
        "class Reminder:\n"
        "    def __init__(self, adapter: ChannelAdapterContract) -> None:\n"
        "        self._adapter = adapter\n"
        "    def run(self, target, text) -> None:\n"
        "        self._adapter.send(target, text)\n"
    )

    assert find_direct_sends(source) == [6]


def test_a_template_sent_through_an_alias_is_found() -> None:
    source = (
        "from app.contracts.channels import (\n"
        "    WhatsAppTemplateAdapterContract as Templates,\n"
        ")\n"
        "def remind(templates: Templates) -> None:\n"
        "    templates.send_template('id', 'user', 'name', 'en', [])\n"
    )

    assert find_direct_sends(source) == [5]


def test_parsing_a_webhook_is_not_sending() -> None:
    source = (
        "from app.contracts.channels import ChannelAdapterContract\n"
        "def receive(adapter: ChannelAdapterContract, body: bytes) -> object:\n"
        "    return adapter.parse_webhook(body)\n"
    )

    assert find_direct_sends(source) == []
