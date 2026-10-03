from app.contracts.registries import NicheTemplateRegistryContract
from app.registries.niches.niche_template_catalog import build_niche_templates
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.niches import NicheTemplate
from app.schemas.exceptions.application_errors import NotFoundError


class NicheTemplateRegistry(NicheTemplateRegistryContract):
    """
    Read-only catalog of the niche templates.

    A template changes only the profile questions, what is booked and the
    handoff rules; every niche runs on the same platform. Templates are built
    once and returned as immutable DTOs, so callers cannot change them.
    """

    def __init__(self) -> None:
        templates: list[NicheTemplate] = build_niche_templates()
        templates_by_key: dict[NicheKey, NicheTemplate] = {}
        for template in templates:
            if template.key in templates_by_key:
                raise ValueError(f"Niche {template.key} has two templates.")

            templates_by_key[template.key] = template

        missing_keys: list[NicheKey] = [
            niche_key for niche_key in NicheKey if niche_key not in templates_by_key
        ]
        if missing_keys != []:
            raise ValueError(f"Niches without a template: {missing_keys}.")

        self._templates: list[NicheTemplate] = templates
        self._templates_by_key: dict[NicheKey, NicheTemplate] = templates_by_key

    def get(self, niche_key: NicheKey) -> NicheTemplate:
        template: NicheTemplate | None = self._templates_by_key.get(niche_key)
        if template is None:
            raise NotFoundError(f"Niche {niche_key} has no template.")

        return template

    def list_all(self) -> list[NicheTemplate]:
        return list(self._templates)
