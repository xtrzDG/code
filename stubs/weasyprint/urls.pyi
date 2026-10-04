from collections.abc import Collection

class URLFetcher:
    def __init__(
        self,
        timeout: float = ...,
        allowed_protocols: Collection[str] | None = ...,
        allow_redirects: bool = ...,
        fail_on_errors: bool = ...,
    ) -> None: ...
