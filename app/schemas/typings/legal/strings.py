"""Keep abc order."""

from base_typed_string import BaseTypedString


class ClientModuleExclusionReason(BaseTypedString):
    """
    Why a package under `app/clients/` reaches no sub-processor, e.g.
    "Public exchange rates; no personal data is sent".
    """


class SubprocessorLocation(BaseTypedString):
    """Where a sub-processor processes the data, in one language."""


class SubprocessorName(BaseTypedString):
    """A sub-processor's name as the DPA table shows it, in one language."""


class SubprocessorPersonalData(BaseTypedString):
    """The personal data a sub-processor receives, in one language."""


class SubprocessorPurpose(BaseTypedString):
    """What a sub-processor does for the service, in one language."""


# Keep abc order for all non example types, if possible.
