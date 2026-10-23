from collections.abc import Sequence

from app.contracts.messaging_clients import EmailSenderClientContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.dto.messaging import EmailAttachment
from app.schemas.typings.messaging.strings import EmailBodyText, EmailSubject
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.utilities.resilience.circuit_calls import call_through_circuit


class CircuitBreakingEmailSenderAdapter(EmailSenderClientContract):
    """
    The platform's e-mail (SMTP: staff notifications, invoices, login
    codes) behind the SMTP circuit breaker: while it is open an e-mail
    fails at once with ProviderCircuitOpenError and no connection is made;
    timeouts and server failures count against the circuit, a refused
    recipient or a login to fix does not.
    """

    def __init__(
        self,
        inner_client: EmailSenderClientContract,
        circuit_breaker: CircuitBreakerContract,
        circuit: CircuitName,
    ) -> None:
        self._inner_client: EmailSenderClientContract = inner_client
        self._circuit_breaker: CircuitBreakerContract = circuit_breaker
        self._circuit: CircuitName = circuit

    def send_email(
        self,
        recipient: EmailAddress,
        subject: EmailSubject,
        text_body: EmailBodyText,
        html_body: EmailBodyText | None,
        attachments: Sequence[EmailAttachment] = (),
    ) -> None:
        call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner_client.send_email(
                recipient, subject, text_body, html_body, attachments
            ),
        )
