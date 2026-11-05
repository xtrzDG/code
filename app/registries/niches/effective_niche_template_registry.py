from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.niche_text_repositories import NicheTextRepoContract
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.niche_texts import NicheTextReleaseDocument
from app.schemas.dto.niches import NicheTemplate
from app.utilities.niches.niche_text_overlay import overlay_niche_template


class EffectiveNicheTemplateRegistry(NicheTemplateRegistryContract):
    """
    The niche templates as new owners read them in the tunnel and the
    profile wizard: the code template with the niche's newest published
    text overrides laid over it (the platform admin's niche template
    editor). The newest versions are read at every call (one indexed probe
    per niche), so a version is in force for every process as soon as it
    is published. A niche without a version reads exactly as the code
    template.

    The assembly of an assistant, its autotests and the checks keep the
    code template (`NicheTemplateRegistry`): a published override never
    changes a prompt; it reaches an assistant only through what an owner
    accepts into the profile.
    """

    def __init__(
        self,
        code_templates: NicheTemplateRegistryContract,
        niche_text_repo: NicheTextRepoContract,
    ) -> None:
        self._code_templates: NicheTemplateRegistryContract = code_templates
        self._niche_text_repo: NicheTextRepoContract = niche_text_repo

    def get(self, niche_key: NicheKey) -> NicheTemplate:
        template: NicheTemplate = self._code_templates.get(niche_key)
        for release in self._niche_text_repo.latest_releases([niche_key]):
            return overlay_niche_template(template, release.entries)

        return template

    def list_all(self) -> list[NicheTemplate]:
        templates: list[NicheTemplate] = self._code_templates.list_all()
        latest: dict[NicheKey, NicheTextReleaseDocument] = {
            release.niche_key: release
            for release in self._niche_text_repo.latest_releases(
                [template.key for template in templates]
            )
        }
        return [
            overlay_niche_template(template, latest[template.key].entries)
            if template.key in latest
            else template
            for template in templates
        ]
