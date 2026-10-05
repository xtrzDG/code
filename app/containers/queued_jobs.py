"""
The worker's handlers of queued jobs by job name (the queue is filled by
use cases through the job queue facilitator):
`GatewaysContainer.queued_job_operators`.
"""

from dependency_injector.providers import Dict

from app.containers.operators.operators_container import OperatorsContainer
from app.use_cases.admin.alerts.check_platform_alerts_use_case import (
    SEND_PLATFORM_ALERT_JOB,
)
from app.use_cases.admin.security.key_rotation_views import (
    ROTATE_ENCRYPTED_SECRETS_JOB,
)
from app.use_cases.autotests.enqueue_autotest_run_use_case import RUN_AUTOTESTS_JOB
from app.use_cases.knowledge.website_import.start_website_import_use_case import (
    IMPORT_WEBSITE_JOB,
)
from app.use_cases.shared.business_export_queue import BUILD_BUSINESS_EXPORT_JOB
from app.use_cases.voice.recordings.recording_archive_paths import (
    ARCHIVE_CALL_RECORDING_JOB,
)
from app.utilities.calls.text_back_jobs import SEND_TEXT_BACK_JOB
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    PROCESS_INBOUND_MESSAGE_JOB,
    PROCESS_PLATFORM_BOT_UPDATE_JOB,
    PROCESS_POST_CALL_JOB,
)
from app.utilities.memory.summary_jobs import SUMMARIZE_CONVERSATION_JOB
from app.utilities.privacy.processor_erasure_jobs import ERASE_PROCESSOR_COPIES_JOB


def queued_job_operator_map(operators: OperatorsContainer) -> Dict:
    """The operator that runs each kind of queued job."""

    return Dict(
        {
            RUN_AUTOTESTS_JOB: operators.assistants.run_queued_autotests_operator,
            # The inbox: webhook messages answered by the worker.
            PROCESS_INBOUND_MESSAGE_JOB: (
                operators.channels.process_inbound_message_operator
            ),
            PROCESS_PLATFORM_BOT_UPDATE_JOB: (
                operators.channels.process_platform_bot_update_operator
            ),
            PROCESS_POST_CALL_JOB: operators.conversations.process_post_call_operator,
            # A finished call's recording moved into the EU object storage.
            ARCHIVE_CALL_RECORDING_JOB: (
                operators.conversations.archive_call_recording_operator
            ),
            # The outbox: replies and staff notifications sent with retries.
            DELIVER_OUTBOUND_JOB: operators.channels.deliver_outbound_operator,
            # A caller who did not get through: their WhatsApp or SMS.
            SEND_TEXT_BACK_JOB: operators.calls.send_text_back_operator,
            # A full export of a business written into its archive.
            BUILD_BUSINESS_EXPORT_JOB: operators.privacy.run_business_export_operator,
            # A business's website read into knowledge drafts.
            IMPORT_WEBSITE_JOB: operators.knowledge.run_website_import_operator,
            # Every stored secret sealed again with the current key.
            ROTATE_ENCRYPTED_SECRETS_JOB: (
                operators.security.rotate_encrypted_secrets_operator
            ),
            # A platform alert to the team's chats and inboxes.
            SEND_PLATFORM_ALERT_JOB: (
                operators.platform_ops.send_platform_alert_operator
            ),
            # A quiet conversation summarized for the customer memory.
            SUMMARIZE_CONVERSATION_JOB: operators.memory.summarize_conversation_operator,  # noqa: E501
            ERASE_PROCESSOR_COPIES_JOB: operators.privacy.erase_copies_operator,
        }
    )
