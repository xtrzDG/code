from dependency_injector import containers
from dependency_injector.providers import Singleton

from app.utilities.conversations.language_detector import LanguageDetector
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from app.utilities.storage.storage_scope_context import StorageScopeContext


class UtilitiesContainer(containers.DeclarativeContainer):
    phone_number_parser: Singleton[PhoneNumberParser] = Singleton(PhoneNumberParser)
    localized_text_resolver: Singleton[LocalizedTextResolver] = Singleton(
        LocalizedTextResolver
    )
    language_detector: Singleton[LanguageDetector] = Singleton(LanguageDetector)
    # One scope shared by every Postgres collection of the process.
    storage_scope: Singleton[StorageScopeContext] = Singleton(StorageScopeContext)
