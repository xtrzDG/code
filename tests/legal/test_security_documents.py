"""
The security documents stay true: every code and test path the threat
model names exists, and the cabinet's security.txt (RFC 9116) is complete
and renewed before it expires.
"""

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPOSITORY: Path = Path(__file__).resolve().parents[2]
THREAT_MODEL: Path = REPOSITORY / "docs" / "security" / "threat-model.md"
ACCESS_REVIEW: Path = REPOSITORY / "docs" / "security" / "access-review.md"
SECURITY_TXT: Path = REPOSITORY / "web" / "public" / ".well-known" / "security.txt"
# A path in backticks: a folder ("app/use_cases/tools/") or a file.
PATH_PATTERN: re.Pattern[str] = re.compile(r"`((?:[\w.-]+/)+[\w.-]*)`")
RENEW_AHEAD: timedelta = timedelta(days=30)
LONGEST_VALIDITY: timedelta = timedelta(days=366)


def test_every_path_in_the_threat_model_exists() -> None:
    text = THREAT_MODEL.read_text(encoding="utf-8")
    paths = set(PATH_PATTERN.findall(text))

    assert len(paths) > 40
    missing = sorted(path for path in paths if not (REPOSITORY / path).exists())
    assert missing == [], f"The threat model names paths that moved: {missing}"


def test_every_stride_row_names_its_code_and_its_tests() -> None:
    rows = [
        line
        for line in THREAT_MODEL.read_text(encoding="utf-8").splitlines()
        if re.match(r"^\| [0-9]+ \|", line)
    ]

    assert len(rows) >= 15
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        stride, code, tests = cells[2], cells[5], cells[6]
        assert set(stride.replace(",", "").split()) <= set("STRIDE"), row
        assert "`" in code and "test" in tests, row


def test_the_access_review_is_linked_from_the_threat_model() -> None:
    assert "docs/security/access-review.md" in THREAT_MODEL.read_text("utf-8")
    assert "- [ ]" in ACCESS_REVIEW.read_text(encoding="utf-8")


def security_fields() -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for line in SECURITY_TXT.read_text(encoding="utf-8").splitlines():
        if line.strip() == "" or line.startswith("#"):
            continue
        name, _, value = line.partition(":")
        fields.setdefault(name.strip().lower(), []).append(value.strip())
    return fields


def test_security_txt_names_a_contact_and_a_policy() -> None:
    fields = security_fields()

    assert fields["contact"], "RFC 9116 requires at least one Contact"
    assert all(
        contact.startswith(("https://", "mailto:")) for contact in fields["contact"]
    )
    assert all(url.startswith("https://") for url in fields.get("policy", []))
    assert "[" not in SECURITY_TXT.read_text(encoding="utf-8")


def test_security_txt_is_renewed_before_it_expires() -> None:
    (expires_text,) = security_fields()["expires"]
    expires = datetime.fromisoformat(expires_text.replace("Z", "+00:00"))
    now = datetime.now(UTC)

    assert expires.tzinfo is not None
    assert expires - now > RENEW_AHEAD, (
        "security.txt expires within 30 days: set a new Expires (at most a "
        "year ahead) in web/public/.well-known/security.txt"
    )
    assert expires - now <= LONGEST_VALIDITY, "RFC 9116: at most a year ahead"
