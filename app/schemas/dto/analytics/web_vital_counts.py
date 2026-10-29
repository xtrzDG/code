from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.analytics import DeviceClass
from app.schemas.typings.analytics.constrained_integers import WebVitalSampleCount
from app.schemas.typings.analytics.constrained_strings import CabinetRoutePattern
from app.schemas.typings.storage.constrained_integers import DocumentBucketIndex


class WebVitalBucketCount(ImmutableDTO):
    """
    How many samples of one vital a page (route and device class) reported
    in one value bucket of a period (the bucket starts are the caller's).
    """

    route: CabinetRoutePattern
    device_class: DeviceClass
    bucket: DocumentBucketIndex
    count: WebVitalSampleCount
