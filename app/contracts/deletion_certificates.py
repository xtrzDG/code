"""The deletion certificate an owner downloads once their business is gone."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.typings.business_closures.strings import DeletionCertificateHtml


class DeletionCertificateRendererContract(AdapterContract, Protocol):
    def render(self, html: DeletionCertificateHtml) -> bytes:
        """
        The certificate's page as a PDF.

        Raises:
            ExternalServiceError: the PDF engine failed.
        """
        raise NotImplementedError
