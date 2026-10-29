"""
The HTML of an invoice or receipt page for the PDF engine: A4, Noto fonts
(Latin, Cyrillic and Georgian), the brand accent, and every value escaped
(`dir="auto"` keeps right-to-left names readable). No external resource is
referenced, so the engine fetches nothing.
"""

from html import escape

from app.transformers.invoicing.billing_document_sheet import (
    BillingDocumentSheet,
    SheetParty,
    SheetRow,
)

STYLE: str = """
@page { size: A4; margin: 18mm 16mm 20mm; }
* { box-sizing: border-box; }
body { font-family: "Noto Sans", "Noto Sans Georgian", "DejaVu Sans", sans-serif;
  font-size: 9.5pt; line-height: 1.45; color: #111827; margin: 0; }
header { display: flex; justify-content: space-between; align-items: flex-start;
  border-bottom: 2pt solid #7c5cff; padding-bottom: 10pt; margin-bottom: 16pt; }
h1 { font-size: 20pt; margin: 0 0 2pt; letter-spacing: -0.2pt; }
.number { font-size: 11pt; color: #4b5563; margin: 0; }
.status { display: inline-block; margin-top: 6pt; padding: 2pt 8pt;
  border-radius: 10pt; background: #ede9fe; color: #4c1d95; font-weight: 600; }
header > div:first-child { flex: 1; }
.brand { max-width: 42%; text-align: right; font-weight: 700; font-size: 11pt;
  color: #7c5cff; }
.facts { width: 100%; border-collapse: collapse; margin-bottom: 14pt; }
.facts td { padding: 2pt 0; vertical-align: top; }
.facts td.label { color: #6b7280; width: 38%; }
.parties { display: flex; gap: 18pt; margin-bottom: 18pt; }
.party { flex: 1; border: 0.75pt solid #e5e7eb; border-radius: 6pt; padding: 9pt 11pt; }
.party h2 { font-size: 8.5pt; font-weight: 600; color: #6b7280; margin: 0 0 4pt; }
.party .name { font-weight: 700; font-size: 10.5pt; margin: 0 0 3pt; }
.party p { margin: 0; white-space: pre-line; }
table.lines { width: 100%; border-collapse: collapse; margin-bottom: 10pt; }
table.lines th { text-align: left; font-size: 8.5pt; font-weight: 600;
  color: #6b7280; border-bottom: 0.75pt solid #d1d5db; padding: 5pt 4pt; }
table.lines td { padding: 7pt 4pt; border-bottom: 0.75pt solid #f3f4f6;
  vertical-align: top; }
table.lines .amount, table.lines .period { text-align: right; white-space: nowrap; }
table.totals { margin-left: auto; border-collapse: collapse; min-width: 52%; }
table.totals td { padding: 3pt 4pt; }
table.totals td.value { text-align: right; white-space: nowrap; }
table.totals tr.grand td { font-weight: 700; font-size: 11pt;
  border-top: 1pt solid #111827; padding-top: 6pt; }
.notes { margin-top: 18pt; color: #374151; }
.notes p { margin: 0 0 4pt; }
footer { margin-top: 28pt; font-size: 8pt; color: #9ca3af; }
"""


def render_billing_document_html(sheet: BillingDocumentSheet) -> str:
    status: str = (
        "" if sheet.status is None else f'<span class="status">{e(sheet.status)}</span>'
    )
    return (
        f'<!doctype html><html lang="{e(sheet.language)}"><head><meta charset="utf-8">'
        f"<title>{e(sheet.title)} {e(sheet.number)}</title><style>{STYLE}</style>"
        "</head><body><header><div>"
        f"<h1>{e(sheet.title)}</h1>"
        f'<p class="number">{e(sheet.number)}</p>{status}</div>'
        f'<div class="brand" dir="auto">{e(sheet.seller.name)}</div></header>'
        f'<table class="facts">{render_rows(sheet.facts, "label", "")}</table>'
        f'<div class="parties">{render_party(sheet.seller)}'
        f"{render_party(sheet.buyer)}</div>"
        '<table class="lines"><thead><tr>'
        f"<th>{e(sheet.columns.description)}</th>"
        f'<th class="period">{e(sheet.columns.period)}</th>'
        f'<th class="amount">{e(sheet.columns.amount)}</th></tr></thead><tbody>'
        + "".join(
            f'<tr><td dir="auto">{e(line.description)}</td>'
            f'<td class="period">{e(line.period)}</td>'
            f'<td class="amount">{e(line.amount)}</td></tr>'
            for line in sheet.lines
        )
        + "</tbody></table>"
        f'<table class="totals">{render_rows(sheet.totals, "", "value")}'
        f'<tr class="grand"><td>{e(sheet.grand_total.label)}</td>'
        f'<td class="value">{e(sheet.grand_total.value)}</td></tr></table>'
        '<div class="notes">'
        + "".join(f"<p>{e(note)}</p>" for note in sheet.notes)
        + f'</div><footer dir="auto">{e(sheet.footer)}</footer></body></html>'
    )


def render_party(party: SheetParty) -> str:
    return (
        f'<section class="party"><h2>{e(party.heading)}</h2>'
        f'<p class="name" dir="auto">{e(party.name)}</p>'
        + "".join(f'<p dir="auto">{e(line)}</p>' for line in party.lines)
        + "</section>"
    )


def render_rows(rows: list[SheetRow], label_class: str, value_class: str) -> str:
    return "".join(
        f'<tr><td class="{label_class}">{e(row.label)}</td>'
        f'<td class="{value_class}" dir="auto">{e(row.value)}</td></tr>'
        for row in rows
    )


def e(text: str) -> str:
    """Escaped for HTML text and attribute values."""

    return escape(text, quote=True)
