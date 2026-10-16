from app.contracts.processor_erasure import ProcessorErasureAdapterContract
from app.schemas.constants.privacy import SubProcessor
from app.schemas.dto.processor_erasure import ProcessorErasureScope
from app.schemas.typings.compliance.constrained_integers import ErasedRecordCount


class MessagingPlatformErasureAdapter(ProcessorErasureAdapterContract):
    """
    The documented no-op for Meta (WhatsApp, Messenger, Instagram) and
    Telegram: their copy of a conversation is the customer's own chat with
    the business, in the customer's app and account. The platforms offer a
    business no way to delete a customer's chat history: the WhatsApp
    Cloud API cannot delete delivered messages, Messenger and Instagram
    cannot unsend a page's messages through the API, and a Telegram bot can
    delete its own messages only within 48 hours. Media the platforms host
    for a business expire on their own (WhatsApp media URLs within 30
    days). The customer deletes their chat in their app; the erasure and
    the retention purge delete everything the platform itself keeps. No
    job is queued for them (`copies_in` is always None), so an erasure
    never waits on a deletion that cannot happen.
    """

    def __init__(self, processor: SubProcessor) -> None:
        self._processor: SubProcessor = processor

    @property
    def processor(self) -> SubProcessor:
        return self._processor

    @property
    def deletes_copies(self) -> bool:
        return False

    def copies_in(self, scope: ProcessorErasureScope) -> ProcessorErasureScope | None:
        del scope
        return None

    def erase(self, scope: ProcessorErasureScope) -> ErasedRecordCount:
        del scope
        return ErasedRecordCount(0)
