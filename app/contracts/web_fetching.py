"""Server-side reading of outside web addresses, guarded against SSRF."""

from typing import Protocol

from app.contracts.client_contract import ClientContract
from app.schemas.dto.web_fetching import FetchedWebResource, WebFetchRequest


class SafeHttpFetcherContract(ClientContract, Protocol):
    """
    The only way the platform reads an address someone else chose (a
    business's website, a menu link). Only public http(s) addresses on
    ports 80 and 443 are fetched: every host is resolved, every address it
    resolves to must be public, and the connection goes to the vetted
    address itself, so a host cannot point somewhere else between the check
    and the request (DNS rebinding). Redirects (at most three) are checked
    the same way.
    """

    def fetch(self, request: WebFetchRequest) -> FetchedWebResource:
        """
        Raises:
            WebFetchError: refused, not fetched, or unusable; its `problem`
                says which.
        """
        raise NotImplementedError
