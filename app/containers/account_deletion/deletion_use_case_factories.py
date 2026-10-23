from app.containers.account_deletion.account_deletion_dependencies import (
    AccountDeletionDependencies,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.business_closures.account_deletion import (
    DeleteCurrentUserCommand,
)
from app.schemas.dto.business_closures.business_deletions import (
    BusinessDeletionList,
    DeletionCertificateFile,
    DeletionCertificateQuery,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.typings.users.prefixed_id import UserId
from app.transformers.business_closures.deletion_certificate_html_transformer import (
    DeletionCertificateHtmlTransformer,
)
from app.use_cases.businesses.deletion.business_deprovisioning import (
    BusinessDeprovisioner,
)
from app.use_cases.businesses.deletion.business_file_erasure import (
    BusinessFileEraser,
)
from app.use_cases.businesses.deletion.channel_deprovisioning import (
    ChannelDeprovisioner,
)
from app.use_cases.businesses.deletion.conversation_trace_erasure import (
    ConversationTraceEraser,
)
from app.use_cases.businesses.deletion.delete_business_use_case import (
    DeleteBusinessUseCase,
)
from app.use_cases.businesses.deletion.deletion_completion import DeletionCompletion
from app.use_cases.users.account_deletion.delete_current_user_use_case import (
    DeleteCurrentUserUseCase,
)
from app.use_cases.users.account_deletion.get_deletion_certificate_use_case import (
    GetDeletionCertificateUseCase,
)
from app.use_cases.users.account_deletion.list_business_deletions_use_case import (
    ListBusinessDeletionsUseCase,
)


class DeletionUseCaseFactories:
    """
    One typed factory per use case of a deletion: the hard delete of a
    closed business (the worker's `delete_business` job, with its
    deprovisioner and erasers), a person's certificates, and deleting the
    person's own account.
    """

    def __init__(self, dependencies: AccountDeletionDependencies) -> None:
        self._dependencies: AccountDeletionDependencies = dependencies

    def delete_business(self) -> UseCaseContract[QueuedJobInput, JobReport]:
        given = self._dependencies
        return DeleteBusinessUseCase(
            business_repo=given.business_repo,
            closure_repo=given.closure_repo,
            deletion_repo=given.deletion_repo,
            ledger_mirror=given.ledger_mirror,
            row_eraser=given.row_eraser,
            deprovisioner=self._deprovisioner(),
            trace_eraser=ConversationTraceEraser(
                conversations=given.conversation_pages,
                calls=given.call_pages,
                llm_turn_repo=given.llm_turn_repo,
                processor_erasure=given.processor_erasure,
            ),
            file_eraser=BusinessFileEraser(
                calls=given.call_pages,
                message_media=given.message_media_pages,
                widget_uploads=given.widget_upload_pages,
                business_exports=given.business_export_pages,
                recording_storage=given.recording_storage,
                media_storage=given.media_storage,
                archive_storage=given.export_archive_storage,
            ),
            completion=DeletionCompletion(
                business_repo=given.business_repo,
                brand_repo=given.brand_repo,
                deletion_repo=given.deletion_repo,
                audit_log_repo=given.audit_log_repo,
            ),
            wall_clock=given.wall_clock,
        )

    def _deprovisioner(self) -> BusinessDeprovisioner:
        given = self._dependencies
        return BusinessDeprovisioner(
            channels=ChannelDeprovisioner(
                secret_cipher=given.secret_cipher,
                telegram_client=given.telegram_client,
                meta_subscriptions=given.meta_subscriptions,
            ),
            channel_repo=given.channel_repo,
            assistant_version_repo=given.assistant_version_repo,
            remove_voice_agent=given.remove_voice_agent,
            disconnect_google_calendar=given.disconnect_google_calendar,
            phone_number_repo=given.phone_number_repo,
            phone_number_provisioner=given.phone_number_provisioner,
            phone_line_lock=given.phone_line_lock,
            subscription_repo=given.subscription_repo,
            payment_gateway=given.payment_gateway,
        )

    def list_business_deletions(self) -> UseCaseContract[UserId, BusinessDeletionList]:
        return ListBusinessDeletionsUseCase(
            deletion_repo=self._dependencies.deletion_repo
        )

    def get_deletion_certificate(
        self,
    ) -> UseCaseContract[DeletionCertificateQuery, DeletionCertificateFile]:
        given = self._dependencies
        return GetDeletionCertificateUseCase(
            deletion_repo=given.deletion_repo,
            user_repo=given.user_repo,
            certificate_html=DeletionCertificateHtmlTransformer(
                given.localized_text_resolver
            ),
            renderer=given.certificate_renderer,
        )

    def delete_current_user(self) -> UseCaseContract[DeleteCurrentUserCommand, None]:
        given = self._dependencies
        return DeleteCurrentUserUseCase(
            step_up=given.step_up,
            storage_scope=given.storage_scope,
            user_repo=given.user_repo,
            user_session_repo=given.user_session_repo,
            totp_factor_repo=given.totp_factor_repo,
            recovery_code_repo=given.recovery_code_repo,
            passkey_repo=given.passkey_repo,
            business_repo=given.business_repo,
            brand_repo=given.brand_repo,
            closure_repo=given.closure_repo,
            push_subscription_repo=given.push_subscription_repo,
            notification_preferences_repo=given.notification_preferences_repo,
            security_nudge_repo=given.security_nudge_repo,
            platform_admins=given.platform_admins,
            audit_log_repo=given.audit_log_repo,
            wall_clock=given.wall_clock,
        )
