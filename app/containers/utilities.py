from dependency_injector import containers
from dependency_injector.providers import Singleton

from app.contracts.jobs import JobWakeupContract
from app.contracts.storage import StorageScopeContract
from app.utilities.conversations.language_detector import LanguageDetector
from app.utilities.jobs.job_wakeup_signal import JobWakeupSignal
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from app.utilities.storage.storage_scope_context import StorageScopeContext


class UtilitiesContainer(containers.DeclarativeContainer):
    phone_number_parser: Singleton[PhoneNumberParser] = Singleton(PhoneNumberParser)
    localized_text_resolver: Singleton[LocalizedTextResolver] = Singleton(
        LocalizedTextResolver
    )
    language_detector: Singleton[LanguageDetector] = Singleton(LanguageDetector)
    # One scope shared by every Postgres collection of the process, and by
    # the operators, orchestrators and the worker that enter it.
    storage_scope: Singleton[StorageScopeContract] = Singleton(StorageScopeContext)
    # Queued jobs wake the idle lane threads of a worker in this process.
    job_wakeup: Singleton[JobWakeupContract] = Singleton(JobWakeupSignal)
