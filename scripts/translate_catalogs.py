"""
Translation of the text catalogs into every cabinet language.

The backend part covers the owner text catalog
(app/registries/localization/texts/<language>.json: plans, niche
templates, staff notifications, call forwarding guides, billing texts):

    uv run python -m scripts.translate_catalogs backend check
    uv run python -m scripts.translate_catalogs backend draft --language de
    uv run python -m scripts.translate_catalogs backend reviewed --language de
    uv run python -m scripts.translate_catalogs backend reviewed --language ka \
        --key plans.chat.name

`check` lists what each language lacks and what waits for review (exit 1
when a text is missing). `draft` asks the configured language model
(LLM_SUMMARY_MODEL_ID, else LLM_MODEL_ID, with the provider keys of .env)
for the missing texts and marks them for review: a reviewed file names them
in `draft_keys`, a file of drafts stays needs_review as a whole. `reviewed`
records that a native speaker checked the named drafts, or the whole file.
English is the source and is written by hand.
"""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from app.containers.app import AppContainer
from app.contracts.llm import LlmAdapterContract
from app.registries.localization.text_catalog_registry import TextCatalogRegistry
from app.schemas.constants.localization import CabinetLanguage
from app.schemas.dto.text_catalog import TextCatalog
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.localization.constrained_strings import OwnerTextKey
from app.utilities.localization.owner_texts import OWNER_TEXTS_DIRECTORY
from app.utilities.localization.text_catalog_files import SOURCE_LANGUAGE
from scripts.catalog_translation.owner_catalog_files import (
    as_reviewed,
    catalog_report,
    load_catalog,
    with_drafts,
    write_catalog_file,
)
from scripts.catalog_translation.text_drafting import DraftedTexts, OwnerTextDrafter

type DrafterFactory = Callable[[], OwnerTextDrafter]


def configured_drafter(container: AppContainer | None = None) -> OwnerTextDrafter:
    """The language model of the environment (.env), as the worker uses it."""

    if container is None:
        container = AppContainer()
    settings = container.config.app_settings()
    adapter: LlmAdapterContract = container.adapters.routing_llm_adapter()
    model_id: LlmModelId = settings.llm_summary_model_id or settings.llm_model_id
    return OwnerTextDrafter(adapter, model_id)


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="translate_catalogs")
    parts = parser.add_subparsers(dest="part", required=True)
    backend = parts.add_parser("backend", help="the owner text catalog")
    commands = backend.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="what each language lacks or has as drafts")
    languages: list[str] = [
        language.value
        for language in CabinetLanguage
        if language is not SOURCE_LANGUAGE
    ]
    draft = commands.add_parser("draft", help="draft the missing texts of a language")
    draft.add_argument("--language", required=True, choices=languages)
    reviewed = commands.add_parser("reviewed", help="mark drafts as checked")
    reviewed.add_argument("--language", required=True, choices=languages)
    reviewed.add_argument("--key", action="append", dest="keys")
    return parser.parse_args(arguments)


def main(
    arguments: list[str],
    directory: Path = OWNER_TEXTS_DIRECTORY,
    drafter_factory: DrafterFactory = configured_drafter,
) -> int:
    options: argparse.Namespace = parse_arguments(arguments)
    catalog: TextCatalog = load_catalog(directory)
    if options.command == "check":
        for line in catalog_report(catalog):
            sys.stdout.write(line + "\n")
        registry = TextCatalogRegistry(catalog)
        return (
            1
            if any(registry.list_missing_keys(lang) for lang in CabinetLanguage)
            else 0
        )

    language = CabinetLanguage(options.language)
    if options.command == "reviewed":
        keys: list[OwnerTextKey] | None = (
            None
            if options.keys is None
            else [OwnerTextKey(key) for key in options.keys]
        )
        path: Path = write_catalog_file(directory, as_reviewed(catalog, language, keys))
        sys.stdout.write(f"{path.name}: marked reviewed\n")
        return 0

    return draft_missing(catalog, language, directory, drafter_factory)


def draft_missing(
    catalog: TextCatalog,
    language: CabinetLanguage,
    directory: Path,
    drafter_factory: DrafterFactory,
) -> int:
    registry = TextCatalogRegistry(catalog)
    missing: list[OwnerTextKey] = registry.list_missing_keys(language)
    if missing == []:
        sys.stdout.write(f"{language.value}.json: nothing to draft\n")
        return 0

    english = catalog.files[SOURCE_LANGUAGE].texts
    drafted: DraftedTexts = drafter_factory().draft(
        language, {key: english[key] for key in missing}
    )
    path: Path = write_catalog_file(
        directory, with_drafts(catalog, language, drafted.drafts)
    )
    sys.stdout.write(f"{path.name}: {len(drafted.drafts)} texts drafted for review\n")
    for key in drafted.refused:
        sys.stdout.write(f"{key}: the draft was refused (placeholders or format)\n")

    return 1 if drafted.refused else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
