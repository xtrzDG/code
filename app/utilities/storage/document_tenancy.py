"""Which business a stored document belongs to, and how its collection is isolated."""

from base_pydantic_schemas import PersistentDocument
from pydantic.fields import FieldInfo

from app.schemas.constants.storage import CollectionIsolation
from app.schemas.typings.businesses.prefixed_id import BusinessId

BUSINESS_ID_FIELD_NAME: str = "business_id"
DOCUMENT_ID_FIELD_NAME: str = "id"


def read_document_business_id(document: PersistentDocument) -> BusinessId | None:
    """
    The business that owns a document, for the `business_id` storage column.

    Tenant documents carry `business_id`; a business document is its own
    tenant (its `id` is a BusinessId). Platform documents return None.
    """

    business_id: object = getattr(document, BUSINESS_ID_FIELD_NAME, None)
    if isinstance(business_id, BusinessId):
        return business_id

    document_id: object = getattr(document, DOCUMENT_ID_FIELD_NAME, None)
    if isinstance(document_id, BusinessId):
        return document_id

    return None


def infer_collection_isolation(
    document_type: type[PersistentDocument],
) -> CollectionIsolation:
    """
    TENANT when every document of the type belongs to exactly one business.

    That is a required `business_id: BusinessId` field. Documents with an
    optional business (audit entries, queued jobs) or none at all (users,
    sessions, one-time codes, raw model turns, businesses) are PLATFORM: they
    are read across businesses, so the scope must not hide them.
    """

    business_id_field: FieldInfo | None = document_type.model_fields.get(
        BUSINESS_ID_FIELD_NAME
    )
    if business_id_field is None:
        return CollectionIsolation.PLATFORM

    is_required_business_id: bool = (
        business_id_field.annotation is BusinessId and business_id_field.is_required()
    )
    if is_required_business_id:
        return CollectionIsolation.TENANT

    return CollectionIsolation.PLATFORM
