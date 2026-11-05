from base_pydantic_schemas import BaseDocument
from pydantic import Field

from app.schemas.constants.analytics import DeviceClass, WebVitalName
from app.schemas.typings.analytics.constrained_integers import WebVitalValue
from app.schemas.typings.analytics.constrained_strings import CabinetRoutePattern
from app.schemas.typings.analytics.prefixed_id import WebVitalSampleId
from app.schemas.typings.users.prefixed_id import UserId


class WebVitalSampleDocument(BaseDocument):
    """
    One Core Web Vital a cabinet page reported (POST /v1/telemetry/events):
    the vital, its value, the page as a route template and the kind of
    device. It names the signed-in user only so one account's reports can
    be limited; every sample is purged after 90 days.
    """

    id: WebVitalSampleId = Field(default_factory=WebVitalSampleId)
    user_id: UserId
    metric: WebVitalName
    value: WebVitalValue
    route: CabinetRoutePattern
    device_class: DeviceClass
