"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class ClientModuleName(BaseConstrainedTypedString):
    """
    The name of one package under `app/clients/`: the code that talks to
    one outside service (its sub-processor, or none for public data).

    Example:
        module = ClientModuleName("openai")
    """

    min_length = 2
    max_length = 40
    pattern = r"^[a-z][a-z0-9_]*$"


class LegalDocumentVersion(BaseConstrainedTypedString):
    """
    Version of a platform legal text (terms of service, privacy policy,
    cookie statement): the day it takes effect, ISO 8601 "YYYY-MM-DD", the
    date in its file name (docs/legal/terms-2026-10-05.en.md).

    Example:
        version = LegalDocumentVersion("2026-10-05")
    """

    min_length = 10
    max_length = 10
    pattern = r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"


class RepositoryPath(BaseConstrainedTypedString):
    """
    A file or directory of this repository, relative to its root, that
    implements a promise of the legal texts (a security measure of DPA
    section 9); tests/legal checks that it exists.

    Example:
        path = RepositoryPath("app/utilities/security/totp_codes.py")
    """

    min_length = 3
    max_length = 160
    pattern = r"^(?!/)(?!.*\.\.)[A-Za-z0-9_.\-/\[\]]+$"


class SecurityMeasureKey(BaseConstrainedTypedString):
    """
    One security measure of the DPA's section 9 as the registry names it.

    Example:
        key = SecurityMeasureKey("two_factor_sign_in")
    """

    min_length = 2
    max_length = 40
    pattern = r"^[a-z][a-z0-9_]*$"


class SubprocessorChangeDate(BaseConstrainedTypedString):
    """
    A day in the life of the sub-processor list, ISO 8601 "YYYY-MM-DD":
    when a sub-processor joined or leaves it, or when that change was
    announced.

    Example:
        added_on = SubprocessorChangeDate("2026-12-01")
    """

    min_length = 10
    max_length = 10
    pattern = r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"


class SubprocessorChangeKey(BaseConstrainedTypedString):
    """
    One announced change of the sub-processor list: the sub-processor, what
    happens to it and the day it takes effect. Owners are told about each
    key once.

    Example:
        key = SubprocessorChangeKey("anthropic-added-2026-12-01")
    """

    min_length = 16
    max_length = 80
    pattern = r"^[a-z][a-z0-9_]*-(added|removed)-[0-9]{4}-[0-9]{2}-[0-9]{2}$"


class SubprocessorKey(BaseConstrainedTypedString):
    """
    A sub-processor of the platform as the registry names it, the same in
    every language.

    Example:
        key = SubprocessorKey("object_storage")
    """

    min_length = 2
    max_length = 40
    pattern = r"^[a-z][a-z0-9_]*$"


# Keep abc order for all non example types, if possible.
