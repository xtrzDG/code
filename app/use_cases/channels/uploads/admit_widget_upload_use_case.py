from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.media_settings import MediaSettings
from app.schemas.constants.media import AttachmentKind, WidgetUploadRefusal
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.channels.widget_uploads import (
    WidgetUploadAdmission,
    WidgetUploadAllowance,
)
from app.schemas.typings.media.constrained_integers import MediaByteLimit
from app.schemas.typings.media.constrained_strings import (
    DeclaredMediaType,
    MessageMediaType,
)
from app.use_cases.shared.widget_chats import (
    require_live_assistant,
    require_open_widget_chat,
)
from app.utilities.channels.widget_rate_limits import (
    WIDGET_UPLOAD_LIMITS,
    refuse_too_frequent_widget_requests,
)
from app.utilities.media.upload_checks import (
    UPLOAD_KINDS,
    accepted_upload_type,
    read_declared_type,
)
from app.utilities.media.upload_refusals import upload_refused


class AdmitWidgetUploadUseCase(
    UseCaseContract[WidgetUploadAdmission, WidgetUploadAllowance]
):
    """
    A website visitor starts uploading a photo or a voice note: before a
    byte of the file is read, the upload is counted per visitor, per client
    network, per business and for the platform (429 with Retry-After,
    `WIDGET_UPLOAD_LIMITS`), the chat must be switched on with its
    assistant live (404 and 409, as for messages), and the type its form
    part declares must be one the chat takes (422 `unsupported_type`). The
    answer says how large the file may be, the cap of the declared kind
    (MEDIA_MAX_IMAGE_BYTES for a photo, MEDIA_MAX_VOICE_BYTES for a voice
    note), so the route stops reading beyond it; the file's own bytes must
    then say the same type (`AcceptWidgetUploadUseCase`).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        media_settings: MediaSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._media_settings: MediaSettings = media_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WidgetUploadAdmission) -> WidgetUploadAllowance:
        refuse_too_frequent_widget_requests(
            self._rate_limit_registry,
            WIDGET_UPLOAD_LIMITS,
            business_id=input_data.business_id,
            session_key=input_data.session_key,
            client_ip_address=input_data.client_ip_address,
            now=self._wall_clock.now_unix(),
        )
        business: BusinessDocument = require_open_widget_chat(
            self._business_repo, self._channel_repo, input_data.business_id
        )
        require_live_assistant(business)
        declared: DeclaredMediaType | None = read_declared_type(
            input_data.declared_type
        )
        accepted: MessageMediaType | None = accepted_upload_type(declared)
        if accepted is None:
            raise upload_refused(WidgetUploadRefusal.UNSUPPORTED_TYPE, declared)

        cap: MediaByteLimit = (
            self._media_settings.max_image_bytes
            if UPLOAD_KINDS[accepted] is AttachmentKind.IMAGE
            else self._media_settings.max_voice_bytes
        )
        return WidgetUploadAllowance(max_file_bytes=cap)
