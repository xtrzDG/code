"""
Valid sample values of the primitives whose format a generic sample cannot
guess, for the golden fixtures (`sample_documents.py`). Keyed by class
name; add an entry when a new constrained primitive appears in a stored
document (the generator names the missing one).
"""

# 2026-09-21T12:26:40Z in UNIX microseconds: every timestamp of a sample.
SAMPLE_MICROSECONDS: int = 1_790_000_000_000_000

CONSTRAINED_TEXT_SAMPLES: dict[str, str] = {
    "AcquisitionSourceTag": "qr-tables",
    "AutotestCaseQuestion": "Do you have a vegetarian menu?",
    "AutotestExpectedText": "vegetarian",
    "AutotestScenarioKey": "booking-happy-path",
    "BackupObjectKey": "workshop/2026/09/workshop-20260921T122640Z.pgdump.age",
    "CabinetRoutePattern": "/b/[businessId]/inbox",
    "BusinessPublicSlug": "cafe-batumi",
    "CabinetDeepLink": (
        "https://app.example.com/n/AQ3xL8nYtQ2bS0pK9mVwZcRj5uHfE1gDaB7iO4lN6eT"
    ),
    "CountryCode": "GE",
    "CurrencyCode": "GEL",
    "CurrencyPairCode": "EUR/GEL",
    "DpaDocumentVersion": "2026-07",
    "GoLiveCheckDetail": "no_opening_hours",
    "IncidentTitle": "WhatsApp replies delayed",
    "InstagramUsername": "cafe.batumi",
    "E164PhoneNumber": "+995599123456",
    "EmailAddress": "owner@example.com",
    "ErrorReasonDetail": "http_status:404",
    "ExchangeRateDate": "2026-10-02",
    "ExchangeRateValue": "2.9563",
    "FactKey": "opening_hours",
    "JobLeaseToken": "0123456789abcdef0123456789abcdef",
    "JobName": "send_booking_reminders",
    "JobPeriodKey": "2026-09-21",
    "JobSerialKey": "business:business_42",
    "KnowledgeAttributeKey": "spice_level",
    "KnowledgeTag": "signature",
    "LandingPath": "/c/cafe-batumi",
    "LanguageTag": "ka",
    "LlmModelId": "gpt-5-mini",
    "LocalDate": "2026-09-21",
    "MessageMediaType": "audio/ogg",
    "LocalTimeOfDay": "22:00",
    "ManagerTelegramUsername": "nino_k",
    "MetaPageUsername": "cafebatumi",
    "PaymentCheckoutUrl": "https://pay.example.com/checkout/42",
    "PushAuthSecret": "BTBZMqHH6r4Tts7J_aSIgg",
    "PushEndpointUrl": "https://push.example.com/send/c1d2e3",
    "PushNotificationTag": "handoff:handoff_42",
    "PushPublicKey": (
        "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4"
    ),
    "QuestionKey": "parking",
    "QuickReplyShortcut": "hours",
    "ReferralCode": "partner-42",
    "ReferrerHost": "www.google.com",
    "ReleaseVersion": "4718714c0f2e9a1b",
    "ReviewLinkToken": "q3Jd8sLq0Pz-Xb7W2nVc1A",
    "SeasonDay": "06-15",
    "SessionUserAgent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "SignupSourceTag": "qr",
    "SupportAccessReason": "Owner asked why bookings stopped",
    "TimezoneName": "Asia/Tbilisi",
    "UtmCampaign": "autumn-launch",
    "UtmContent": "hero-button",
    "UtmMedium": "social",
    "UtmSource": "instagram",
    "UtmTerm": "ai receptionist",
    "ValueReportPeriodKey": "2026-W38",
    "WebLink": "https://example.com/menu",
    "WhatsAppTemplateLanguageCode": "en_US",
    "WhatsAppNumberDigits": "995599123456",
    "WhatsAppTemplateName": "booking_reminder",
    "WidgetAccentColor": "#7c5cff",
    "WorkerHostName": "srv-workshop-worker-1",
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
    "BookingValueMinor": 4_500,
    "BufferMinutes": 15,
    "ClosingMinuteOfDay": 1_080,
    "ExchangeRateDayNumber": 20_261_002,
    "MoneyAmountMinor": 1_500,
    "NightlyRateMinor": 25_000,
    "OpeningMinuteOfDay": 540,
    "ServiceDurationMinutes": 45,
    "SlotDurationMinutes": 30,
}
