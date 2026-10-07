"""
What the public /privacy, /terms, /dpa, /security and /contact pages read:
the security overview as a legal text, every text marked as a draft until
the operator sets LEGAL_TEXTS_FINAL (and fills every field), and
GET /v1/legal/overview with the DPA in force and the operator's details.
"""

from pathlib import Path

from app.utilities.config_helpers.app_settings.compliance_settings_section import (
    DEFAULT_DPA_DOCUMENT_VERSION,
)
from tests.legal.legal_http import build_legal_client
from tests.legal.legal_world import Clock

SELLER: dict[str, str] = {
    "SELLER_LEGAL_NAME": "Workshop Labs LLC",
    "SELLER_ADDRESS": "1 Rustaveli Ave, Tbilisi",
    "SELLER_EMAIL": "legal@workshop.example",
    "SELLER_TAX_ID": "405123456",
}


def test_the_security_overview_is_published_in_three_languages() -> None:
    client = build_legal_client(Clock("2026-10-05"))

    english = client.get("/v1/legal/security").json()
    georgian = client.get("/v1/legal/security", params={"language": "ka"}).json()

    assert english["kind"] == "security"
    assert english["version"] == "2026-10-05"
    assert english["available_languages"] == ["en", "ka", "ru"]
    assert english["title"] == "Security at Assistant Workshop"
    assert english["has_placeholders"] is False
    assert georgian["language"] == "ka"


def test_every_text_is_a_draft_until_the_operator_declares_them_final(
    tmp_path: Path,
) -> None:
    draft = build_legal_client(Clock("2026-10-05"))
    final = build_legal_client(
        Clock("2026-10-05"), environment={"LEGAL_TEXTS_FINAL": "true"}
    )

    assert draft.get("/v1/legal/security").json()["is_draft"] is True
    assert final.get("/v1/legal/security").json()["is_draft"] is False
    # A text with fields still in brackets stays a draft whatever is declared.
    assert final.get("/v1/legal/terms").json()["is_draft"] is True

    (tmp_path / "terms-2026-10-05.en.md").write_text(
        "# Terms\n\nVersion 2026-10-05\n\nFilled in.", "utf-8"
    )
    filled = build_legal_client(
        Clock("2026-10-05"),
        documents=tmp_path,
        environment={"LEGAL_TEXTS_FINAL": "true"},
    )
    assert filled.get("/v1/legal/terms").json()["is_draft"] is False


def test_the_overview_names_the_dpa_in_force_and_the_operator() -> None:
    client = build_legal_client(
        Clock("2026-10-05"), environment={**SELLER, "LEGAL_TEXTS_FINAL": "true"}
    )

    response = client.get("/v1/legal/overview")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=300"
    body = response.json()
    assert body["is_draft"] is False
    # The version in force is the deployment's DPA_DOCUMENT_VERSION (default).
    assert body["dpa_version"] == DEFAULT_DPA_DOCUMENT_VERSION
    assert body["operator"] == {
        "legal_name": "Workshop Labs LLC",
        "address": "1 Rustaveli Ave, Tbilisi",
        "email": "legal@workshop.example",
        "tax_id": "405123456",
        "country_code": "GE",
    }


def test_an_operator_without_details_is_named_by_default_only() -> None:
    body = build_legal_client(Clock("2026-10-05")).get("/v1/legal/overview").json()

    assert body["is_draft"] is True
    assert body["operator"]["legal_name"] == "Assistant Workshop"
    assert body["operator"]["email"] is None
    assert body["operator"]["address"] is None
