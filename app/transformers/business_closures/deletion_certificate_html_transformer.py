from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.business_closures import DeprovisionOutcome
from app.schemas.domain.business_closures import (
    BusinessDeletionDocument,
    CollectionRowCount,
)
from app.schemas.dto.business_closures.deletion_certificates import (
    DeletionCertificateSource,
)
from app.schemas.typings.business_closures.strings import DeletionCertificateHtml
from app.transformers.business_closures import deletion_certificate_texts as texts
from app.transformers.business_closures.deletion_certificate_page import (
    DeletionCertificatePage,
)

AUDIT_TABLES: frozenset[str] = frozenset(
    {
        "audit_log_entries",
        "audit_chain_heads",
        "audit_chain_checkpoints",
        "audit_chain_statuses",
    }
)
# The cabinet's paper and graphite with its one clay accent (globals.css).
PAGE_STYLE: str = (
    "@page{size:A4;margin:22mm 20mm}"
    "body{font-family:'Noto Sans','Noto Sans Georgian','Noto Sans Hebrew',sans-serif;"
    "color:#24211d;font-size:10.5pt;line-height:1.5}"
    "h1{font-size:20pt;margin:0 0 4mm;color:#24211d;border-bottom:2px solid #ad5732;"
    "padding-bottom:3mm}h2{font-size:12pt;margin:7mm 0 2mm;color:#ad5732}"
    "table{border-collapse:collapse;width:100%}td{padding:1.2mm 0;vertical-align:top}"
    "td.label{color:#6b645c;width:42%}ul{margin:0;padding-inline-start:5mm}"
    ".digest{font-family:'Noto Sans Mono',monospace;font-size:8.5pt;"
    "word-break:break-all}"
    ".footer{margin-top:10mm;color:#6b645c;font-size:9pt}"
)


class DeletionCertificateHtmlTransformer(
    TransformerContract[DeletionCertificateSource, DeletionCertificateHtml]
):
    """
    The deletion certificate's page: who and what was deleted, when, what
    was switched off at the providers, what the sub-processors were asked
    to delete, what the law keeps (with counts, never contents) and the
    fingerprint of these facts. Self-contained (no image, font or link it
    would fetch), printed to PDF by the certificate renderer.
    """

    def __init__(self, localized_text_resolver: LocalizedTextResolverContract) -> None:
        self._resolver: LocalizedTextResolverContract = localized_text_resolver

    def transform(
        self, input_data: DeletionCertificateSource
    ) -> DeletionCertificateHtml:
        page = DeletionCertificatePage(self._resolver, input_data)
        entry: BusinessDeletionDocument = page.entry
        body: str = "".join(
            (
                f"<h1>{page.say(texts.TITLE)}</h1><p>{page.say(texts.INTRO)}</p>",
                facts_table(page, entry),
                deleted_section(page, entry),
                providers_section(page, entry),
                retained_section(page, entry),
                f"<p>{page.say(texts.BACKUPS)}</p>",
                f"<h2>{page.say(texts.DIGEST)}</h2>",
                f'<p class="digest">{page.value(entry.certificate_digest or "")}</p>',
                f'<p class="footer">{page.say(texts.FOOTER)}</p>',
            )
        )
        return DeletionCertificateHtml(
            f'<!doctype html><html lang="{page.value(page.language)}" '
            f'dir="{page.direction}"><head><meta charset="utf-8">'
            f"<title>{page.say(texts.TITLE)}</title><style>{PAGE_STYLE}</style>"
            f"</head><body>{body}</body></html>"
        )


def facts_table(page: DeletionCertificatePage, entry: BusinessDeletionDocument) -> str:
    rows: list[tuple[str, str]] = [
        (page.say(texts.BUSINESS), page.value(entry.business_name)),
        (page.say(texts.BUSINESS_ID), page.value(entry.deleted_business_id)),
        (page.say(texts.NUMBER), page.value(entry.id)),
        (
            page.say(texts.REQUESTED),
            f"{page.moment(entry.requested_at)}, "
            f"{page.say(texts.REASONS[entry.reason])}",
        ),
        (page.say(texts.STARTED), page.moment(entry.started_at)),
        (page.say(texts.COMPLETED), page.moment(entry.completed_at)),
    ]
    cells: str = "".join(
        f'<tr><td class="label">{label}</td><td>{value}</td></tr>'
        for label, value in rows
    )
    return f"<table>{cells}</table>"


def deleted_section(
    page: DeletionCertificatePage, entry: BusinessDeletionDocument
) -> str:
    rows: int = sum(int(item.row_count) for item in entry.erased_rows)
    items: list[str] = [
        page.say(texts.DELETED_ROWS, count=page.count(rows)),
        page.say(texts.DELETED_FILES, count=page.count(int(entry.erased_files or 0))),
        page.say(
            texts.PROCESSORS,
            count=page.count(int(entry.processor_erasure_jobs or 0)),
        ),
    ]
    listed: str = "".join(f"<li>{item}</li>" for item in items)
    return f"<h2>{page.say(texts.DELETED_HEADING)}</h2><ul>{listed}</ul>"


def providers_section(
    page: DeletionCertificatePage, entry: BusinessDeletionDocument
) -> str:
    cells: str = "".join(
        f'<tr><td class="label">{page.say(texts.TARGETS[record.target])}</td><td>'
        + (
            page.say(
                texts.OUTCOMES[record.outcome], count=page.count(int(record.item_count))
            )
            if record.outcome is DeprovisionOutcome.DONE
            else page.say(texts.OUTCOMES[record.outcome])
        )
        + "</td></tr>"
        for record in entry.deprovisioned
    )
    return f"<h2>{page.say(texts.PROVIDERS_HEADING)}</h2><table>{cells}</table>"


def retained_section(
    page: DeletionCertificatePage, entry: BusinessDeletionDocument
) -> str:
    audit: int = count_of(entry.retained_rows, AUDIT_TABLES, among=True)
    billing: int = count_of(entry.retained_rows, AUDIT_TABLES, among=False)
    items: str = (
        f"<li>{page.say(texts.RETAINED_AUDIT, count=page.count(audit))}</li>"
        f"<li>{page.say(texts.RETAINED_BILLING, count=page.count(billing))}</li>"
    )
    return f"<h2>{page.say(texts.RETAINED_HEADING)}</h2><ul>{items}</ul>"


def count_of(
    rows: list[CollectionRowCount], tables: frozenset[str], *, among: bool
) -> int:
    return sum(
        int(item.row_count)
        for item in rows
        if (str(item.collection) in tables) is among
    )
