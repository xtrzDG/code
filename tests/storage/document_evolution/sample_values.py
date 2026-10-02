"""
Valid sample values of the primitives whose format a generic sample cannot
guess, for the golden fixtures (`sample_documents.py`). Keyed by class
name; add an entry when a new constrained primitive appears in a stored
document (the generator names the missing one).
"""

# 2026-09-21T12:26:40Z in UNIX microseconds: every timestamp of a sample.
SAMPLE_MICROSECONDS: int = 1_790_000_000_000_000

CONSTRAINED_TEXT_SAMPLES: dict[str, str] = {
    "AutotestScenarioKey": "booking-happy-path",
    "CountryCode": "GE",
    "CurrencyCode": "GEL",
    "DpaDocumentVersion": "2026-07",
    "E164PhoneNumber": "+995599123456",
    "EmailAddress": "owner@example.com",
    "FactKey": "opening_hours",
    "JobLeaseToken": "0123456789abcdef0123456789abcdef",
    "JobName": "send_booking_reminders",
    "JobPeriodKey": "2026-09-21",
    "JobSerialKey": "business:business_42",
    "KnowledgeAttributeKey": "spice_level",
    "KnowledgeTag": "signature",
    "LanguageTag": "ka",
    "LlmModelId": "gpt-5-mini",
    "LocalDate": "2026-09-21",
    "PaymentCheckoutUrl": "https://pay.example.com/checkout/42",
    "QuestionKey": "parking",
    "TimezoneName": "Asia/Tbilisi",
    "WebLink": "https://example.com/menu",
    "WhatsAppTemplateLanguageCode": "en_US",
    "WhatsAppTemplateName": "booking_reminder",
    "WidgetAccentColor": "#7c5cff",
}

# Unconstrained text that still has a format in practice.
PLAIN_TEXT_SAMPLES: dict[str, str] = {
    "ClientIpAddress": "203.0.113.7",
    "JobPayloadJson": '{"business_id": "business_42"}',
    "LlmProviderPayload": '{"role": "assistant", "content": "Hello"}',
    "LlmToolInputJson": '{"date": "2026-09-21"}',
    "LlmToolResultJson": '{"ok": true}',
    "RecordingStoragePath": "recordings/2026/09/call-42.mp3",
}

INTEGER_SAMPLES: dict[str, int] = {
    "BookingEndsAtUnixSeconds": 1_790_003_600,
    "BookingStartsAtUnixSeconds": 1_790_000_000,
    "ClosingMinuteOfDay": 1_080,
    "MoneyAmountMinor": 1_500,
    "OpeningMinuteOfDay": 540,
    "SlotDurationMinutes": 30,
}
