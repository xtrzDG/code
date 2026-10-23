from enum import StrEnum


class CircuitState(StrEnum):
    """
    A circuit breaker's state: CLOSED lets calls through and counts their
    failures; OPEN refuses calls until its wait is over; HALF_OPEN lets one
    trial call through, whose outcome closes or opens the circuit again.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class OutboundProvider(StrEnum):
    """
    An external provider the platform sends through. Each has its own
    circuit breaker (`provider:<value>`, opened by its own outages) and its
    own share of a worker's outbound threads, so one provider's brownout
    holds up neither the others nor the platform alerts.

    META carries WhatsApp, Messenger and Instagram; TELEGRAM the businesses'
    bots; PLATFORM_BOT the platform's Telegram bot (staff notifications and
    alerts); TWILIO_SMS and SMTP staff SMS and e-mail; WEB_PUSH the cabinet's
    devices (a share of the lane, no circuit: its endpoints are many
    services); FLITT and STRIPE payments (a circuit each; they send no
    outbox messages).
    """

    META = "meta"
    TELEGRAM = "telegram"
    PLATFORM_BOT = "platform_bot"
    TWILIO_SMS = "twilio_sms"
    SMTP = "smtp"
    WEB_PUSH = "web_push"
    FLITT = "flitt"
    STRIPE = "stripe"
