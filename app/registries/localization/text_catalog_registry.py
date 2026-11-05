from app.contracts.catalog_registries import TextCatalogRegistryContract
from app.schemas.constants.localization import CabinetLanguage, TextReviewStatus
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.text_catalog import TextCatalog, TextCatalogFile
from app.schemas.typings.localization.constrained_strings import OwnerTextKey
from app.utilities.localization.owner_texts import OWNER_TEXT_CATALOG, owner_text
from app.utilities.localization.text_catalog_files import SOURCE_LANGUAGE


class TextCatalogRegistry(TextCatalogRegistryContract):
    """
    The owner text catalog: plans, niche templates, staff notifications,
    call forwarding guides and billing texts in every cabinet language
    (`app/registries/localization/texts/<language>.json`, read and checked
    at startup). English is the source and the only fallback; Hebrew and
    German are drafts until a native speaker reviews them (`needs_review`).

    The catalog modules build their texts from the same process-wide
    catalog; this registry answers what is translated and reviewed (the
    translation script and the completeness checks ask it).
    """

    def __init__(self, catalog: TextCatalog = OWNER_TEXT_CATALOG) -> None:
        self._catalog: TextCatalog = catalog

    def get(self, key: OwnerTextKey) -> LocalizedText:
        return owner_text(str(key), self._catalog)

    def list_keys(self) -> list[OwnerTextKey]:
        return list(self._catalog.files[SOURCE_LANGUAGE].texts)

    def list_missing_keys(self, language: CabinetLanguage) -> list[OwnerTextKey]:
        texts = self._catalog.files[language].texts
        return [key for key in self.list_keys() if key not in texts]

    def review_status(
        self, key: OwnerTextKey, language: CabinetLanguage
    ) -> TextReviewStatus | None:
        catalog_file: TextCatalogFile = self._catalog.files[language]
        if key not in catalog_file.texts:
            return None

        if key in catalog_file.draft_keys:
            return TextReviewStatus.NEEDS_REVIEW

        return catalog_file.review_status
