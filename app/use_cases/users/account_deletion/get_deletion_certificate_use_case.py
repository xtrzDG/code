from app.contracts.deletion_certificates import DeletionCertificateRendererContract
from app.contracts.repositories.business_closure_repositories import (
    BusinessDeletionRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.business_closures import BusinessDeletionDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.business_closures.business_deletions import (
    DeletionCertificateFile,
    DeletionCertificateQuery,
)
from app.schemas.dto.business_closures.deletion_certificates import (
    DeletionCertificateSource,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.business_closures.constrained_strings import (
    DeletionCertificateFileName,
)
from app.schemas.typings.business_closures.strings import DeletionCertificateHtml
from app.schemas.typings.localization.constrained_strings import LanguageTag

FALLBACK_LANGUAGE: LanguageTag = LanguageTag("en")


class GetDeletionCertificateUseCase(
    UseCaseContract[DeletionCertificateQuery, DeletionCertificateFile]
):
    """
    The deletion certificate of a business the person owned, as a PDF in
    the language they ask for (their interface language by default): who
    and what was deleted, when, what was switched off, what the law keeps,
    and the fingerprint of those facts. Anyone else gets 404, as for a
    business that never existed; a deletion still running has none yet.
    """

    def __init__(
        self,
        deletion_repo: BusinessDeletionRepoContract,
        user_repo: UserRepoContract,
        certificate_html: TransformerContract[
            DeletionCertificateSource, DeletionCertificateHtml
        ],
        renderer: DeletionCertificateRendererContract,
    ) -> None:
        self._deletion_repo: BusinessDeletionRepoContract = deletion_repo
        self._user_repo: UserRepoContract = user_repo
        self._certificate_html: TransformerContract[
            DeletionCertificateSource, DeletionCertificateHtml
        ] = certificate_html
        self._renderer: DeletionCertificateRendererContract = renderer

    def run(self, input_data: DeletionCertificateQuery) -> DeletionCertificateFile:
        entry: BusinessDeletionDocument | None = self._deletion_repo.get(
            input_data.deletion_id
        )
        if entry is None or all(
            holder.user_id != input_data.user_id for holder in entry.owners
        ):
            raise NotFoundError("There is no such deletion certificate.")

        if entry.completed_at is None:
            raise ConflictError(
                "The deletion is still running; the certificate follows."
            )

        user: UserDocument | None = self._user_repo.get(input_data.user_id)
        language: LanguageTag = input_data.language or (
            user.locale if user is not None else FALLBACK_LANGUAGE
        )
        html: DeletionCertificateHtml = self._certificate_html.transform(
            DeletionCertificateSource(entry=entry, language=language)
        )
        return DeletionCertificateFile(
            file_name=DeletionCertificateFileName(
                f"deletion-certificate-{str(entry.id).rsplit('_', 1)[-1][:8]}.pdf"
            ),
            content=self._renderer.render(html),
        )
