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
| Фоновый воркер | `python -m app.worker_main` | периодические задачи и очередь задач |
| Миграции | `python -m app.adapters.storage.postgres.migrate` | схема Postgres (ЕС) с изоляцией по бизнесу (RLS) |

Все три собираются в один образ (`Dockerfile`, роли `api`, `worker`, `migrate`);
кабинет владельца на Next.js — отдельный образ `web/Dockerfile`.

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

### Всё сразу в Docker

```bash
cp .env.example .env            # необязательно: ключи внешних сервисов
docker compose up --build       # кабинет http://localhost:3000, API http://localhost:8000
```

`docker-compose.yml` поднимает Postgres 16, одноразовые миграции (`migrate`), API,
воркер и кабинет (`web`, `BACKEND_URL=http://api:8000`, `COOKIE_SECURE=false` для
http). По умолчанию `APP_ENV=development`, поэтому коды входа без настроенного
провайдера появляются в логе API: `docker compose logs -f api`. Приложение
подключается ролью `workshop` без прав суперпользователя (её создаёт
`docker/postgres/init`), так что изоляция RLS работает и локально. Задайте в `.env`
постоянный `ENCRYPTION_KEY` (например, `python -c "import secrets;
print(secrets.token_urlsafe(32))"`), иначе API и воркер шифруют токены каналов
разными временными ключами. Порты меняются через `API_PORT` и `WEB_PORT`;
`docker compose down -v` удаляет и данные.

Образ бэкенда отдельно:

```bash
docker build -t assistant-workshop-backend .
docker run --env-file .env -p 8000:8000 assistant-workshop-backend api
docker run --env-file .env assistant-workshop-backend worker
docker run --env-file .env assistant-workshop-backend migrate --dry-run
```

Образ работает от непривилегированного пользователя, по умолчанию `APP_ENV=production`
(нужен `ENCRYPTION_KEY`), слушает `$PORT` (8000), проверка здоровья — `GET /healthz`.
API запускается с `--proxy-headers`; адреса доверенных прокси — в
`FORWARDED_ALLOW_IPS` (по умолчанию 127.0.0.1).

### Деплой на Render (ЕС)

`render.yaml` — Blueprint: в Render нажмите **New → Blueprint** и выберите
репозиторий. Всё создаётся во Франкфурте:

| Ресурс | Что это |
| --- | --- |
| `workshop-db` | управляемый Postgres 16, доступен только изнутри Render |
| `workshop-api` | API из `Dockerfile`; перед каждым деплоем `workshop migrate`, проверка `/healthz` |
| `workshop-worker` | фоновый воркер из того же образа |
| `workshop-cabinet` | кабинет из `web/Dockerfile` |

При создании Render спросит секреты (`sync: false`): ключи модели, провайдеров
кодов входа, Meta, Telegram, ElevenLabs, Flitt, Langfuse, Sentry — ненужные оставьте
пустыми. Воркер берёт значения у API, `ENCRYPTION_KEY` генерируется один раз (не
меняйте его). После первого деплоя укажите `APP_BASE_URL` (публичный адрес API,
например `https://workshop-api.onrender.com`) и `BACKEND_URL` кабинета (внутренний
адрес API из Render: `http://<хост>:8000`, или публичный). Адреса вебхуков для
внешних кабинетов — в разделе «Окружение».

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

## Коды входа

Код приходит через первый канал из списка страны номера (SMS, WhatsApp, Telegram),
для которого настроен провайдер; запрошенный пользователем канал идёт первым. Если
провайдер отказал, тот же код уходит следующим каналом, а в ответе указан канал,
который сработал. Вход по почте требует SMTP.

| Канал | Провайдер | Переменные |
| --- | --- | --- |
| SMS | Twilio Programmable Messaging | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` или `TWILIO_MESSAGING_SERVICE_SID` |
| Telegram | Telegram Gateway API (`sendVerificationMessage`, платно за доставленный код) | `TELEGRAM_GATEWAY_API_TOKEN` |
| WhatsApp | шаблон категории «authentication» в WhatsApp Cloud API (код в тексте и кнопке «скопировать») | `WHATSAPP_OTP_PHONE_NUMBER_ID`, `WHATSAPP_OTP_TEMPLATE`, `WHATSAPP_OTP_TEMPLATE_LANGUAGES`, `WHATSAPP_OTP_ACCESS_TOKEN` (по умолчанию `WHATSAPP_SYSTEM_USER_TOKEN`) |
| Почта | любой SMTP (STARTTLS или TLS) | `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` |

Тексты SMS и писем — на языке пользователя (английский, русский, грузинский,
украинский, турецкий, иврит, арабский, немецкий, французский, испанский; иначе
английский); сообщения Telegram и WhatsApp пишут сами платформы. Провайдер
настраивается целиком или никак: неполные настройки останавливают запуск.

В `development` и `test` каналы без провайдера пишут код в лог (`OTP_LOG_CODES`, по
умолчанию включено). В `production` коды никогда не пишутся в лог (`OTP_LOG_CODES=true`
— ошибка запуска), канал без провайдера не предлагается, а без единого провайдера
API при старте пишет ошибку, и вход отвечает 502 с объяснением.

## Виджет сайта

Кабинет выдаёт код для сайта (`GET …/channels/web/snippet`):

```html
<script src="https://<APP_BASE_URL>/widget.js" data-tenant="<id бизнеса>" async></script>
```

`/widget.js` — скрипт без зависимостей и без cookie: кнопка и окно чата в shadow
DOM (стили сайта и виджета не смешиваются), язык посетителя из браузера среди
языков бизнеса, письмо справа налево для иврита и арабского, индикатор набора,
ошибки с повтором, полноэкранное окно на телефоне, управление с клавиатуры.
Посетителя узнаёт случайный ключ в `localStorage`, там же — последние сообщения.
Необязательные атрибуты: `data-color="#0f766e"`, `data-position="left"`,
`data-language="ka"`, `data-open="true"`. Сайту со строгой CSP нужно разрешить
адрес API в `script-src` и `connect-src`. Страница
`GET /widget/demo?business_id=…` показывает виджет как на сайте, даже пока чат
выключен (предпросмотр для владельца и UI-тестов).

## Окружение

Все переменные с пояснениями — в [`.env.example`](.env.example). Главное:

| Переменная | Без неё |
| --- | --- |
| `APP_ENV` | `development`; в `production` обязателен `ENCRYPTION_KEY`, коды входа не пишутся в лог |
| `TWILIO_*`, `TELEGRAM_GATEWAY_API_TOKEN`, `WHATSAPP_OTP_*`, `SMTP_*` | коды входа только в логе (вне `production`); см. «Коды входа» |
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
| Вебхуки и виджет | `POST /v1/channels/telegram/{channel_id}/webhook`, `GET·POST /v1/channels/meta/webhook`, `POST /v1/channels/telegram-platform/webhook`, `GET /v1/widget/{id}/config`, `POST /v1/widget/{id}/messages`, `GET /widget.js`, `GET /widget/demo` |
| Голос | `POST /v1/voice/tools/{tool}`, `POST /v1/voice/webhooks/conversation-initiation`, `POST /v1/voice/webhooks/post-call` |
| Оплата | `GET …/billing`, `POST …/billing/trial`, `POST …/billing/plan`, `POST …/billing/cancel`, `POST …/billing/checkout`, `POST /v1/payments/flitt/webhook` |
| Админка платформы | `GET /v1/admin/clients[/{business_id}]`, `POST /v1/admin/clients/{business_id}/open` |

`…` — это `/v1/businesses/{business_id}`.

## Проверки

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pyright
uv run pytest
```

CI (`.github/workflows/ci.yml`) прогоняет те же проверки бэкенда (с Postgres 16 из
пакетов Ubuntu), линтер, проверку типов, тесты и сборку кабинета (`web/`), собирает
оба Docker-образа и проверяет `docker-compose.yml`.

Сквозные тесты (`tests/e2e/`) собирают настоящий `AppContainer` и подменяют только
края: настройки, часы, модель (`ScriptedLlmAdapter`), доставку кодов и внешние
HTTP-сервисы (`httpx.MockTransport`). Тесты хранилища поднимают локальный
Postgres 16, если он установлен, и пропускаются без него.
