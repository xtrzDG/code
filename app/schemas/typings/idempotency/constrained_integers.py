"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class StoredResponseStatus(BaseConstrainedTypedInt):
    """
    The HTTP status of a stored answer to a creating request: only a
    success (2xx) is kept and replayed; a refusal or a failure releases the
    key, so the retry runs again.
    """

    ge = 200
    le = 299


# Keep abc order for all non example types, if possible.
