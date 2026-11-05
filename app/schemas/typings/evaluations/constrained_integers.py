"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class LlmCassetteFormatVersion(BaseConstrainedTypedInt):
    """Version of the cassette file layout (evals/cassettes/*.json)."""

    ge = 1


class LlmCassetteSampleIndex(BaseConstrainedTypedInt):
    """
    Which sample of a repeated scenario a recorded model call belongs to
    (0 for the first; pass^k plays every scenario k times).
    """

    ge = 0
    le = 99
