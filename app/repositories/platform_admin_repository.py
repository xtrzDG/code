from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.platform_admins import PlatformAdminRepoContract
from app.repositories.document_queries import field_equals, stored_text
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.domain.platform_admins import PlatformAdminDocument
from app.schemas.typings.access.prefixed_id import PlatformAdminId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.users.constrained_strings import EmailAddress

PHONE_NUMBER_FIELD: DocumentFieldPath = DocumentFieldPath("phone_number")
EMAIL_FIELD: DocumentFieldPath = DocumentFieldPath("email")
ROLE_FIELD: DocumentFieldPath = DocumentFieldPath("role")


class PlatformAdminRepository(PlatformAdminRepoContract):
    """
    The admin team (a platform collection, 1103): a person's record by
    their sign-in phone or e-mail, and the admins of a role, on indexed
    columns; the Team page reads the team role by role.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[PlatformAdminDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[PlatformAdminDocument] = (
            collection
        )

    def save(self, admin: PlatformAdminDocument) -> None:
        self._collection.upsert(str(admin.id), admin)

    def get(self, admin_id: PlatformAdminId) -> PlatformAdminDocument | None:
        return self._collection.get(str(admin_id))

    def delete(self, admin_id: PlatformAdminId) -> None:
        self._collection.delete(str(admin_id))

    def find_by_phone_number(
        self, phone_number: E164PhoneNumber
    ) -> PlatformAdminDocument | None:
        return self._collection.find_one_by_field(
            PHONE_NUMBER_FIELD, stored_text(phone_number)
        )

    def find_by_email(self, email: EmailAddress) -> PlatformAdminDocument | None:
        return self._collection.find_one_by_field(EMAIL_FIELD, stored_text(email))

    def list_by_role(self, role: PlatformAdminRole) -> list[PlatformAdminDocument]:
        return self._collection.list_by_fields([field_equals(ROLE_FIELD, role)])

    def list_team(self) -> list[PlatformAdminDocument]:
        # One indexed query per role: the team is a handful of rows.
        return [
            admin for role in PlatformAdminRole for admin in self.list_by_role(role)
        ]
