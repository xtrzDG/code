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
- Запуск для владельца: аккаунты, ключи, Render, проверка —
  [`docs/LAUNCH.md`](docs/LAUNCH.md)

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
| Фоновый воркер | `python -m app.worker_main` | периодические задачи и очередь задач по полосам (ответы на сообщения из входящих, доставка исходящих, автотесты версий помощника и др.); воркеров может быть сколько угодно; в разработке без Postgres — поток внутри API (`EMBEDDED_WORKER`) |
| Миграции | `python -m app.gateways.cli.migrate` | схема Postgres (ЕС) с изоляцией по бизнесу (RLS) |
| Миграция документов | `python -m app.gateways.cli.migrate_documents` | переписывает сохранённые документы старых версий схемы в текущую (после деплоя, см. [`docs/operations/deploys.md`](docs/operations/deploys.md)) |
| Нагрузочные данные | `python -m app.gateways.cli.seed_load` | заполняет базу для нагрузочных тестов (500 бизнесов, 2 млн сообщений, 200 тыс. броней) и пишет манифест для k6; не в production, см. [`docs/operations/capacity.md`](docs/operations/capacity.md) |

Все они собираются в один образ (`Dockerfile`, роли `api`, `worker`, `migrate`,
`migrate-documents`, `seed-load`);
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

# фоновый воркер (по SIGINT/SIGTERM даёт текущим задачам до 25 секунд);
# с Postgres — отдельным процессом, без DATABASE_URL он уже работает внутри API
uv run python -m app.worker_main
```

Без `DATABASE_URL` данные хранятся в памяти процесса (удобно для демо и тестов).
Отдельный воркер тогда не видит данных API, поэтому в разработке
(`APP_ENV=development`) без `DATABASE_URL` API сам запускает фоновый воркер в
своём потоке: автотесты версий доходят до конца, напоминания уходят, и второй
процесс не нужен. Это `EMBEDDED_WORKER`:

| Значение | Что делает |
| --- | --- |
| `auto` (по умолчанию) | воркер внутри API только при `APP_ENV=development` и пустом `DATABASE_URL` |
| `true` | всегда внутри API (например, разработка с локальным Postgres без отдельного воркера); в продакшене запрещено — там воркеры работают отдельным сервисом (`workshop worker`), чтобы автотесты не тормозили API |
| `false` | никогда; запускайте `python -m app.worker_main` |

Воркеров может быть несколько (процессы, экземпляры сервиса, встроенный рядом с
отдельным — с общим Postgres): задача берётся из очереди с арендой
(`FOR UPDATE SKIP LOCKED`), пока она выполняется, воркер продлевает аренду, а
задачу упавшего воркера после конца аренды подхватывает другой. У каждой полосы
(`inbound`, `outbound`, `default`, `autotests`) свои потоки
(`WORKER_LANE_CONCURRENCY`), поэтому долгий прогон автотестов не задерживает
напоминания и ответы клиентам; автотесты одного бизнеса идут по одному.
Периодические задачи работают в своём потоке и выполняются один раз за период
(день, ISO-неделя или интервал) на все воркеры — запись в `periodic_job_runs`,
поэтому перезапуск не повторяет сегодняшние напоминания и сводки. Завершённые
задачи хранятся 30 дней; «мёртвые» платформенный админ видит и перезапускает
через `GET /v1/admin/jobs?status=dead` и `POST /v1/admin/jobs/{job_id}/retry`
(или `…/discard`), с записью в журнал аудита. При остановке воркер даёт
текущим задачам до 25 секунд.

Приложение стартует и с пустым окружением: без ключей внешние сервисы отвечают
понятной ошибкой (HTTP 502), а не ломают запуск.

При старте API прогревает каталог стран, регистрирует вебхук бота платформы в
Telegram (если заданы `TELEGRAM_PLATFORM_BOT_TOKEN`, `ENCRYPTION_KEY` и
`APP_BASE_URL`), с `SEED_DEMO_DATA=true` создаёт демо-бизнесы, раз в минуту отправляет журнал вызовов модели в Langfuse и, если
включён `EMBEDDED_WORKER`, запускает фоновый воркер; при остановке останавливает
воркер, досылает журнал и закрывает пул Postgres. За прокси запускайте uvicorn с
`--proxy-headers --forwarded-allow-ips=<адрес прокси>`: IP клиента пишется в журнал
аудита.

### Демо-данные

Чтобы пустая установка выглядела как живой продукт (для показа и скриншотов),
запустите API с `SEED_DEMO_DATA=true`:

```bash
APP_ENV=development SEED_DEMO_DATA=true uv run uvicorn app.main:create_application --factory
```

При старте API один раз (повторный запуск ничего не дублирует — и в памяти, и в
Postgres) создаёт демо-владельца (`+995 555 00 00 01`, `demo@example.com`) и
сотрудника (`+995 555 00 00 02`), а у владельца — два бизнеса:

- ресторан «Mtsvane Ezo» в Тбилиси (Грузия, лари; гости пишут на грузинском,
  русском, английском, иврите и арабском): заполненная анкета, меню с ценами,
  столы, часы и особые дни, опубликованная версия помощника с пройденными
  автотестами, Telegram, WhatsApp, чат на сайте и телефон, около 40 переписок за
  месяц с вызовами инструментов, звонок с расшифровкой, брони (предстоящие,
  прошедшие, неявки, отмены), заявки, передачи сотрудникам, вопросы без ответа,
  пробный период и пакет, израсходованный примерно на 80 %;
- салон красоты «Studio Lindenblatt» в Берлине (Германия, евро, немецкий и
  английский): услуги, мастера, брони и несколько переписок.

Код входа в разработке пишется в лог API. Чтобы войти и в «Админку», добавьте
`PLATFORM_ADMIN_PHONE_NUMBERS=+995555000001`. Учётные данные каналов выдуманы;
при заполнении ни один провайдер не вызывается. В `production` переменная
запрещена: API не запустится.

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
`docker/postgres/init`), так что изоляция RLS работает и локально. API и воркер
шифруют токены каналов одним ключом `ENCRYPTION_KEY`; значение по умолчанию в
`docker-compose.yml` общеизвестно и годится только для этой машины — перед
подключением настоящих каналов задайте в `.env` свой (например, `python -c "import
secrets; print(secrets.token_urlsafe(32))"`) и не меняйте его потом; с
`APP_ENV=production` API это значение не принимает. Порты меняются через `API_PORT` и
`WEB_PORT` (адреса `APP_BASE_URL` и `CABINET_BASE_URL` следуют за ними); вход через
кабинет локально идёт с одного адреса контейнера, поэтому Compose поднимает лимит
кодов с адреса до 100 в час. `docker compose down -v` удаляет и данные. Пошагово,
со входом без SMS, — в [`docs/LAUNCH.md`](docs/LAUNCH.md).

Образ бэкенда отдельно:

```bash
docker build -t assistant-workshop-backend .
docker run --env-file .env -p 8000:8000 assistant-workshop-backend api
docker run --env-file .env assistant-workshop-backend worker
docker run --env-file .env assistant-workshop-backend migrate --dry-run
```

Образ работает от непривилегированного пользователя, по умолчанию `APP_ENV=production`
(нужен `ENCRYPTION_KEY`), слушает `$PORT` (8000), проверка здоровья — `GET /healthz`
(жив ли процесс), готовность к трафику — `GET /readyz` (см. «Наблюдение и устойчивость»).
API запускается с `--proxy-headers`; адреса доверенных прокси — в
`FORWARDED_ALLOW_IPS` (по умолчанию 127.0.0.1). Указывайте диапазоны адресов
прокси, а не `*`: со `*` uvicorn берёт самый левый адрес `X-Forwarded-For`,
который подставляет сам клиент, и IP в журнале аудита можно подделать.

### Наблюдение и устойчивость

- **Здоровье.** `GET /healthz` — асинхронный, без потоков и базы: отвечает,
  даже когда все `THREADPOOL_SIZE` потоков запросов заняты. `GET /readyz`
  (по нему Render направляет трафик) — `select 1` с таймаутом 2 с, все
  миграции этой сборки применены, свободное соединение из пула; иначе 503.
  Возраст последнего пульса воркера (`worker_heartbeats`, миграция 1030;
  воркер пишет его каждый такт с версией и итогами периодических задач)
  виден в ответе, но трафик не останавливает.
- **Таймауты.** Каждое соединение с Postgres: `statement_timeout=10s` и
  `idle_in_transaction_session_timeout=30s` (`workshop migrate` — 30 мин и
  5 мин). Вызов модели в чате — `LLM_CALL_TIMEOUT_SECONDS` (25 с) и одна
  повторная попытка; инструмент голосового агента отвечает не дольше 8 с
  (иначе агент получает ошибку и говорит звонящему, что коллега перезвонит).
- **Остановка.** uvicorn даёт открытым запросам 25 с
  (`--timeout-graceful-shutdown 25`, keep-alive 5 с), воркер — 25 с
  выполняющимся задачам; Render ждёт 30 и 60 с (`maxShutdownDelaySeconds`).
- **Логи.** `LOG_FORMAT=json` (по умолчанию в `production`): одна строка JSON
  на запись — время, уровень, логгер, поток, текст и `request_id`,
  `business_id`, `conversation_id`, `channel`, `job_name`, `job_id`; тот же
  `X-Request-ID` возвращается в ответе. Токены ботов в адресах скрыты.
- **Sentry.** `SENTRY_DSN`: ошибки API и воркера с версией сборки
  (`RENDER_GIT_COMMIT`/`APP_RELEASE`) и тегами контекста, доля трассировок
  `SENTRY_TRACES_SAMPLE_RATE`, проверки Sentry Crons вокруг каждой
  периодической задачи (пропущенный или упавший запуск видно в Sentry),
  ошибки виджета сайтов (`POST /v1/widget/errors`) и кабинета
  (`SENTRY_DSN` сервиса `workshop-cabinet`, `web/README.md`). Без тел
  запросов, пользователей и breadcrumbs.

### Деплой на Render (ЕС)

`render.yaml` — Blueprint: в Render нажмите **New → Blueprint** и выберите
репозиторий (пошагово, со списком ключей и адресов вебхуков, — в
[`docs/LAUNCH.md`](docs/LAUNCH.md)). Всё создаётся во Франкфурте:

| Ресурс | Что это |
| --- | --- |
| `workshop-db` | управляемый Postgres 16, доступен только изнутри Render |
| `workshop-api` | API из `Dockerfile`; перед каждым деплоем `workshop migrate`, проверка готовности `/readyz`, 30 с на завершение запросов при остановке |
| `workshop-worker` | фоновый воркер из того же образа; 60 с на завершение задач при остановке |
| `workshop-cabinet` | кабинет из `web/Dockerfile` |

При создании Render спросит секреты (`sync: false`): провайдер и ключи модели,
провайдеров кодов входа, Meta (и шаблоны WhatsApp), Telegram, ElevenLabs, Flitt,
Langfuse, Sentry — ненужные оставьте пустыми. Воркер копирует у API только ключи,
перечисленные в `render.yaml`; остальные переменные (тонкая настройка модели,
`OPENAI_BASE_URL`, `LANGFUSE_HOST`, `RECORDING_RETENTION_DAYS`, `WORKER_POLL_SECONDS`
и т. п.) задавайте в группе окружения `workshop-backend` — её читают и API, и воркер.
`ENCRYPTION_KEY` генерируется один раз (не меняйте его). После первого деплоя
укажите `APP_BASE_URL` (публичный адрес API,
например `https://workshop-api.onrender.com`), `CABINET_BASE_URL` (публичный адрес
кабинета, например `https://workshop-cabinet.onrender.com`: туда Google Calendar и
страница оплаты возвращают владельца), `CORS_ALLOWED_ORIGINS` API (тот же адрес
кабинета) и `BACKEND_URL` кабинета (внутренний
адрес API из Render: `http://<хост>:8000`; не публичный — иначе все входы придут с
одного адреса Render и упрутся в лимит кодов с одного адреса). Адреса вебхуков для
внешних кабинетов — в разделе «Окружение».

Деплой только после проверок: сервисы `render.yaml` следуют ветке `release`
и разворачивают коммит, только когда все проверки GitHub по нему зелёные
(`autoDeployTrigger: checksPass`). `render.staging.yaml` — такое же окружение
staging на ветке `main` с отдельной базой и группой `workshop-staging`
(`LLM_PROVIDER=scripted`: фиксированные ответы без модели). После каждого
деплоя `.github/workflows/deploy-smoke.yml` прогоняет `scripts/smoke.sh`;
зелёный staging переносит коммит в `release`. Правила изменения схемы
(сначала расширить, потом сузить), миграция документов и откат — в
[`docs/operations/deploys.md`](docs/operations/deploys.md).

### Postgres (ЕС)

```bash
export DATABASE_URL=postgresql://app_user:...@host:5432/workshop?sslmode=require
uv run python -m app.gateways.cli.migrate --dry-run   # что будет применено
uv run python -m app.gateways.cli.migrate             # применить
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
| `purge_finished_jobs` | сутки | удаляет выполненные, «мёртвые» и отброшенные задачи очереди и записи периодических запусков старше 30 дней |
| `flush_llm_traces` | минута | отправляет журнал вызовов модели в Langfuse (в каждом процессе воркера) |
| `purge_stale_rows` | сутки | удаляет истёкшие сессии, коды входа старше суток и квитанции вебхуков старше 30 дней |

## Коды входа

Код приходит через первый канал из списка страны номера (SMS, WhatsApp, Telegram),
для которого настроен провайдер; запрошенный пользователем канал идёт первым. Если
провайдер отказал, тот же код уходит следующим каналом, а в ответе указан канал,
который сработал. Вход по почте требует SMTP. `GET /v1/auth/login-options?country_code=GE`
говорит странице входа, какие каналы страны работают прямо сейчас (пересечение списка
страны и настроенных провайдеров) и работает ли вход по почте: кабинет предлагает
только их и объясняет, когда входа нет.

| Канал | Провайдер | Переменные |
| --- | --- | --- |
| SMS | Twilio Programmable Messaging | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` или `TWILIO_MESSAGING_SERVICE_SID` |
| Telegram | Telegram Gateway API (`sendVerificationMessage`, платно за доставленный код) | `TELEGRAM_GATEWAY_API_TOKEN` |
| WhatsApp | шаблон категории «authentication» в WhatsApp Cloud API (код в тексте и кнопке «скопировать») | `WHATSAPP_OTP_PHONE_NUMBER_ID`, `WHATSAPP_OTP_TEMPLATE`, `WHATSAPP_OTP_TEMPLATE_LANGUAGES`, `WHATSAPP_OTP_ACCESS_TOKEN` (по умолчанию `WHATSAPP_SYSTEM_USER_TOKEN`) |
| Почта | любой SMTP (STARTTLS или TLS) | `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` |

Тексты SMS и писем — на языке пользователя (английский, русский, грузинский,
украинский, турецкий, иврит, арабский, немецкий, французский, испанский; иначе
английский) и всегда называют сервис (Assistant Workshop); SMS укладывается в одну
часть. Сообщения Telegram и WhatsApp пишут сами платформы. Провайдер
настраивается целиком или никак: неполные настройки останавливают запуск.

Каждый код — платное сообщение, поэтому отправки ограничены: повтор на тот же номер
и тем же каналом — не раньше чем через 30 секунд (переключиться на другой канал,
«код не пришёл — отправить по SMS», можно сразу), и не больше
`OTP_SENDS_PER_DESTINATION_PER_HOUR` (5) кодов на номер или почту,
`OTP_SENDS_PER_IP_PER_HOUR` (10) с одного адреса и `OTP_SENDS_PER_HOUR` (300) всего
за час; сверх лимита — 429. Проверка и резерв отправки идут под одной блокировкой до
обращения к провайдеру, так что параллельные запросы не проходят лимит вместе
(с базой — `pg_advisory_xact_lock` на всю платформу в одной транзакции с резервом,
общая для всех экземпляров API). Если все провайдеры отказали, подробности пишутся в лог, а пользователь
получает общий ответ без названий провайдеров и настроек.

### Защита входа

- **Перебор кода.** Каждая проверка сначала атомарно занимает одну из
  `OTP_MAX_FAILED_ATTEMPTS` попыток (блокировка строки в Postgres, блокировка
  коллекции в памяти) и только потом сравнивает код, поэтому даже 40 параллельных
  догадок сравниваются не больше пяти раз; верный код «гасит» вызов через
  compare-and-swap и открывает одну сессию. Проверки ограничены
  `OTP_VERIFIES_PER_IP_PER_10_MINUTES` (20) с одного адреса и 10 на один вызов за
  10 минут (429 с `Retry-After`; счётчики — в процессе API).
- **SMS pumping.** Номера premium-rate, shared-cost, персональные и универсальные
  (по разметке libphonenumber), спутниковые и международные сети, а также диапазоны
  `OTP_DENIED_PHONE_PREFIXES` кода не получают. На новые номера одной страны —
  не больше `OTP_SENDS_PER_COUNTRY_PER_HOUR` (100) кодов в час. Подтверждённые
  пользователи тратят отдельный бюджет `OTP_SENDS_TO_VERIFIED_USERS_PER_HOUR`
  (300): поток кодов на новые номера не закрывает вход вернувшимся владельцам.
  Когда срабатывает любой общий лимит, платформенные админы
  (`PLATFORM_ADMIN_EMAILS`, если настроен SMTP) получают письмо, а Sentry — событие,
  не чаще раза в час на лимит.
- **Проверка «не робот».** С `TURNSTILE_SITE_KEY` и `TURNSTILE_SECRET_KEY`
  (Cloudflare Turnstile) рискованный запрос кода — новый номер или почта, адрес,
  уже запросивший 3 кода за час, использована половина общего бюджета, страна из
  `OTP_HIGH_RISK_COUNTRIES` — получает 403 с причиной `challenge_required` и ключом
  виджета; страница входа показывает проверку и повторяет запрос с её токеном.
  Вернувшийся владелец в спокойный день проверку не видит. Если Cloudflare не
  отвечает, рискованный запрос отклоняется (fail closed). Без ключей проверка
  выключена (разработка, тесты).

В `development` и `test` каналы без провайдера пишут код в лог (`OTP_LOG_CODES`, по
умолчанию включено). В `production` коды никогда не пишутся в лог (`OTP_LOG_CODES=true`
— ошибка запуска), канал без провайдера не предлагается, а без единого провайдера
API при старте пишет ошибку, и вход отвечает 502 с объяснением.

## Виджет сайта

Кабинет выдаёт код для сайта (`GET …/channels/web/snippet`):

```html
<script src="<APP_BASE_URL>/widget.js" data-tenant="<id бизнеса>" async></script>
```

`/widget.js` — скрипт без зависимостей и без cookie: кнопка и окно чата в shadow
DOM (стили сайта и виджета не смешиваются), язык посетителя из браузера среди
языков бизнеса, письмо справа налево для иврита и арабского, индикатор набора,
ошибки с повтором, полноэкранное окно на телефоне, управление с клавиатуры.
Посетителя узнаёт случайный ключ в `localStorage`, там же — последние сообщения.
Фирменный цвет и угол кнопки владелец выбирает в кабинете (`PUT …/channels/web`
с `widget_color` и `widget_position`), приветствие на каждом языке живой версии
приходит в `GET /v1/widget/{id}/config`. Атрибуты кода важнее настроек кабинета:
`data-color="#0f766e"`, `data-position="left"`, а также `data-language="ka"`,
`data-open="true"` (окно открыто только на первой странице визита: если посетитель
закрыл или открыл чат, его выбор сохраняется на следующих страницах). Виджет
опрашивает `GET /v1/widget/{id}/messages?after=<id сообщения>` (ключ посетителя — в
заголовке `X-Widget-Session-Key`, не в адресе, чтобы не попадать в логи) и
показывает ответы ассистента и сотрудников: пока передача открыта, пока окно открыто
в течение суток после последнего обмена (сотрудник может написать в любой чат
сайта) и после ухода со страницы, пока ответ ещё писался. Сначала раз в 4 с, без
новостей реже (до 30 с, до 60 с с закрытым окном), на скрытой вкладке не опрашивает.
API ограничивает опрос (в минуту: 60 на посетителя, 300 на сеть, 6000 на бизнес,
60 000 на платформу) и сообщения (каждое — вызов модели; в минуту: 12 на
посетителя, 60 на сеть, 120 на бизнес, 1200 на платформу) и читает только
разговоры и сообщения этого посетителя. Сеть — адрес IPv4 или блок /64 адреса
IPv6; ключ посетителя выбирает сам вызывающий, поэтому расход модели держат
лимиты сети, бизнеса и платформы. Отказанный запрос не засчитывается ни в один
лимит. Счётчики общие для всех экземпляров API (таблица `rate_limit_buckets`,
миграция 1041): окно в минуту плюс предыдущее окно с весом той его части, что ещё
входит в скользящую минуту. Сверх лимита — 429 с `Retry-After`
(заголовок открыт сайтам через CORS): виджет пишет «слишком много сообщений» и
включает отправку и «Повторить» ровно через столько секунд, опрос тоже ждёт.
Приветствие API переведено на все языки интерфейса виджета (тест сверяет списки).
Вкладки одного сайта ведут одну историю: каждая перенимает то, что сохранили другие.
Сайту со строгой CSP нужно разрешить адрес API в
`script-src` и `connect-src`. Страница `GET /widget/demo?business_id=…` показывает
виджет как на сайте, даже пока чат выключен (предпросмотр для владельца и
UI-тестов); `color`, `position` и `language` в ней показывают ещё не сохранённый
выбор.
До первого сообщения виджет предлагает до трёх вопросов из частых вопросов
бизнеса на языке посетителя (`starter_questions` в конфигурации), кнопку
«Позвать человека» (`POST /v1/widget/{id}/handoff`: разговор передаётся
сотрудникам, посетитель видит, что ему ответят), «Новый разговор» в шапке (после
подтверждения — новый ключ посетителя; старый разговор остаётся у сотрудников) и
строку «AI-ассистент · может ошибаться · Конфиденциальность»: ссылка ведёт на
политику бизнеса (ссылка «Политика конфиденциальности» в анкете), иначе на
политику платформы по умолчанию `/c/{адрес}/privacy` (en, ru, ka). Все новые
тексты — на всех языках виджета.

**Страница чата** `<CABINET_BASE_URL>/c/{адрес}` — чат бизнеса на отдельной
странице для ссылок и QR-кодов (сайт не нужен): виджет в режиме страницы
(`data-mode="page"`, `data-container`), на весь экран телефона, в цветах бизнеса,
на языке посетителя (Accept-Language среди языков бизнеса), со ссылками на другие
каналы. Адрес — slug из названия (`cafe-batumi`), его можно сменить в кабинете;
старый адрес и id бизнеса ведут на текущий (308, метка `?src=` сохраняется).
Страница не индексируется (`X-Robots-Tag` и meta robots), её политика CSP
разрешает только сам кабинет и API (`connect-src`), без фреймов и форм; ключ
посетителя не попадает в адрес. Скрипт и API — по `APP_BASE_URL`, без него — по
`BACKEND_URL` кабинета (годится только когда браузер его видит: локально и в
e2e). В кабинете «Каналы → Поделиться»: ссылки с кнопкой «Копировать», метка
места (`?src=`), QR-код (делается в браузере), PNG и SVG, печать карточки A6 на
столик на языке клиентов.

Исходник скрипта — небольшие части в `app/gateways/http/static/widget/`
(тексты по группам языков, стили, окно чата, опрос, сеть, хранилище); API
склеивает их при старте в порядке из `app/gateways/http/widget_script_assembly.py`
и отдаёт одним файлом с ETag.

## Окружение

Пошаговый запуск с перечнем всех аккаунтов и ключей — в
[`docs/LAUNCH.md`](docs/LAUNCH.md). Все переменные с пояснениями — в
[`.env.example`](.env.example); переменные кабинета (`BACKEND_URL`,
`COOKIE_SECURE`, `TRUSTED_PROXY_HOPS`) — в [`web/README.md`](web/README.md).
Таблицу сверяет с кодом тест `tests/platform/test_environment_variables.py`: каждая
переменная, которую читают настройки или SDK, есть в `.env.example` и здесь.

| Переменная | Без неё (по умолчанию) |
| --- | --- |
| `APP_ENV` | `development` (образ Docker — `production`); в `production` обязателен `ENCRYPTION_KEY`, коды входа не пишутся в лог |
| `APP_BASE_URL` | публичный https-адрес API (вебхуки, виджет, оплата); без него нельзя опубликовать голосовую версию, подключить Telegram, принять оплату |
| `CABINET_BASE_URL` | вне `production` — `http://localhost:3000`; в `production` после согласия в Google владелец видит простую страницу вместо возврата в кабинет, а страница оплаты возвращает плательщика только на адреса из `CORS_ALLOWED_ORIGINS` |
| `CORS_ALLOWED_ORIGINS` | CORS выключен (виджет сайта разрешает любой источник сам); страница оплаты возвращает плательщика только на источник `CABINET_BASE_URL` и `APP_BASE_URL`. Укажите адрес кабинета (`http://localhost:3000` локально; в `docker-compose.yml` он задан) |
| `DATABASE_URL` | хранение в памяти |
| `LIVE_EVENTS_DATABASE_URL` | живые обновления кабинета слушают события (`LISTEN`) через `DATABASE_URL`; задайте прямое (сессионное) подключение к той же базе, только если `DATABASE_URL` идёт через пулер транзакций (PgBouncer, Supavisor на порту 6543): там `LISTEN` не работает. Без `DATABASE_URL` события передаются внутри процесса |
| `ENCRYPTION_KEY` | временный ключ: токены каналов не переживут перезапуск; в `production` — ошибка запуска (как и с общеизвестным значением по умолчанию из `docker-compose.yml`). Ключ Fernet или любая случайная строка от 32 символов; после первого запуска не меняется |
| `LLM_PROVIDER`, `LLM_MODEL_ID`, `LLM_JUDGE_MODEL_ID` | `openai` и `gpt-5-mini` (`anthropic` — `claude-opus-5-5`; `scripted` — без модели и ключей: каждый ответ — одна фиксированная фраза, для staging и проверок); `LLM_JUDGE_MODEL_ID` — модель клиента и судьи автотестов, по умолчанию та же модель провайдера |
| `LLM_CHAT_EFFORT`, `LLM_JUDGE_EFFORT` | усилие рассуждений: `low` в чате, `medium` у судьи автотестов (`minimal`, `low`, `medium`, `high`) |
| `LLM_MAX_OUTPUT_TOKENS`, `LLM_TOOL_ROUND_LIMIT` | 16000 токенов ответа, 8 кругов вызова инструментов на один ответ |
| `LLM_CALL_TIMEOUT_SECONDS` | 25: столько секунд ждём один вызов модели в чате с клиентом, затем одна повторная попытка; после второй неудачи разговор передаётся сотруднику |
| `LLM_MAX_CONCURRENCY` | 32 вызова модели одновременно в одном процессе (экземпляр API или воркер); следующий ждёт свободного места не дольше `LLM_CALL_TIMEOUT_SECONDS`, потом разговор передаётся сотруднику. Держите меньше `THREADPOOL_SIZE`, чтобы медленная модель не заняла все потоки запросов |
| `OPENAI_API_KEY`, `OPENAI_PROJECT_ID`, `OPENAI_BASE_URL` | ответы модели — ошибка 502 при первом вызове; ключ читает SDK OpenAI; адрес по умолчанию — `https://eu.api.openai.com/v1` (проект с хранением в ЕС) |
| `ANTHROPIC_API_KEY` | нужен только при `LLM_PROVIDER=anthropic` (ключ читает SDK Anthropic) |
| `AUTOTEST_TURN_LIMIT` | 4 сообщения клиента в одном сценарии автотеста |
| `SCRIPTED_LLM_LATENCY_MS` | 0: сколько миллисекунд модель `scripted` ждёт перед каждым ответом, как настоящий провайдер; задают нагрузочные тесты (`perf/k6`, `docs/operations/capacity.md`) |
| `OTP_LIFETIME_SECONDS`, `OTP_MAX_FAILED_ATTEMPTS` | код входа действует 600 секунд; после 5 неверных попыток нужен новый код |
| `OTP_SENDS_PER_DESTINATION_PER_HOUR`, `OTP_SENDS_PER_IP_PER_HOUR`, `OTP_SENDS_PER_HOUR` | 5 кодов на номер или почту, 10 с одного адреса и 300 на новые номера и почты всего за час (см. «Защита входа») |
| `OTP_SENDS_PER_COUNTRY_PER_HOUR`, `OTP_SENDS_TO_VERIFIED_USERS_PER_HOUR` | 100 кодов в час на новые номера одной страны; 300 в час подтверждённым пользователям — отдельный бюджет, который поток на новые номера не съедает |
| `OTP_VERIFIES_PER_IP_PER_10_MINUTES` | 20 проверок кода с одного адреса (IPv6 — сеть /64) за 10 минут |
| `OTP_HIGH_RISK_COUNTRIES` | список стран, номерам которых нужна проверка «не робот» (малые тихоокеанские территории и ряд африканских сетей); пустое значение — без такого признака |
| `OTP_DENIED_PHONE_PREFIXES` | только встроенный запрет: номера premium-rate, shared-cost, персональные и спутниковые коды не получают никогда |
| `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY` | проверка «не робот» (Cloudflare Turnstile) выключена; задаются оба или ни один |
| `OTP_LOG_CODES` | вне `production` включено: каналы без провайдера пишут код в лог; в `production` включить нельзя |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TWILIO_MESSAGING_SERVICE_SID` | нет кодов входа по SMS |
| `TELEGRAM_GATEWAY_API_TOKEN` | нет кодов входа в Telegram |
| `WHATSAPP_OTP_PHONE_NUMBER_ID`, `WHATSAPP_OTP_ACCESS_TOKEN`, `WHATSAPP_OTP_TEMPLATE`, `WHATSAPP_OTP_TEMPLATE_LANGUAGES` | нет кодов входа в WhatsApp; токен по умолчанию — `WHATSAPP_SYSTEM_USER_TOKEN`, язык шаблона — `en` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | нет входа по почте; порт по умолчанию — 587 (`starttls`), 465 (`ssl`), 25 (`none`). Без единого провайдера кодов вход работает только вне `production` (коды в логе) |
| `SESSION_LIFETIME_SECONDS` | сессия кабинета — 30 дней |
| `PLATFORM_ADMIN_EMAILS`, `PLATFORM_ADMIN_PHONE_NUMBERS` | нет админов платформы (права проверяются при каждом входе) |
| `RESTRICTED_COUNTRY_CODES` | `CU,IR,KP,SY`: из этих стран нельзя войти по номеру и создать бизнес; пустое значение снимает ограничение (список сверить с юристом) |
| `DEFAULT_DATA_REGION` | `eu` — регион обработки данных в профилях стран (`eu` или `us`) |
| `RECORDING_RETENTION_DAYS` | 90 дней хранения записей и расшифровок звонков (бизнес может поменять свой срок) |
| `RECORDINGS_DIRECTORY` | `var/recordings` (записи звонков на этом сервере при `RECORDINGS_STORAGE=local`) |
| `RECORDINGS_STORAGE` | `local`: записи, которые платформа хранит сама, — файлы этого сервера (разработка; ElevenLabs держит свои). `s3` — объектное хранилище в ЕС: каждая запись зашифрована ключом своего бизнеса (HKDF от `ENCRYPTION_KEY`, AES-256-GCM блоками по 64 КиБ), запись звонка после него переносится туда из ElevenLabs и удаляется там; без `RECORDINGS_S3_*` или `ENCRYPTION_KEY` — ошибка запуска |
| `RECORDINGS_S3_ENDPOINT_URL`, `RECORDINGS_S3_REGION`, `RECORDINGS_S3_BUCKET` | при `s3`: адрес S3-совместимого хранилища в ЕС (AWS `eu-central-1`, Cloudflare R2 с юрисдикцией ЕС, Hetzner, Scaleway), регион подписи (`auto` у R2) и закрытый бакет без версий |
| `RECORDINGS_S3_ACCESS_KEY_ID`, `RECORDINGS_S3_SECRET_ACCESS_KEY` | при `s3`: ключ, которому разрешены только чтение, запись и удаление в этом бакете; запросы подписываются (Signature V4, ссылки на одну минуту) |
| `CONTACT_MESSAGE_LIMIT_PER_HOUR` | 60 сообщений одного клиента за последний час во всех каналах: на 60-м помощник предупреждает о лимите, дальше молчит |
| `DPA_DOCUMENT_VERSION` | `2026-10-01` — действующая версия договора из `docs/legal/` |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_WEBHOOK_SECRET`, `ELEVENLABS_API_BASE_URL` | голосовой агент не создаётся: в `production` публикация версии с голосом отклоняется (409, причина `voice_configuration`), в `development`/`test` версия выходит без голосового агента (предупреждение в логе). Адрес по умолчанию — `https://api.eu.residency.elevenlabs.io` (хранение в ЕС) |
| `ELEVENLABS_ALLOW_NON_EU_REGION` | `false`: в `production` другой адрес ElevenLabs, кроме ЕС, — ошибка запуска |
| `ZADARMA_API_KEY`, `ZADARMA_API_SECRET` | пока не используются: номер помощника покупается в Zadarma вручную и вводится в кабинете (канал «Телефон») |
| `META_APP_SECRET`, `META_VERIFY_TOKEN`, `WHATSAPP_SYSTEM_USER_TOKEN` | WhatsApp, Instagram и Messenger не принимают вебхуки, WhatsApp не подключается и не отправляет сообщения |
| `META_APP_ID` | пока не используется |
| `TELEGRAM_PLATFORM_BOT_TOKEN`, `WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID`, `WHATSAPP_NOTIFICATION_TEMPLATE` | уведомления сотрудникам в Telegram и WhatsApp не уходят (контакт показывает причину). Почта и SMS сотрудникам идут через `SMTP_*` и `TWILIO_*` (как коды входа); без них вне `production` пишутся в лог |
| `WEB_PUSH_VAPID_PUBLIC_KEY`, `WEB_PUSH_VAPID_PRIVATE_KEY`, `WEB_PUSH_VAPID_SUBJECT` | уведомлений на устройства (Web Push) нет: кнопка «Включить на этом устройстве» скрыта; задаются все три или ни одной, пара ключей проверяется при запуске |
| `WHATSAPP_REMINDER_TEMPLATE` | напоминание о брони в WhatsApp уходит, только если клиент писал туда за последние 24 часа |
| `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` | нет синхронизации с Google Calendar |
| `FLITT_MERCHANT_ID`, `FLITT_SECRET_KEY` | оплата недоступна (502), вебхук оплаты отклоняется |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` | журнал вызовов модели не ведётся; адрес по умолчанию — `https://cloud.langfuse.com` (ЕС) |
| `LANGFUSE_CAPTURE_CONTENT` | `false`: тексты сообщений в журнал не пишутся |
| `SENTRY_DSN` | неожиданные ошибки только в логе |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.05`: доля запросов API, чья трассировка уходит в Sentry (от 0 до 1) |
| `APP_RELEASE`, `RENDER_GIT_COMMIT` | версия сборки в отчётах Sentry и в пульсе воркера; `RENDER_GIT_COMMIT` Render задаёт сам, `APP_RELEASE` — для других платформ |
| `LOG_FORMAT` | `json` в `production` (одна строка JSON с `request_id`, `business_id`, `conversation_id`, `channel`, `job_name`, `job_id`), `text` в остальных окружениях |
| `THREADPOOL_SIZE` | 64 обработчика запросов API одновременно (потоки AnyIO) |
| `DB_POOL_SIZE` | равен `THREADPOOL_SIZE`: столько соединений с Postgres держит один процесс (поток держит не больше одного соединения); сумма по всем экземплярам API и воркерам должна быть меньше лимита базы |
| `WORKER_POLL_SECONDS` | фоновый воркер проверяет задачи раз в 15 секунд |
| `WORKER_LANE_CONCURRENCY` | `inbound=8,outbound=4,default=2,autotests=2`: столько задач каждой полосы один процесс воркера выполняет одновременно (не указанные полосы — по умолчанию, от 1 до 64) |
| `EMBEDDED_WORKER` | `auto`: воркер работает потоком внутри API только при `APP_ENV=development` и пустом `DATABASE_URL`; `true` — всегда (в `production` — ошибка запуска), `false` — никогда (см. «Запуск») |
| `SEED_DEMO_DATA` | `false`: демо-данных нет. `true` (только разработка, в `production` — ошибка запуска): при старте API один раз создаёт демо-бизнесы — ресторан в Тбилиси и салон в Берлине с месяцем переписок, броней, заявок и передач; вход — `+995 555 00 00 01` или `demo@example.com`, код — в логе API (см. «Демо-данные») |
| `PORT`, `FORWARDED_ALLOW_IPS` | читает запуск образа, а не приложение: порт uvicorn (8000) и адреса доверенных прокси (`127.0.0.1`); их задают `Dockerfile`, `docker-compose.yml` и `render.yaml` |

Адреса для внешних кабинетов (`APP_BASE_URL` + путь):
вебхук Meta — `/v1/channels/meta/webhook`; post-call вебхук ElevenLabs —
`/v1/voice/webhooks/post-call`; redirect URI Google —
`/v1/integrations/google-calendar/callback` (подключение завершает кабинет, поэтому
без `CABINET_BASE_URL` Google Calendar выключен); колбэк Flitt — `/v1/payments/flitt/webhook`.

## HTTP API

Кабинет работает с `Authorization: Bearer <токен>` (выдаётся при входе по коду).
Чужой бизнес отвечает `404`, действия только для владельца — `403`, ошибки
проверки — `422` в формате `{"error": ..., "message": ...}`. Полное описание —
`/docs` и `/openapi.json`.

| Раздел | Маршруты |
| --- | --- |
| Здоровье | `GET /healthz` (жив ли процесс; не трогает базу и потоки запросов), `GET /readyz` (готов ли принимать трафик: база отвечает за 2 с, все миграции сборки применены, есть свободное соединение — иначе 503; в ответе каждая проверка и возраст пульса воркера) |
| Вход и профиль | `GET /v1/auth/login-options[?country_code=…]`, `POST /v1/auth/otp/start`, `POST /v1/auth/otp/verify`, `POST /v1/auth/logout`, `GET·PATCH /v1/me` |
| Каталог | `GET /v1/catalog/countries[/{code}]`, `GET /v1/catalog/languages`, `GET /v1/catalog/plans`, `GET /v1/catalog/niches[/{niche}]`, `POST /v1/phone-numbers/parse` |
| Бизнесы и команда | `POST·GET /v1/businesses`, `GET·PATCH /v1/businesses/{id}` (в ответе `revision`, растёт с каждым сохранением; PATCH с `expected_revision` от устаревшей версии — 409 `stale_revision`, ничего не меняется), `POST …/members` (роль `owner` или `staff`), `PATCH·DELETE …/members/{user_id}` (последнего владельца нельзя ни удалить, ни сделать сотрудником), `GET …/call-forwarding-instructions` |
| Данные и договор | `GET·POST …/dpa`, `GET /v1/legal/dpa/{version}?language=` (текст DPA, без токена), `GET …/audit-log` (страницы, фильтры `action`, `entity`, `actor_id`, `since`, `until`), `GET …/contacts` (страницы, `search`), `GET·DELETE …/contacts/{contact_id}`, `GET …/contacts/{contact_id}/export` |
| Анкета | `GET …/profile/wizard`, `GET·PUT·PATCH …/profile` (PATCH — автосохранение: меняются только присланные поля; с `expected_updated_at` от устаревшей анкеты — 409 `stale_revision`), `PUT …/profile/steps/{step}`, `GET …/profile/gaps` |
| Пошаговый запуск | `POST /v1/assistants` («Создать AI-помощника»: бизнес с умолчаниями страны, его шаги запуска и готовые ответы ниши; 201), `GET …/setup` (семь шагов по порядку — бизнес, предложение, часы и запись, кто получает заявки, каналы, проба, запуск — со статусами `done`, `skipped`, `next`, `todo`, процент, минуты до конца, следующее действие, ссылки «проверить с телефона», вехи и ход «Применить изменения»; `?language=`), `PUT·DELETE …/setup/skipped-steps/{setup_step}` (пропустить необязательный шаг `offer`, `channels`, `test` или вернуть его), `POST …/setup/milestones/{kind}/celebrate` (кабинет показал поздравление — один раз), `GET …/setup/starter-answers` (подсказки ниши для страны бизнеса: часы, правила брони, первый ресурс, передача человеку, запреты, тон, частые вопросы, примеры предложения без цен), `POST …/setup/starter-answers/apply` (принять одним вызовом: заполняются только пустые разделы, цены никогда не подставляются), `POST·GET …/assistant/apply` («Применить изменения»: версия из текущей анкеты, проверки в фоне и публикация, когда они прошли; 202; стадии `building`, `checking`, `publishing`, `live`, `needs_attention` с причинами простыми словами и местом, где их исправить) |
| Знания | `GET·POST …/knowledge`, `GET·PATCH·DELETE …/knowledge/{item_id}`, `POST …/knowledge/search`, `POST …/knowledge/import[/confirm]`, `DELETE …/knowledge/import/{batch_id}` |
| Ресурсы и расписание | `GET·POST …/resources`, `PATCH …/resources/{id}`, `GET·POST …/schedule-exceptions`, `DELETE …/schedule-exceptions/{id}` |
| Брони, заявки, передачи | `GET …/availability` (`full_day=true` — весь день для сотрудников), `GET·POST …/bookings`, `PATCH …/bookings/{id}` (статус, гости, место, примечание, имя), `POST …/bookings/{id}/cancel`, `POST …/bookings/{id}/reschedule`, `GET …/leads`, `PATCH …/leads/{id}`, `GET …/handoffs`, `POST …/handoffs/{id}/resolve`, `GET …/unanswered-questions`, `POST …/unanswered-questions/{id}/answer`, `GET …/dashboard`, `GET …/inbox-counts` (открытые передачи и новые заявки, без записи в журнал) |
| Живой кабинет | `GET …/events` (Server-Sent Events: что изменилось в бизнесе — передачи, сообщения, заявки, брони, каналы, автотесты — только виды и id, без текста клиентов; `Last-Event-ID` досылает пропущенное, не больше 5 потоков на человека в одном процессе), `GET …/attention-counts` (открытые передачи, новые заявки, неподтверждённые брони, каналы с ошибкой — индексные счётчики для значков меню, без записи в журнал) |
| Google Calendar | `GET·DELETE …/integrations/google-calendar`, `GET …/integrations/google-calendar/connect-url`, `GET /v1/integrations/google-calendar/callback` (ничего не обменивает, только передаёт `code`, `state`, `error` странице кабинета `CABINET_BASE_URL/integrations/google-calendar/callback`), `POST /v1/integrations/google-calendar/complete` (Bearer; завершает подключение только для того пользователя, который его начал; кабинет затем открывает `/b/{id}/channels?calendar=connected` или `?calendar=error&reason=…`) |
| Разговоры | `GET …/conversations` (страницы, фильтры `channel`, `status`, `from`/`to`, `search`), `GET …/conversations/{id}` (последние 100 сообщений расшифровки, расход модели, звонки, брони, заявки, передачи), `GET …/conversations/{id}/messages` (более ранние сообщения страницами, `limit`, `cursor`), `PUT …/conversations/{id}/rating`, `POST …/conversations/{id}/messages` (ответ сотрудника клиенту; шаблон WhatsApp, который Meta не принял, — 409 `template_rejected`), `GET …/calls/{call_id}/recording` (запись звонка; отдаёт части по `Range`, прослушивание пишется в журнал аудита), `POST …/test-chat` |
| Сборка помощника | `POST·GET …/assistant-versions`, `GET …/assistant-versions/{id}[/autotest-run]`, `GET …/assistant-versions/{id}/go-live-readiness`, `POST …/assistant-versions/{id}/autotests`, `POST …/assistant-versions/{id}/publish`, `POST …/assistant-versions/{id}/rollback` |
| Каналы (кабинет) | `GET …/channels`, `PUT·DELETE …/channels/{channel}`, `GET …/channels/web/snippet`, `PUT …/channels/whatsapp/staff-template` (шаблон WhatsApp для ответа сотрудника вне 24-часового окна), `POST …/manager-contacts/telegram-link` |
| Поделиться | `GET …/share-links?src=<метка>` (страница чата `/c/{адрес}` и ссылка каждого включённого канала — wa.me, t.me, m.me, ig.me, tel: — с меткой места: `?src=` у страницы чата, `?ref=` у m.me и ig.me; первый вызов даёт бизнесу адрес из названия), `PUT …/public-slug` (владелец: новый адрес страницы чата; занятый — 409 `slug_taken`, служебный — 422 `slug_reserved`; старые адреса продолжают вести к бизнесу) |
| Уведомления сотрудников | `GET …/notification-contacts` (контакты из настроек с ключом, готовностью канала и состоянием последней доставки; Telegram — с @username), `POST …/notification-contacts/{key}/test` (владелец: проверка контакта, не больше 5 в час), `GET·PUT …/notification-preferences` (мои события и тихие часы, ключ VAPID и мои устройства), `POST …/push-subscriptions` (включить уведомления на этом устройстве), `DELETE …/push-subscriptions/{id}`, `POST …/push-subscriptions/{id}/test`, `GET …/notification-links/{token}` (куда ведёт подписанная ссылка из уведомления; просроченная — `is_expired`) |
| Вебхуки и виджет | `POST /v1/channels/telegram/{channel_id}/webhook`, `GET·POST /v1/channels/meta/webhook`, `POST /v1/channels/telegram-platform/webhook`, `GET /v1/widget/{id}/config`, `GET·POST /v1/widget/{id}/messages`, `POST /v1/widget/{id}/handoff` («Позвать человека»: передача сотрудникам с причиной `customer_request`; свои лимиты на посетителя, сеть, бизнес и платформу), `GET /v1/public/chat/{адрес}` (что нужно странице чата до загрузки виджета: по адресу или id бизнеса, `noindex`), `POST /v1/widget/errors` (сигнал ошибки виджета: вид, этап, тип ошибки и место в widget.js, без текстов; лимиты на сеть, бизнес и платформу), `GET /widget.js`, `GET /widget/demo` |
| Голос | `POST /v1/voice/tools/{tool}`, `POST /v1/voice/webhooks/conversation-initiation`, `POST /v1/voice/webhooks/post-call` |
| Оплата | `GET …/billing`, `POST …/billing/trial`, `POST …/billing/plan`, `POST …/billing/cancel`, `POST …/billing/checkout`, `POST …/billing/subscribe` (тариф и период с оплатой сразу: после пробного периода, после отмены или без него), `POST /v1/payments/flitt/webhook` |
| Админка платформы | `GET /v1/admin/clients` (страницы, фильтры `status`, `health`, `country`, `niche`, `search`, сортировка `sort`), `GET /v1/admin/clients/{business_id}`, `POST /v1/admin/clients/{business_id}/open` |
| Очередь фоновых задач (платформенный админ) | `GET /v1/admin/jobs` (страницы, фильтры `status` — `pending`, `running`, `done`, `dead`, `discarded` — и `name`; без содержимого задач), `POST /v1/admin/jobs/{job_id}/retry` (снова в очередь «мёртвую» или отброшенную задачу), `POST /v1/admin/jobs/{job_id}/discard` (отбросить «мёртвую» или ожидающую); перезапуск и отказ пишутся в журнал аудита |

`…` — это `/v1/businesses/{business_id}`.

Автотесты не выполняются внутри запроса: `POST …/assistant-versions` и
`POST …/assistant-versions/{id}/autotests` запускают прогон (версия — `testing`,
прогон — `running`, ответ `202` для повторного прогона), а играет его фоновый воркер.
Ход прогона виден в `GET …/assistant-versions/{id}/autotest-run`: пока прогон
`running`, `scenario_count` — число запланированных сценариев, а `results` —
уже сыгранные (воркер сохраняет их после каждого сценария). Статус `ready`
даёт только прогон по всем языкам и сценариям версии. Выйти в эфир можно с
идущим пробным периодом или оплаченной подпиской, принятым DPA, контактом
менеджера и без блокирующих пробелов анкеты. Бесплатный пробный период
начинается при первом выходе в эфир, а не при создании бизнеса: если его ещё
не было, первая публикация открывает его на тарифе бизнеса (помесячно) и
пишет веху `went_live`; начатый раньше пробный период не перезапускается.

Чек-лист запуска — `GET …/assistant-versions/{id}/go-live-readiness`: пункты
`subscription_or_trial` (`trial_at_go_live` — пробный период начнётся при
запуске), `dpa`, `profile_gaps` (виды пробелов), `staff_contact`,
`autotests` (статус версии и прогона) и для версий с голосом
`voice_configuration`, у каждого `is_ok`, `is_blocking` и `details`. Те же коды
приходят в отказах публикации и отката: тело ошибки может содержать
`"reasons": [{"code", "message", "details"}]` (ещё `version_already_live`,
`version_archived`, `version_not_archived`, `force_publish_admin_only`).
Нечитаемая ссылка на меню — `422` с причиной `menu_link_invalid`,
`menu_link_unreachable` или `menu_link_unreadable`; недоступная модель — `502`.
Тело без причин остаётся прежним `{"error", "message"}`.

Ответ `POST …/test-chat` содержит версию, которая ответила
(`assistant_version_id`, `assistant_version_number`), и вызовы инструментов хода
(`tool_calls`); без `assistant_version_id` отвечает самая новая не архивная
версия. Если в ней ещё нет последних правок владельца (или версий ещё нет
вовсе), для владельца сначала собирается черновик из текущей анкеты — так
«Попробуйте помощника» работает до запуска и всегда с последними изменениями;
черновик ничего не публикует и не проверяется. Списки `GET …/knowledge` и `GET …/unanswered-questions` постраничные:
`?limit=&cursor=`, ответ `{"items", "next_cursor"}`, фильтры применяются до
разбиения на страницы. Импорт меню возвращает `batch_id`; `DELETE
…/knowledge/import/{batch_id}` удаляет неподтверждённые черновики этого импорта.

### Пошаговый запуск и «Применить изменения»

Кнопка «Создать AI-помощника» — это `POST /v1/assistants`: бизнес с
умолчаниями страны создателя (часовой пояс, языки, валюта), его шаги запуска
и готовые ответы ниши. Готовые ответы (`app/registries/niches/starters/`) есть
для всех 16 ниш на английском, русском и грузинском; часы раскладываются по
рабочей неделе страны (выходные из CLDR: в Израиле — пятница и суббота).
Это подсказки, а не факты бизнеса: в анкету они попадают только после
`POST …/setup/starter-answers/apply`, заполняют лишь пустые разделы, и цен в
них нет — пробел «нет цен» остаётся, пока их не впишет владелец.

`GET …/setup` вычисляет шаги из данных бизнеса (пробелы анкеты, контакт
сотрудника, подключённые каналы, проба помощника, опубликованная версия),
поэтому ничего не нужно «отмечать вручную»; хранятся только пропущенные
необязательные шаги и вехи (`went_live`, `test_chat_tried`,
`first_conversation`, `first_booking`, `first_handoff` — у каждой время, когда
она случилась, и `celebrated_at`). Первые настоящие разговор, бронь и передача
человеку находятся по самым ранним записям бизнеса (песочница тестового чата и
автотестов не считается). В ответе — ссылки «проверить с телефона»:
страница чата на сайте (`/widget/demo?business_id=…`, если API доступен по
HTTPS и чат на сайте включён) и бот Telegram бизнеса; `is_answering` — отвечают
ли они уже (после запуска).

`POST …/assistant/apply` собирает версию из текущей анкеты и знаний, сразу
проверяет условия запуска, кроме автотестов (контакт сотрудника, договор,
оплата, анкета), и отдаёт автотесты фоновому воркеру; когда они прошли, воркер
публикует версию. Повторное нажатие, пока идёт применение, или когда в эфире
уже всё актуально, ничего не запускает. Проверенная и не устаревшая версия
публикуется сразу, без новых автотестов. Стадии видны в
`GET …/assistant/apply` (`checks_done` из `checks_total`, пока идут проверки);
`needs_attention` перечисляет причины (`profile_incomplete`,
`staff_contact_missing`, `agreement_not_accepted`, `payment_needed`,
`build_failed`, `checks_failed` с видами сценариев, `checks_stopped`,
`voice_not_ready`, `publish_failed`) с текстом на языке владельца и местом,
где это исправить. Начало применения и публикация пишутся в журнал аудита.
Версии, автотесты и ручная публикация остаются в разделе «Дополнительно».

## Договор об обработке данных (DPA)

Текст DPA лежит в [`docs/legal/`](docs/legal/README.md): `dpa-<версия>.<язык>.md`
на английском, русском и грузинском. API отдаёт его по
`GET /v1/legal/dpa/{version}?language=` (язык, затем базовый язык, затем
английский), статус `GET …/dpa` ссылается на него в `document_url`, кабинет
показывает его перед кнопкой «Принять». Действующая версия — `DPA_DOCUMENT_VERSION`;
версию без текста принять нельзя.

> **Это шаблон.** До запуска в работу оператор должен показать его юристу своей
> юрисдикции и стран клиентов, заполнить поля в квадратных скобках (реквизиты,
> места обработки у субобработчиков, сроки, резервные копии, применимое право) и
> выпускать изменения новой версией (новые файлы и новое `DPA_DOCUMENT_VERSION`),
> чтобы владельцы приняли её заново.

## Проверки

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pyright
uv run pytest
```

Короче — через [`just`](https://just.systems) (`justfile`): `just setup`
(зависимости и git-хук `.pre-commit-config.yaml`), `just dev` (API с демо-данными
и кабинет), `just check` (всё, что CI проверяет в коде бэкенда и кабинета),
`just gen`, `just e2e`, `just security`, `just db-reset`.

Бюджеты задержек (p95 входа, ленты разговоров, карточки, свободного времени,
дашборда и опроса виджета) на большой базе проверяет отдельный набор
`uv run pytest -m perf tests/perf` (`PERF_SCALE=small|medium|full`; по
умолчанию он исключён из `pytest`); раз в неделю его и сценарии k6 запускает
`.github/workflows/perf.yml` — подробности в
[docs/operations/capacity.md](docs/operations/capacity.md).

Ворота качества в CI: покрытие строк и ветвей `app/` не ниже 95 %
(`pytest -n auto --cov=app --cov-branch`), пороги покрытия `src/lib` и `_lib`
кабинета (`npm run test:coverage`), слои ролей (`.importlinter`, решение
[ADR 0002](docs/adr/0002-role-chain-and-layers.md)), мёртвый код (`vulture`),
актуальность `openapi.json` и `schema.d.ts`, совместимость API внутри `/v1`
(`oasdiff`, [docs/api-versioning.md](docs/api-versioning.md),
[docs/API_CHANGELOG.md](docs/API_CHANGELOG.md)) и проверки безопасности
(pip-audit, npm audit, gitleaks, bandit, CodeQL, Trivy, SBOM; Dependabot раз в
неделю) — см. [SECURITY.md](SECURITY.md). Решения архитектуры —
[docs/adr/](docs/adr/README.md).

CI (`.github/workflows/ci.yml`) прогоняет те же проверки бэкенда (с Postgres 16 из
пакетов Ubuntu), линтер, проверку типов, тесты и сборку кабинета (`web/`), проверки
безопасности, собирает оба Docker-образа, сканирует их Trivy и проверяет
`docker-compose.yml`. Задача `e2e` после проверки
кабинета запускает браузерные тесты Playwright (`web/e2e/`): API в режиме
разработки и собранный кабинет, вход по телефону и e-mail, создание бизнеса,
анкета, все разделы, смена языка и демо виджета (`cd web && npm run e2e`, см.
`web/README.md`).

Сквозные тесты (`tests/e2e/`) собирают настоящий `AppContainer` и подменяют только
края: настройки, часы, модель (`ScriptedLlmAdapter`), доставку кодов и внешние
HTTP-сервисы (`httpx.MockTransport`). Тесты хранилища поднимают локальный
Postgres 16, если он установлен, и пропускаются без него.
