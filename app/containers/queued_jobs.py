"""
The worker's handlers of queued jobs by job name (the queue is filled by
use cases through the job queue facilitator):
`GatewaysContainer.queued_job_operators`.
"""

from dependency_injector.providers import Dict, Factory, Provider

from app.containers.account_deletion.account_deletion_operator_factories import (
    AccountDeletionOperatorFactories,
)
from app.containers.operators.operators_container import OperatorsContainer
from app.use_cases.admin.alerts.check_platform_alerts_use_case import (
    SEND_PLATFORM_ALERT_JOB,
)
from app.use_cases.admin.incidents.incident_expansion import EXPAND_INCIDENT_JOB
from app.use_cases.admin.security.key_rotation_views import (
    ROTATE_ENCRYPTED_SECRETS_JOB,
)
from app.use_cases.autotests.enqueue_autotest_run_use_case import RUN_AUTOTESTS_JOB
from app.use_cases.knowledge.website_import.start_website_import_use_case import (
    IMPORT_WEBSITE_JOB,
)
from app.use_cases.shared.business_export_queue import BUILD_BUSINESS_EXPORT_JOB
from app.use_cases.shared.knowledge_index_queue import INDEX_KNOWLEDGE_JOB
from app.use_cases.voice.recordings.recording_archive_paths import (
    ARCHIVE_CALL_RECORDING_JOB,
    DISCARD_CALL_RECORDING_JOB,
)
from app.utilities.business_closures.deletion_jobs import DELETE_BUSINESS_JOB
from app.utilities.calendar_sync.booking_system_jobs import (
    WRITE_BOOKING_SYSTEM_BOOKING_JOB,
)
from app.utilities.calls.text_back_jobs import SEND_TEXT_BACK_JOB
from app.utilities.deliveries.comment_trigger_jobs import PROCESS_COMMENT_TRIGGER_JOB
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    PROCESS_INBOUND_MESSAGE_JOB,
    PROCESS_PLATFORM_BOT_UPDATE_JOB,
    PROCESS_POST_CALL_JOB,
)
from app.utilities.integrations.webhook_jobs import DELIVER_WEBHOOK_JOB
from app.utilities.memory.summary_jobs import SUMMARIZE_CONVERSATION_JOB
from app.utilities.privacy.processor_erasure_jobs import ERASE_PROCESSOR_COPIES_JOB
from app.utilities.waitlist.offer_jobs import OFFER_FREED_PLACE_JOB


def queued_job_operator_map(
    operators: OperatorsContainer,
    account_deletions: Provider[AccountDeletionOperatorFactories],
) -> Dict:
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
            # An Instagram comment that named the owner's keyword (1212).
            PROCESS_COMMENT_TRIGGER_JOB: (
                operators.channels.process_comment_trigger_operator
            ),
            # A finished call's recording moved into the EU object storage.
            ARCHIVE_CALL_RECORDING_JOB: (
                operators.conversations.archive_call_recording_operator
            ),
            # A declined call recording deleted at the voice platform.
            DISCARD_CALL_RECORDING_JOB: (
                operators.conversations.discard_call_recording_operator
            ),
            # The outbox: replies and staff notifications sent with retries.
            DELIVER_OUTBOUND_JOB: operators.channels.deliver_outbound_operator,
            # A caller who did not get through: their WhatsApp or SMS.
            SEND_TEXT_BACK_JOB: operators.calls.send_text_back_operator,
            # A full export of a business written into its archive.
            BUILD_BUSINESS_EXPORT_JOB: operators.privacy.run_business_export_operator,
            # A business's website read into knowledge drafts.
            IMPORT_WEBSITE_JOB: operators.knowledge.run_website_import_operator,
            # Aliases in the business's languages and search vectors (1211).
            INDEX_KNOWLEDGE_JOB: operators.knowledge.index_knowledge_operator,
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
            # A freed place offered to the next waiting customer (1151).
            OFFER_FREED_PLACE_JOB: operators.growth.offer_freed_place_operator,
            # The next batch of businesses an all-businesses incident reaches.
            EXPAND_INCIDENT_JOB: operators.reliability.expand_incident_operator,
            # An outbound webhook's signed POST, retried up to a day (1181).
            DELIVER_WEBHOOK_JOB: operators.webhooks.deliver_webhook_operator,
            # A booking written to (or cancelled in) its resource's Cal.com.
            WRITE_BOOKING_SYSTEM_BOOKING_JOB: (
                operators.calendars.write_booking_system_booking_operator
            ),
            # A closed business deleted for good, on the platform pool (1220).
            DELETE_BUSINESS_JOB: Factory(
                AccountDeletionOperatorFactories.delete_business, account_deletions
            ),
        }
    )
