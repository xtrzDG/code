"""A location leaving its brand: the brand owner's way and the location's own."""

from typed_time_provider import Microseconds

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.brands import BrandDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.brands.prefixed_id import BrandId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.brands.brand_audit import BRAND_LOCATION_ENTITY, record_in_locations


def take_location_out(
    business_repo: BusinessRepoContract,
    brand_repo: BrandRepoContract,
    audit_log_repo: AuditLogRepoContract,
    brand_id: BrandId,
    location_id: BusinessId,
    actor_id: UserId,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """
    The location stops naming the brand (in one step with what is stored),
    which ends every brand member's access to it at their next request;
    then no manager keeps it assigned, so joining again later gives nobody
    access by surprise. Its own team and data stay. Raises NotFoundError
    when the business is no location of the brand.
    """

    def leave(current: BusinessDocument) -> None:
        if current.brand_id != brand_id:
            raise NotFoundError(f"Business {location_id} is no location of this brand.")

        current.brand_id = None
        current.updated_at = now

    business_repo.update(location_id, leave)

    def unassign(current: BrandDocument) -> None:
        for member in current.members:
            member.business_ids = [
                business_id
                for business_id in member.business_ids
                if business_id != location_id
            ]
        current.updated_at = now

    if brand_repo.get(brand_id) is not None:
        brand_repo.update(brand_id, unassign)

    record_in_locations(
        audit_log_repo,
        [location_id],
        actor_id,
        AuditAction.DELETE,
        BRAND_LOCATION_ENTITY,
        AuditEntityReference(str(brand_id)),
        client_ip_address,
        now,
    )
