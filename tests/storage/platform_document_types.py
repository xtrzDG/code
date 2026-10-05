"""
The document types that belong to the platform rather than to one
business: their collections are PLATFORM-isolated (no `business_id`
column of their own), every other catalog collection is TENANT.
"""

from base_pydantic_schemas import PersistentDocument

from app.schemas.domain import help_progress, platform_status
from app.schemas.domain.billing_profiles import InvoiceCounterDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.client_health_changes import AdminDigestStateDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import LlmTurnDocument
from app.schemas.domain.exchange_rates import ExchangeRateDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.domain.jobs import (
    PeriodicJobRunDocument,
    QueuedJobDocument,
    WorkerHeartbeatDocument,
)
from app.schemas.domain.key_rotations import KeyRotationDocument
from app.schemas.domain.legal import SubprocessorAnnouncementDocument
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.domain.mfa import (
    MfaChallengeDocument,
    RecoveryCodeDocument,
    TotpFactorDocument,
)
from app.schemas.domain.platform_admins import PlatformAdminDocument
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.domain.web_vitals import WebVitalSampleDocument

PLATFORM_DOCUMENT_TYPES: frozenset[type[PersistentDocument]] = frozenset(
    {
        UserDocument,
        AdminDigestStateDocument,
        OtpChallengeDocument,
        UserSessionDocument,
        BusinessDocument,
        AuditLogEntryDocument,
        LlmTurnDocument,
        QueuedJobDocument,
        PeriodicJobRunDocument,
        WorkerHeartbeatDocument,
        # Staff-bot updates and finished-call reports arrive before their
        # business is known.
        InboundEventDocument,
        # A re-encryption run covers every business at once.
        KeyRotationDocument,
        # Published exchange rates are the same for every business.
        ExchangeRateDocument,
        # Growth analytics: a sign-in names no business, and the metrics
        # read every business's steps.
        ProductEventDocument,
        WebVitalSampleDocument,
        # Two-factor sign-in belongs to a person, whatever businesses they
        # work for.
        TotpFactorDocument,
        RecoveryCodeDocument,
        MfaChallengeDocument,
        # The platform's own operations: alerts, backups, incidents (an
        # incident names the businesses it affected, it belongs to none).
        PlatformAlertStateDocument,
        MaintenanceRunDocument,
        IncidentDocument,
        # The platform admin team belongs to the platform (1103).
        PlatformAdminDocument,
        # The status page belongs to the platform, help progress to a person.
        platform_status.PlatformAnnouncementDocument,
        platform_status.PlatformStatusDayDocument,
        help_progress.HelpProgressDocument,
        InvoiceCounterDocument,  # One invoice series for every business (1114).
        # A sub-processor change is announced to every business at once (1124).
        SubprocessorAnnouncementDocument,
    }
)
