"""Settings of the end-to-end workshop: start time, URLs and environment."""

from datetime import UTC, datetime
from typing import Any

# Monday 2026-10-05 08:00 UTC: 12:00 in Tbilisi, 10:00 in Rome.
START: datetime = datetime(2026, 10, 5, 8, 0, tzinfo=UTC)
API_BASE_URL: str = "https://api.workshop.example"
CABINET_ORIGIN: str = "https://cabinet.workshop.example"
ADMIN_EMAIL: str = "admin@workshop.example"
PLATFORM_BOT_TOKEN: str = "123456:platform-bot-token"
ELEVENLABS_BASE_URL: str = "https://elevenlabs.test"
E2E_ENVIRONMENT: dict[str, str] = {
    "APP_ENV": "test",
    "APP_BASE_URL": API_BASE_URL,
    "CORS_ALLOWED_ORIGINS": CABINET_ORIGIN,
    "ENCRYPTION_KEY": "e2e-encryption-secret-0123456789abcdef",  # gitleaks:allow
    "LLM_PROVIDER": "scripted",
    # Every message answered at once (the movable clock never runs on by
    # itself, so a burst would wait forever).
    "MESSAGE_COALESCE_SECONDS": "0",
    "PLATFORM_ADMIN_EMAILS": ADMIN_EMAIL,
    "TELEGRAM_PLATFORM_BOT_TOKEN": PLATFORM_BOT_TOKEN,
    "ELEVENLABS_API_KEY": "xi-e2e-key",
    "ELEVENLABS_WEBHOOK_SECRET": "elevenlabs-webhook-secret-e2e",  # gitleaks:allow
}

type JsonObject = dict[str, Any]
