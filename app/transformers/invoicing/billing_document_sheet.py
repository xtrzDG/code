"""
A laid-out invoice or receipt before it becomes HTML: every text already
in the document's language, every amount and date already formatted. The
HTML (`billing_document_html.py`) only places and escapes them.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SheetRow:
    """A label and its value (a fact under the title, a total)."""

    label: str
    value: str


@dataclass(frozen=True)
class SheetParty:
    """The seller or the buyer: a heading, the name and the detail lines."""

    heading: str
    name: str
    lines: list[str] = field(default_factory=list[str])


@dataclass(frozen=True)
class SheetLine:
    """One line of the table: what was sold, for which period, for how much."""

    description: str
    period: str
    amount: str


@dataclass(frozen=True)
class BillingDocumentSheet:
    """Everything one invoice or receipt page shows, in reading order."""

    language: str
    title: str
    number: str
    status: str | None
    facts: list[SheetRow]
    seller: SheetParty
    buyer: SheetParty
    columns: SheetLine
    lines: list[SheetLine]
    totals: list[SheetRow]
    grand_total: SheetRow
    notes: list[str]
    footer: str
