"""
The niche template editor never changes an assembled prompt by itself.

Without a published override the effective templates (what new owners
read in the tunnel and the wizard) assemble every golden snapshot byte for
byte; with overrides in every language but English, too, because the
prompt reads only the English texts. English overrides change what owners
read, so the assembly keeps the code templates (the e2e journey of the
editor checks a published English override against an assembled prompt).
"""

import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.niches.effective_niche_template_registry import (
    EffectiveNicheTemplateRegistry,
)
from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.registries.niches.starter_answer_registry import StarterAnswerRegistry
from app.repositories.niche_text_repository import NicheTextRepository
from app.schemas.constants.localization import CabinetLanguage
from app.schemas.constants.niches import NicheTextReleaseKind
from app.schemas.domain.niche_texts import (
    NicheTextDraftDocument,
    NicheTextEntry,
    NicheTextReleaseDocument,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.niches.constrained_integers import NicheTextVersion
from app.schemas.typings.niches.constrained_strings import NicheOverrideText
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.niches.niche_text_catalog import build_niche_text_catalog
from app.utilities.niches.niche_text_identity import release_id_for
from tests.assembly.niche_prompt_samples import (
    SNAPSHOT_DIRECTORY,
    render_sample_prompts,
)

CODE_TEMPLATES = NicheTemplateRegistry()
STARTERS = StarterAnswerRegistry()


def effective_registry(
    *, with_overrides: bool
) -> tuple[EffectiveNicheTemplateRegistry, NicheTextRepository]:
    repo = NicheTextRepository(
        InMemoryDocumentCollectionAdapter(NicheTextDraftDocument),
        InMemoryDocumentCollectionAdapter(NicheTextReleaseDocument),
    )
    if with_overrides:
        for template in CODE_TEMPLATES.list_all():
            catalog = build_niche_text_catalog(
                template, STARTERS.get(template.key, CountryCode("GE"))
            )
            repo.add_release(
                NicheTextReleaseDocument(
                    id=release_id_for(template.key, NicheTextVersion(1)),
                    niche_key=template.key,
                    version=NicheTextVersion(1),
                    kind=NicheTextReleaseKind.PUBLISH,
                    entries=[
                        NicheTextEntry(
                            field_key=field.field_key,
                            language=LanguageTag(language.value),
                            text=NicheOverrideText(f"Reworded {language.value}"),
                        )
                        for field in catalog.fields
                        for language in CabinetLanguage
                        if language is not CabinetLanguage.ENGLISH
                    ],
                    published_by=UserId(),
                )
            )
    return EffectiveNicheTemplateRegistry(CODE_TEMPLATES, repo), repo


@pytest.mark.parametrize("with_overrides", [False, True])
def test_every_snapshot_is_byte_identical_through_the_effective_templates(
    with_overrides: bool,
) -> None:
    registry, _ = effective_registry(with_overrides=with_overrides)

    prompts = render_sample_prompts(registry.list_all())

    assert len(prompts) == 32
    for file_name, text in prompts.items():
        stored: bytes = (SNAPSHOT_DIRECTORY / file_name).read_bytes()
        assert text.encode("utf-8") == stored, file_name


def test_without_a_version_each_effective_template_is_the_code_template() -> None:
    registry, _ = effective_registry(with_overrides=False)

    for template in CODE_TEMPLATES.list_all():
        assert registry.get(template.key) is CODE_TEMPLATES.get(template.key)
