"""Which business an operation works for, and the fail-closed scope check."""

from app.schemas.constants.storage import StorageScopeKind
from app.schemas.dto.storage import StorageScope
from app.schemas.exceptions.storage_errors import UnscopedStorageAccessError
from app.schemas.typings.businesses.prefixed_id import BusinessId

BUSINESS_ID_ATTRIBUTE: str = "business_id"


def find_operation_business_id(input_data: object) -> BusinessId | None:
    """
    The business named by an operation's input (its `business_id`, or the
    input itself when it is a business id), or None for platform-level
    operations (sign-in, webhooks resolved later, admin lists, jobs over
    every business).
    """

    if isinstance(input_data, BusinessId):
        return input_data

    business_id: object = getattr(input_data, BUSINESS_ID_ATTRIBUTE, None)
    if isinstance(business_id, BusinessId):
        return business_id

    return None


def require_tenant_scope(scope: StorageScope, collection_label: str) -> StorageScope:
    """
    The scope an operation on a tenant collection runs in.

    Raises:
        UnscopedStorageAccessError: the code entered no scope.
    """

    if scope.kind is StorageScopeKind.UNSCOPED:
        raise UnscopedStorageAccessError(
            f"{collection_label} was used outside a storage scope. Run the "
            "code inside scoped_to_business(...) (a request or job for one "
            "business) or, for platform-level work, platform_wide()."
        )

    return scope
