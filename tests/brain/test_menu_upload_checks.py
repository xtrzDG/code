"""
An uploaded menu is what its type says, by its first bytes: an HTML page
renamed to menu.pdf or menu.png is refused (422) before a model reads it,
HTML is not an upload type, and a text file must be UTF-8 text, not
markup. A web page still comes in by its link.
"""

import base64

import pytest

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.menu_import.constrained_strings import (
    MenuSourceBase64,
    MenuSourceMediaType,
)
from app.use_cases.menu_import.menu_upload_checks import check_menu_upload
from tests.brain.brain_world import build_world
from tests.brain.cabinet_http import bearer, build_cabinet_client
from tests.brain.menu_extraction_helpers import PNG_BYTES
from tests.brain.scripted_turns import scripted
from tests.brain.test_menu_import_drafts import FakeMenuExtractor, extracted

HTML_PAGE: bytes = b"<!DOCTYPE html><html><script>alert(1)</script></html>"
JPEG_BYTES: bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00" + b"\x00" * 64
PDF_BYTES: bytes = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
GIF_BYTES: bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00" + b"\x00" * 32
WEBP_BYTES: bytes = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32


def check(media_type: str, content: bytes) -> None:
    check_menu_upload(
        MenuSourceMediaType(media_type),
        MenuSourceBase64(base64.b64encode(content).decode("ascii")),
    )


@pytest.mark.parametrize(
    ("media_type", "content"),
    [
        ("image/png", PNG_BYTES),
        ("image/jpeg", JPEG_BYTES),
        ("image/gif", GIF_BYTES),
        ("image/webp", WEBP_BYTES),
        ("application/pdf", PDF_BYTES),
        ("text/plain", "Khachapuri 18,50 ₾\nLemonade 5".encode()),
        ("text/csv", b"\xef\xbb\xbftitle,price\nTea,3\n"),
        ("text/plain", b"Prices < 10 EUR: espresso, tea"),
    ],
)
def test_files_that_are_what_they_say_pass(media_type: str, content: bytes) -> None:
    check(media_type, content)


@pytest.mark.parametrize(
    ("media_type", "content"),
    [
        ("application/pdf", HTML_PAGE),
        ("image/png", HTML_PAGE),
        ("image/jpeg", PNG_BYTES),
        ("image/png", PDF_BYTES),
        ("application/pdf", b"<svg onload=alert(1)>"),
        ("text/plain", HTML_PAGE),
        ("text/plain", b"  <svg xmlns='http://www.w3.org/2000/svg'/>"),
        ("text/csv", b"\xef\xbb\xbf<html><body>menu</body></html>"),
        ("text/plain", b"Tea\x00\x01binary"),
        ("text/plain", PNG_BYTES),
    ],
)
def test_a_file_whose_bytes_contradict_its_type_is_refused(
    media_type: str, content: bytes
) -> None:
    with pytest.raises(ValidationFailedError, match="does not match its type"):
        check(media_type, content)


@pytest.mark.parametrize("media_type", ["text/html", "image/svg+xml", "video/mp4"])
def test_html_svg_and_other_types_are_not_menu_uploads(media_type: str) -> None:
    with pytest.raises(ValidationFailedError, match="must be a JPEG"):
        check(media_type, b"<html></html>")


def test_text_in_another_encoding_is_refused_with_a_reason() -> None:
    with pytest.raises(ValidationFailedError, match="UTF-8"):
        check("text/plain", "Caffè 1,20 €".encode("cp1252"))

    with pytest.raises(ValidationFailedError, match="not valid base64"):
        check_menu_upload(
            MenuSourceMediaType("image/png"), MenuSourceBase64("not base64!!")
        )


def test_the_api_refuses_a_renamed_page_and_reads_nothing() -> None:
    world = build_world(scripted())
    extractor = FakeMenuExtractor([extracted("Tea", "3", None)])
    client = build_cabinet_client(world, extractor, {"owner": world.owner_id})
    url = f"/v1/businesses/{world.business.id}/knowledge/import"
    page = base64.b64encode(HTML_PAGE).decode("ascii")

    renamed = client.post(
        url,
        json={"media_type": "application/pdf", "data_base64": page},
        headers=bearer("owner"),
    )
    html_upload = client.post(
        url,
        json={"media_type": "text/html", "data_base64": page},
        headers=bearer("owner"),
    )
    link = client.post(
        url,
        json={"media_type": "text/html", "url": "https://cafe.example/menu"},
        headers=bearer("owner"),
    )

    assert (renamed.status_code, html_upload.status_code) == (422, 422)
    assert link.status_code == 201
    assert [str(request.url) for request in extractor.requests] == [
        "https://cafe.example/menu"
    ]
