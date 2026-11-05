"""
Owner-editable texts render literally in the API's own renderers: a CSV
export writes template syntax as it was typed and defuses formulas, a
download's name can never carry a header break or a quote, and the
widget's greeting puts the business name in as text.
"""

import json
import shutil
from collections.abc import Callable

import pytest
from base_typed_string import BaseTypedStringConstraintViolationError

from app.gateways.http.billing_document_routes import (
    attachment_disposition as document_disposition,
)
from app.gateways.http.csv_streaming import attachment_disposition, stream_csv
from app.schemas.dto.privacy.csv_exports import CsvExportHeader, CsvExportPage, CsvRow
from app.schemas.typings.bookings.constrained_strings import BookingCalendarFileName
from app.schemas.typings.invoicing.constrained_strings import BillingDocumentFileName
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.privacy.constrained_strings import ExportFileName
from app.schemas.typings.privacy.strings import CsvCellText, CsvColumnTitle
from tests.channels.widget_node_runner import run_in_node
from tests.channels.widget_script_source import SCRIPT_SOURCE

TEMPLATE_PAYLOADS: tuple[str, ...] = (
    "{{7*7}}",
    "${7*7}",
    "<%= 7*7 %>",
    "#{7*7}",
    "%(name)s",
    "{business}",
    "$& $` $'",
    "{{constructor.constructor('alert(1)')()}}",
)
HEADER_PAYLOADS: tuple[str, ...] = (
    'menu".csv',
    "menu.csv\r\nSet-Cookie: session=stolen",
    "menu.csv\nX-Injected: 1",
    "menu;filename=evil.csv",
    "../../etc/passwd.csv",
    "mеnu.csv",  # a Cyrillic "е"
)


def exported(cells: list[str]) -> str:
    header = CsvExportHeader(
        file_name=ExportFileName("customers-2026-11-02.csv"),
        columns=[CsvColumnTitle("Name"), CsvColumnTitle("Note")],
    )

    def read_page(cursor: PageCursor | None) -> CsvExportPage:
        assert cursor is None
        return CsvExportPage(rows=[CsvRow(cells=[CsvCellText(c) for c in cells])])

    return b"".join(stream_csv(header, read_page)).decode("utf-8")


@pytest.mark.parametrize("payload", TEMPLATE_PAYLOADS)
def test_template_syntax_in_an_export_is_written_as_typed(payload: str) -> None:
    text = exported([f"Trattoria {payload}", payload])

    assert f"Trattoria {payload}" in text
    assert "49" not in text


def test_formulas_typed_by_owners_stay_text() -> None:
    text = exported(['=HYPERLINK("https://evil.example")', "+1-2"])

    assert "'=HYPERLINK" in text
    assert "'+1-2" in text


@pytest.mark.parametrize("payload", HEADER_PAYLOADS)
@pytest.mark.parametrize(
    "file_name_type",
    [ExportFileName, BillingDocumentFileName, BookingCalendarFileName],
)
def test_a_download_name_cannot_break_its_header(
    payload: str, file_name_type: Callable[[str], object]
) -> None:
    with pytest.raises(BaseTypedStringConstraintViolationError):
        file_name_type(payload)


def test_a_valid_download_name_is_one_quoted_header_value() -> None:
    export = attachment_disposition(str(ExportFileName("bookings-2026-11-02.csv")))
    document = document_disposition(
        str(BillingDocumentFileName("invoice-AW-2026-000042.pdf"))
    )

    assert export == 'attachment; filename="bookings-2026-11-02.csv"'
    assert document.startswith('attachment; filename="invoice-AW-2026-000042.pdf"; ')
    for value in (export, document):
        assert "\r" not in value and "\n" not in value


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
@pytest.mark.parametrize("payload", TEMPLATE_PAYLOADS)
def test_the_widget_greeting_takes_the_business_name_as_text(payload: str) -> None:
    expression: str = (
        'text("greeting").split("{business}").join(config.business_name || "")'
    )
    assert expression in SCRIPT_SOURCE
    name: str = f"Pizza {payload}"
    program: str = (
        "function text() { return 'Ciao! Sono l’assistente di {business}.'; }"
        f"\nvar config = {{ business_name: {json.dumps(name)} }};"
        f"\nconsole.log(JSON.stringify({expression}));"
    )

    assert run_in_node(program) == f"Ciao! Sono l’assistente di {name}."
