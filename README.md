# Assistant Workshop

Python-бэкенд AI-помощника для бизнеса: помощник отвечает клиентам ресторанов,
отелей, VR-клубов, салонов и других ниш круглосуточно, на их языке, во всех каналах
(телефон, WhatsApp, Instagram, Messenger, Telegram, чат на сайте), бронирует и
записывает, а сложное передаёт человеку. Бизнес заполняет анкету — помощник
собирается сам.

- Продукт и техническое задание: [`docs/concept.md`](docs/concept.md)
- Архитектура и отличия от стека в ТЗ: [`docs/architecture.md`](docs/architecture.md)
- Правила кода: [`AGENTS.md`](AGENTS.md), [`docs/conventions.md`](docs/conventions.md)
- План работ: [`docs/PLAN.md`](docs/PLAN.md)

Проект сгенерирован из шаблона
[`copier-template-python-backend`](https://github.com/eldenizfamilyanskicode/copier-template-python-backend):
uv, Python 3.14, ruff, mypy и pyright в строгом режиме, pytest, dependency-injector,
типизированные доменные примитивы.

## Любая страна

Владелец из любой страны входит по номеру телефона своей страны и собирает себе
помощника. Номера разбираются для 245 регионов и хранятся в E.164; страна задаёт
языки, валюту, часовой пояс, экстренный номер, способ доставки кода входа и правила
записи звонков; цены хранятся в валюте бизнеса; брони считаются в его часовом поясе.

## Из чего состоит

| Процесс | Точка входа | Что делает |
| --- | --- | --- |
| HTTP API | `app.main:create_application` (фабрика uvicorn) | кабинет, каталог, вебхуки каналов, голоса и оплаты, виджет сайта |
| Фоновый воркер | `python -m app.worker_main` | периодические задачи и очередь задач (автотесты версий помощника) |
| Миграции | `python -m app.adapters.storage.postgres.migrate` | схема Postgres (ЕС) с изоляцией по бизнесу (RLS) |

API и воркер собираются из одного контейнера `app/containers/app.py::AppContainer`
(dependency-injector): клиенты → адаптеры → репозитории, реестры, фасилитаторы,
трансформеры, утилиты → use case → оркестраторы → пайплайны → операторы. Роутеры
всех разделов собирает `app/gateways/http/router_assembly.py`.

## Запуск

```bash
uv sync
cp .env.example .env            # заполнить нужные ключи

# API (http://127.0.0.1:8000/docs — описание OpenAPI)
uv run uvicorn app.main:create_application --factory --reload

# фоновый воркер (останавливается по SIGINT/SIGTERM после текущего такта)
uv run python -m app.worker_main
```

Без `DATABASE_URL` данные хранятся в памяти процесса (удобно для демо и тестов;
API и воркер тогда не видят данных друг друга). Приложение стартует и с пустым
окружением: без ключей внешние сервисы отвечают понятной ошибкой (HTTP 502), а не
ломают запуск.

При старте API прогревает каталог стран, регистрирует вебхук бота платформы в
Telegram (если заданы `TELEGRAM_PLATFORM_BOT_TOKEN`, `ENCRYPTION_KEY` и
`APP_BASE_URL`) и раз в минуту отправляет журнал вызовов модели в Langfuse; при
остановке досылает журнал и закрывает пул Postgres. За прокси запускайте uvicorn с
`--proxy-headers --forwarded-allow-ips=<адрес прокси>`: IP клиента пишется в журнал
аудита.

### Postgres (ЕС)

```bash
export DATABASE_URL=postgresql://app_user:...@host:5432/workshop?sslmode=require
uv run python -m app.adapters.storage.postgres.migrate --dry-run   # что будет применено
uv run python -m app.adapters.storage.postgres.migrate             # применить
```

Миграции из `migrations/` применяются по порядку, каждая в своей транзакции;
запуск безопасен на каждом деплое и из нескольких экземпляров сразу. API, воркер и
миграции должны подключаться ролью без прав суперпользователя и без `BYPASSRLS`,
иначе Postgres не применяет политики изоляции. Подробнее — в
[`migrations/README.md`](migrations/README.md).

### Фоновые задачи

| Задача | Интервал | Что делает |
| --- | --- | --- |
| `purge_expired_recordings` | сутки | удаляет записи и расшифровки звонков старше срока хранения бизнеса |
| `end_trials` | час | завершает пробные периоды (неоплаченные — в льготный период) |
| `enforce_grace_periods` | час, после `end_trials` | по окончании льготного периода включает режим «только заявки» |
| `check_package_usage` | сутки | предупреждает владельца при 80 % пакета минут и диалогов |
| `send_booking_reminders` | 15 минут | напоминает клиентам о бронях в ближайшие 24 часа |
| `flush_llm_traces` | минута | отправляет журнал вызовов модели в Langfuse |

## Окружение

Все переменные с пояснениями — в [`.env.example`](.env.example). Главное:

| Переменная | Без неё |
| --- | --- |
| `APP_ENV` | `development`; в `production` обязателен `ENCRYPTION_KEY`, коды входа не пишутся в лог |
| `APP_BASE_URL` | нельзя опубликовать голосовую версию, подключить Telegram, принять оплату |
| `DATABASE_URL` | хранение в памяти |
| `ENCRYPTION_KEY` | временный ключ: токены каналов не переживут перезапуск |
| `CORS_ALLOWED_ORIGINS` | CORS выключен (виджет сайта разрешает любой источник сам) |
| `LLM_PROVIDER`, `LLM_MODEL_ID`, `OPENAI_API_KEY`, `OPENAI_PROJECT_ID` | ответы модели — ошибка 502 при первом вызове |
| `PLATFORM_ADMIN_EMAILS`, `PLATFORM_ADMIN_PHONE_NUMBERS` | нет админов платформы |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_WEBHOOK_SECRET`, `ELEVENLABS_API_BASE_URL` | голосовой агент не создаётся (502 при публикации версии с голосом) |
| `META_APP_SECRET`, `META_VERIFY_TOKEN`, `WHATSAPP_SYSTEM_USER_TOKEN` | WhatsApp, Instagram и Messenger не принимают вебхуки |
| `TELEGRAM_PLATFORM_BOT_TOKEN`, `WHATSAPP_NOTIFICATION_*` | уведомления сотрудникам только пишутся в лог |
| `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` | нет синхронизации с Google Calendar |
| `FLITT_MERCHANT_ID`, `FLITT_SECRET_KEY` | оплата недоступна (502), вебхук оплаты отклоняется |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | журнал вызовов модели не ведётся |
| `SENTRY_DSN` | неожиданные ошибки только в логе |
| `RECORDINGS_DIRECTORY` | `var/recordings` (записи звонков на этом сервере) |

Адреса для внешних кабинетов (`APP_BASE_URL` + путь):
вебхук Meta — `/v1/channels/meta/webhook`; post-call вебхук ElevenLabs —
`/v1/voice/webhooks/post-call`; redirect URI Google —
`/v1/integrations/google-calendar/callback`; колбэк Flitt — `/v1/payments/flitt/webhook`.

## HTTP API

Кабинет работает с `Authorization: Bearer <токен>` (выдаётся при входе по коду).
Чужой бизнес отвечает `404`, действия только для владельца — `403`, ошибки
проверки — `422` в формате `{"error": ..., "message": ...}`. Полное описание —
`/docs` и `/openapi.json`.

| Раздел | Маршруты |
| --- | --- |
| Здоровье | `GET /healthz` |
| Вход и профиль | `POST /v1/auth/otp/start`, `POST /v1/auth/otp/verify`, `POST /v1/auth/logout`, `GET·PATCH /v1/me` |
| Каталог | `GET /v1/catalog/countries[/{code}]`, `GET /v1/catalog/languages`, `GET /v1/catalog/plans`, `GET /v1/catalog/niches[/{niche}]`, `POST /v1/phone-numbers/parse` |
| Бизнесы и команда | `POST·GET /v1/businesses`, `GET·PATCH /v1/businesses/{id}`, `POST …/members`, `DELETE …/members/{user_id}`, `GET …/call-forwarding-instructions` |
| Данные и договор | `GET·POST …/dpa`, `GET …/audit-log`, `GET …/contacts/{contact_id}/export`, `DELETE …/contacts/{contact_id}` |
| Анкета | `GET …/profile/wizard`, `GET·PUT …/profile`, `PUT …/profile/steps/{step}`, `GET …/profile/gaps` |
| Знания | `GET·POST …/knowledge`, `GET·PATCH·DELETE …/knowledge/{item_id}`, `POST …/knowledge/search`, `POST …/knowledge/import[/confirm]` |
| Ресурсы и расписание | `GET·POST …/resources`, `PATCH …/resources/{id}`, `GET·POST …/schedule-exceptions`, `DELETE …/schedule-exceptions/{id}` |
| Брони, заявки, передачи | `GET …/availability`, `GET·POST …/bookings`, `PATCH …/bookings/{id}`, `POST …/bookings/{id}/cancel`, `POST …/bookings/{id}/reschedule`, `GET …/leads`, `PATCH …/leads/{id}`, `GET …/handoffs`, `POST …/handoffs/{id}/resolve`, `GET …/unanswered-questions`, `POST …/unanswered-questions/{id}/answer`, `GET …/dashboard` |
| Google Calendar | `GET …/integrations/google-calendar/connect-url`, `DELETE …/integrations/google-calendar`, `GET /v1/integrations/google-calendar/callback` |
| Разговоры | `GET …/conversations[/{id}]`, `POST …/test-chat` |
| Сборка помощника | `POST·GET …/assistant-versions`, `GET …/assistant-versions/{id}[/autotest-run]`, `POST …/assistant-versions/{id}/autotests`, `POST …/assistant-versions/{id}/publish`, `POST …/assistant-versions/{id}/rollback` |
| Каналы (кабинет) | `GET …/channels`, `PUT·DELETE …/channels/{channel}`, `GET …/channels/web/snippet`, `POST …/manager-contacts/telegram-link` |
| Вебхуки и виджет | `POST /v1/channels/telegram/{channel_id}/webhook`, `GET·POST /v1/channels/meta/webhook`, `POST /v1/channels/telegram-platform/webhook`, `GET /v1/widget/{id}/config`, `POST /v1/widget/{id}/messages` |
| Голос | `POST /v1/voice/tools/{tool}`, `POST /v1/voice/webhooks/conversation-initiation`, `POST /v1/voice/webhooks/post-call` |
| Оплата | `GET …/billing`, `POST …/billing/trial`, `POST …/billing/plan`, `POST …/billing/cancel`, `POST …/billing/checkout`, `POST /v1/payments/flitt/webhook` |
| Админка платформы | `GET /v1/admin/clients[/{business_id}]`, `POST /v1/admin/clients/{business_id}/open` |

`…` — это `/v1/businesses/{business_id}`.

Автотесты не выполняются внутри запроса: `POST …/assistant-versions` и
`POST …/assistant-versions/{id}/autotests` запускают прогон (версия — `testing`,
прогон — `running`, ответ `202` для повторного прогона), а играет его фоновый воркер.
Ход прогона виден в `GET …/assistant-versions/{id}/autotest-run`. Статус `ready`
даёт только прогон по всем языкам и сценариям версии. Выйти в эфир можно с
пробным периодом или оплаченной подпиской, принятым DPA, контактом менеджера и
без блокирующих пробелов анкеты.

## Проверки

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pyright
uv run pytest
```

Сквозные тесты (`tests/e2e/`) собирают настоящий `AppContainer` и подменяют только
края: настройки, часы, модель (`ScriptedLlmAdapter`), доставку кодов и внешние
HTTP-сервисы (`httpx.MockTransport`). Тесты хранилища поднимают локальный
Postgres 16, если он установлен, и пропускаются без него.
