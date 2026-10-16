"""S3-compatible object storage (EU region): how to reach one bucket."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.constrained_strings import (
    ObjectStorageBucketName,
    ObjectStorageRegion,
)
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret


class ObjectStorageConnection(ImmutableDTO):
    """
    One bucket of S3-compatible object storage, addressed path-style
    (`<endpoint>/<bucket>/<key>`, which AWS S3, Cloudflare R2, Hetzner,
    Scaleway and MinIO all accept) and signed with AWS Signature Version 4.
    """

    endpoint_url: PublicBaseUrl
    region: ObjectStorageRegion
    bucket: ObjectStorageBucketName
    access_key_id: PlatformIdentifier
    secret_access_key: PlatformSecret = Field(repr=False)
