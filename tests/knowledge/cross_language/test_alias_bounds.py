"""
A long alias list costs no more than reading it once: the request refuses
more than `MAX_ALIASES_PER_ITEM` aliases before any check runs, and the
check stops at the first language with one alias too many.
"""

from collections.abc import Iterator, Sequence
from typing import overload

import pytest
from pydantic import ValidationError

from app.schemas.constants.knowledge import (
    MAX_ALIASES_PER_ITEM,
    MAX_ALIASES_PER_LANGUAGE,
    KnowledgeAliasStatus,
    KnowledgeItemKind,
)
from app.schemas.domain.knowledge import KnowledgeAlias
from app.schemas.dto.knowledge_admin import KnowledgeItemInput, KnowledgeItemPatch
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAliasText
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.aliases.alias_rules import check_aliases
from tests.knowledge.routes_fixture import OWNER, build_fixture


class CountingAliases(Sequence[KnowledgeAlias]):
    """A list of aliases that counts how many of them were read."""

    def __init__(self, aliases: list[KnowledgeAlias]) -> None:
        self.aliases = aliases
        self.read = 0

    def __iter__(self) -> Iterator[KnowledgeAlias]:
        for alias in self.aliases:
            self.read += 1
            yield alias

    def __len__(self) -> int:
        return len(self.aliases)

    @overload
    def __getitem__(self, index: int) -> KnowledgeAlias: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[KnowledgeAlias]: ...

    def __getitem__(
        self, index: int | slice
    ) -> KnowledgeAlias | Sequence[KnowledgeAlias]:
        return self.aliases[index]


def many_aliases(count: int) -> list[KnowledgeAlias]:
    return [
        KnowledgeAlias(
            language=LanguageTag("en"),
            text=KnowledgeAliasText(f"Parking number {number}"),
            status=KnowledgeAliasStatus.APPROVED,
        )
        for number in range(count)
    ]


def test_the_check_stops_at_the_first_alias_too_many_in_a_language() -> None:
    aliases = CountingAliases(many_aliases(5000))

    with pytest.raises(ValidationFailedError, match="At most 3"):
        check_aliases(aliases, [LanguageTag("en")])

    assert aliases.read == MAX_ALIASES_PER_LANGUAGE + 1


def test_a_request_with_more_aliases_than_an_item_may_have_is_refused() -> None:
    too_many = many_aliases(MAX_ALIASES_PER_ITEM + 1)

    with pytest.raises(ValidationError):
        KnowledgeItemInput(
            kind=KnowledgeItemKind.FAQ,
            title=KnowledgeTitle("Do you have parking?"),
            aliases=too_many,
        )
    with pytest.raises(ValidationError):
        KnowledgeItemPatch(aliases=too_many)


def test_the_api_refuses_a_long_alias_list_with_422() -> None:
    fixture = build_fixture()
    aliases = [
        {"language": "en", "text": f"Parking number {number}"}
        for number in range(MAX_ALIASES_PER_ITEM + 1)
    ]

    created = fixture.client.post(
        f"{fixture.base}/knowledge",
        json={"kind": "faq", "title": "Parking", "aliases": aliases},
        headers=OWNER,
    )

    assert created.status_code == 422
