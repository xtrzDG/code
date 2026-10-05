"""
The cabinet's lists, the conversation card, the dashboard and the admin
client summaries never load a business's whole history.

They read one keyset page (`page_by`) or let the database count
(`count_by`). `take_page` pages a list that is already in memory, and
`list_by_business` of the growing collections reads every row a business
ever had: neither may come back into these use cases. Small, bounded
reads (the business's resources, its schedule exceptions, its assistant
versions) stay allowed.
"""

import ast
from pathlib import Path

APP_DIRECTORY: Path = Path(__file__).resolve().parents[2] / "app"
KEYSET_USE_CASES: tuple[str, ...] = (
    "use_cases/conversations/list_conversations_use_case.py",
    "use_cases/conversations/get_conversation_use_case.py",
    "use_cases/conversations/rate_conversation_use_case.py",
    "use_cases/conversations/card/list_conversation_messages_use_case.py",
    "use_cases/conversations/card/conversation_links.py",
    "use_cases/conversations/feed/conversation_rows.py",
    "use_cases/conversations/feed/feed_search_scan.py",
    "use_cases/bookings/list_bookings_use_case.py",
    "use_cases/bookings/check_availability_use_case.py",
    "use_cases/leads/list_leads_use_case.py",
    "use_cases/handoffs/list_handoffs_use_case.py",
    "use_cases/handoffs/handoff_queue_paging.py",
    "use_cases/handoffs/list_unanswered_questions_use_case.py",
    "use_cases/compliance/list_audit_log_use_case.py",
    "use_cases/contacts/list_contacts_use_case.py",
    "use_cases/contacts/contact_list_search.py",
    "use_cases/contacts/get_contact_use_case.py",
    "use_cases/knowledge/list_knowledge_items_use_case.py",
    "use_cases/insights/get_dashboard_stats_use_case.py",
    "use_cases/admin/summarize_client_use_case.py",
    "use_cases/billing/compute_client_cost_use_case.py",
)
# Collections that grow with every customer message, booking or view.
GROWING_REPOSITORIES: frozenset[str] = frozenset(
    {
        "_conversation_repo",
        "_message_repo",
        "_contact_repo",
        "_booking_repo",
        "_lead_repo",
        "_handoff_repo",
        "_unanswered_question_repo",
        "_audit_log_repo",
        "_call_repo",
        "conversation_repo",
        "message_repo",
        "contact_repo",
        "booking_repo",
        "lead_repo",
        "handoff_repo",
        "call_repo",
    }
)
FORBIDDEN_NAMES: frozenset[str] = frozenset({"take_page", "take_ordered_page"})


def find_full_loads(source: str) -> list[str]:
    """Every whole-history read and in-memory paging call in a module."""

    findings: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            findings.append(node.id)
        elif (
            isinstance(node, ast.Attribute)
            and node.attr == "list_by_business"
            and repository_name(node.value) in GROWING_REPOSITORIES
        ):
            findings.append(f"{repository_name(node.value)}.list_by_business")

    return findings


def repository_name(node: ast.expr) -> str:
    if isinstance(node, ast.Attribute):
        return node.attr

    if isinstance(node, ast.Name):
        return node.id

    return ""


def test_lists_dashboards_and_cards_read_pages_and_counts_only() -> None:
    offenders: dict[str, list[str]] = {}
    for relative_path in KEYSET_USE_CASES:
        source: str = (APP_DIRECTORY / relative_path).read_text(encoding="utf-8")
        findings: list[str] = find_full_loads(source)
        if findings:
            offenders[relative_path] = findings

    assert offenders == {}, (
        "These use cases must read keyset pages (page_by) or database counts "
        f"(count_by), never a whole business: {offenders}"
    )


def test_the_policy_catches_a_full_load() -> None:
    source = (
        "def run(self):\n"
        "    rows = self._message_repo.list_by_business(business_id)\n"
        "    resources = self._resource_repo.list_by_business(business_id)\n"
        "    return take_page(rows, page, key, item)\n"
    )

    assert find_full_loads(source) == ["_message_repo.list_by_business", "take_page"]
