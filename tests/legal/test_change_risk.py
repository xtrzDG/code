"""
The change risk classes (docs/security/change-risk.md) and the pull request
template agree: every path the code owners must approve is HIGH, every
path the classes name exists, and the template asks for the risk class,
the six questions of the differential review, the regenerated entry-point
inventory and the cabinet's languages as they are today; a pull request
the `risk:high` label marks (.github/labeler.yml) is HIGH.
"""

import re
from typing import cast

import yaml

from app.schemas.constants.localization import CABINET_LANGUAGES
from tests.legal.governance_documents import (
    OPERATIONS,
    missing_paths,
    read,
    section,
)

CHANGE_RISK: str = "docs/security/change-risk.md"
TEMPLATE: str = ".github/pull_request_template.md"
REVIEW_QUESTIONS: tuple[str, ...] = (
    "Entry points",
    "Authorization",
    "Data",
    "Secrets",
    "Failure",
    "Rollback",
)
LANGUAGE_NAMES: dict[str, str] = {"en": "English", "it": "Italian"}
RISK_LABEL: str = "risk:high"
LABELER: str = ".github/labeler.yml"


def code_owner_paths() -> list[str]:
    """The paths of .github/CODEOWNERS, without their leading slash."""

    return [
        line.split()[0].lstrip("/")
        for line in read(".github/CODEOWNERS").splitlines()
        if line.startswith("/")
    ]


def test_every_code_owner_path_is_a_high_risk_path() -> None:
    high = section(read(CHANGE_RISK), "Classes").split("**MEDIUM**")[0]
    paths = code_owner_paths()

    assert len(paths) >= 15
    assert [path for path in paths if f"`{path}`" not in high] == []


def test_a_pull_request_with_the_risk_label_is_high() -> None:
    labels = cast(dict[str, object], yaml.safe_load(read(LABELER)))
    high = section(read(CHANGE_RISK), "Classes").split("**MEDIUM**")[0]

    assert RISK_LABEL in labels
    assert f"`{RISK_LABEL}`" in high and f"`{LABELER}`" in high
    assert f"`{RISK_LABEL}`" in section(read(TEMPLATE), "Risk")


def test_the_classes_name_only_paths_that_exist() -> None:
    assert missing_paths(read(CHANGE_RISK), OPERATIONS) == []


def test_the_template_asks_for_the_risk_and_the_differential_review() -> None:
    template = read(TEMPLATE)
    review = section(template, "Differential review (HIGH only)")
    questions = re.findall(r"^\d\. \*\*([A-Za-z ]+)\*\*", read(CHANGE_RISK), re.M)

    assert "## Risk" in template and "Risk: " in template
    assert "docs/security/change-risk.md" in template
    assert questions == list(REVIEW_QUESTIONS)
    for question in REVIEW_QUESTIONS:
        assert f"**{question}:**" in review, question
    assert "uv run python -m scripts.entry_point_inventory" in template


def test_the_template_names_the_cabinet_languages() -> None:
    template = read(TEMPLATE)
    names = [LANGUAGE_NAMES[str(language.value)] for language in CABINET_LANGUAGES]

    assert all(name in template for name in names)
    assert re.search(r"\b(ru|ka|Russian|Georgian)\b", template) is None
