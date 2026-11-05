"""Keep abc order."""

from base_typed_string import BaseTypedString


class ClientModuleExclusionReason(BaseTypedString):
    """
    Why a package under `app/clients/` reaches no sub-processor, e.g.
    "Public exchange rates; no personal data is sent".
    """


class ProcessorUseDescription(BaseTypedString):
    """
    What one flow of data to an outside provider is for, in English, e.g.
    "The nightly judge scores a sample of real conversations".
    """


class SubprocessorLocation(BaseTypedString):
    """Where a sub-processor processes the data, in one language."""


class SubprocessorName(BaseTypedString):
    """A sub-processor's name as the DPA table shows it, in one language."""


class SubprocessorPersonalData(BaseTypedString):
    """The personal data a sub-processor receives, in one language."""


class SubprocessorPurpose(BaseTypedString):
    """What a sub-processor does for the service, in one language."""


class SubprocessorTransfer(BaseTypedString):
    """
    The safeguards of a sub-processor's processing as the DPA table names
    them, in one language, e.g. "EU-US Data Privacy Framework; standard
    contractual clauses (2021)".
    """


# Keep abc order for all non example types, if possible.
