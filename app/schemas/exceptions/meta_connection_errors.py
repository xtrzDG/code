"""Why a WhatsApp number from Embedded Signup could not be put to work."""

from app.schemas.exceptions.application_errors import ConflictError


class WhatsAppPinMismatchError(ConflictError):
    """
    The number was registered for the Cloud API before, with a two-step
    verification PIN that is not the one the platform keeps for it (Graph
    error 133005): its owner turns two-step verification off in WhatsApp
    Manager (or tells the PIN) before it can be registered again.
    """
