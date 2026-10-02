# Архитектура бэкенда

Бэкенд сгенерирован из шаблона
[`copier-template-python-backend`](https://github.com/eldenizfamilyanskicode/copier-template-python-backend)
и следует его ролям и правилам (`AGENTS.md`, `docs/conventions.md`). Здесь — как
техническое задание из [концепции v2](concept.md) переложено на Python.

## Отличия от стека в ТЗ

| В ТЗ | Здесь | Почему |
| --- | --- | --- |
| Next.js API-роуты (вебхуки, инструменты) | FastAPI в этом репозитории | требование владельца: бэкенд на Python по шаблону copier |
| Сайт, анкета, кабинет на Next.js | кабинет на Next.js в `web/` | ходит в HTTP API бэкенда через свои серверные маршруты; токен только в httpOnly cookie |
| Supabase Postgres (ЕС) + RLS | контракт документного хранилища; in-memory для тестов и Postgres (ЕС) с изоляцией по `business_id` | use case не зависят от базы |
| Node-воркер + pg-boss | Python-воркер с очередью в Postgres | один язык и одни use case для API и фоновых задач |
| packages/core, brain, channels, niches, evals | роли шаблона: use_cases, orchestrators, registries, adapters… | `services` запрещён шаблоном |
| `tenants`, `users` | `BusinessDocument`, `UserDocument` | те же поля; «бизнес» понятнее в коде |

Всё остальное — как в ТЗ: OpenAI gpt-5-mini в проекте с хранением в ЕС как «мозг»,
ElevenLabs Agents для голоса, номера Zadarma, WhatsApp Cloud API, Instagram и
Messenger через Graph API, Telegram Bot API, свой виджет, Flitt, Langfuse, Sentry.

## Роли и направление зависимостей

```text
HTTP (FastAPI)              app/gateways/http/      маршруты, коды ошибок, ответы
  └─ operators              app/operators/          одна точка входа на эндпоинт
      └─ pipelines          app/pipelines/          порядок оркестраторов в фазе
          └─ orchestrators  app/orchestrators/      координация нескольких use case
              └─ use_cases  app/use_cases/          одно бизнес-действие
                  ├─ repositories  app/repositories/  документы с изоляцией по бизнесу
                  ├─ registries    app/registries/    страны, языки, ниши, тарифы
                  ├─ facilitators  app/facilitators/  узкие побочные эффекты (SMS, уведомления)
                  ├─ utilities     app/utilities/     детерминированные операции
                  └─ transformers  app/transformers/  преобразование форм
repositories ─ adapters (app/adapters/) ─ clients (app/clients/)  внешние системы
```

## Данные (ТЗ §2)

Каждая таблица ТЗ — документ в `app/schemas/domain/`. Документы бизнеса несут
`business_id`; репозитории читают их только вместе с `business_id`
(`BusinessScopedRepository`), поэтому чужие данные недоступны ни по какому id —
это аналог RLS из ТЗ. `tenant_id` в инструментах берётся из сессии или из
канала на сервере, никогда из слов модели.

Вторая линия защиты — RLS в Postgres. Операторы (`BusinessScopedPipelineOperator`)
выполняют запрос бизнеса внутри `StorageScopeContract.scoped_to_business(...)`,
так же работают ход разговора (с вызовами инструментов модели), вызовы
инструментов голосового агента и задачи очереди с `business_id`. Тогда даже
репозиторий, забывший фильтр по бизнесу, не прочитает и не запишет чужие строки.
Вход, вебхуки до определения бизнеса, админка и периодические задачи по всем
бизнесам работают на уровне платформы; код, которому нужно посмотреть сквозь
бизнесы (уникальность аккаунта канала), явно поднимается через `platform_wide()`.

| Таблица ТЗ | Документ |
| --- | --- |
| tenants | `BusinessDocument` (участники, контакты менеджеров, режим обслуживания) |
| users | `UserDocument`, `OtpChallengeDocument`, `UserSessionDocument` |
| assistants, assistant_versions | `AssistantVersionDocument` |
| knowledge_items | `KnowledgeItemDocument` |
| resources, schedules, schedule_exceptions | `ResourceDocument`, `ScheduleExceptionDocument` |
| channels | `ChannelDocument` (токены только в зашифрованном виде) |
| contacts | `ContactDocument` |
| conversations, messages, calls | `ConversationDocument`, `MessageDocument`, `CallDocument`, `LlmTurnDocument` |
| bookings, leads, handoffs, unanswered_questions | `BookingDocument`, `LeadDocument`, `HandoffDocument`, `UnansweredQuestionDocument` |
| test_runs | `AutotestRunDocument` |
| subscriptions, invoices, usage_events | `SubscriptionDocument`, `InvoiceDocument`, `UsageEventDocument` |
| audit_logs, dpa_acceptances | `AuditLogEntryDocument`, `DpaAcceptanceDocument` |
| профиль анкеты (§3) | `BusinessProfileDocument` |

## Адаптивность под любую страну

Требование владельца проекта и раздел «Масштаб» ТЗ («новая страна — это язык,
номера, платежи и партнёр на месте, а не новый продукт»):

1. **Номера телефонов** любой страны разбираются библиотекой `phonenumbers`
   (245 регионов) и хранятся только в E.164. Из номера выводятся страна, тип
   линии и часовые пояса. Телефон в инструментах модели разбирается с подсказкой
   страны бизнеса, а не «+995» по умолчанию.
2. **Профиль страны** собирается для каждой страны мира из `phonenumbers` и
   Babel/CLDR (языки, валюта, часовые пояса), сверху — кураторские данные:
   экстренный номер, стартовые языки (для Грузии ka, ru, en; по запросу tr, he,
   ar, hy), канал кода входа, правило записи звонков (уведомление или согласие
   всех сторон), местные номера, статус онбординга, регион данных (ЕС).
3. **Языки** — любые теги BCP 47; направление письма (иврит и арабский — справа
   налево); честная пометка голоса: `verified`, `beta`, `needs_pilot_check`
   (грузинский — до замера на пилоте, как требует ТЗ).
4. **Деньги** — целые минимальные единицы валюты бизнеса (в Грузии — лари).
   Тарифы — в евро с прайсом в лари; фильтр выдуманных цифр понимает символы и
   коды любой валюты.
5. **Время** — часы, исключения и брони в часовом поясе бизнеса (IANA),
   хранение в UTC.
6. **Тексты** для владельца и клиента — словари `язык → текст` с откатом:
   запрошенный язык → базовый язык → английский.

## Путь сообщения (ТЗ §1)

Вебхук канала → адаптер канала (`parse_webhook`, `verify_signature`) →
`InboundMessage` → бизнес по id канала → контакт → разговор, закреплённый за
опубликованной версией → язык по первой фразе → модель с инструкцией (шаблон
ниши + факты) и инструментами → сервер выполняет инструменты → фильтр выдуманных
цифр (переписать один раз, потом передать человеку) → отправка в канал → запись
в `messages` и `usage_events`. Пока передача человеку открыта, в чате бот молчит.

## Путь звонка (ТЗ §1, §7)

Переадресация «нет ответа / занято» → номер Zadarma → SIP → агент ElevenLabs
этого бизнеса. Агент собран из той же версии: та же инструкция и те же
инструменты, вызываемые через наши вебхуки с подписью HMAC. После звонка вебхук
приносит расшифровку, запись и стоимость → `calls`, итог (бронь, заявка,
передача, вопрос без ответа), подтверждение клиенту сообщением.

## LLM

- Провайдер-нейтральный контракт `LlmAdapterContract`. По умолчанию — OpenAI
  `gpt-5-mini` через `https://eu.api.openai.com/v1` (проект с хранением в ЕС,
  как в ТЗ); запасной — Anthropic; для тестов — `ScriptedLlmAdapter`.
- Транскрипт хранится «как есть» и только дописывается: пользовательские ходы —
  в каноническом формате, ходы модели — в формате провайдера. Изменчивое
  (текущее местное время) — в пользовательском ходе, не в инструкции.
- Инструкция собирается кодом из шаблона ниши без модели и не меняется внутри
  версии, поэтому кэш промпта работает.

## HTTP-слой

- Роутер каждого раздела — функция `build_<раздел>_router(...)`, операторы
  приходят аргументами.
- Ошибки приложения переводятся в HTTP-коды в одном месте
  (`app/gateways/http/error_responses.py`).
- Авторизация: `Authorization: Bearer`, зависимость
  `build_current_user_dependency`; доступ к бизнесу — `AuthorizeBusinessAccessUseCase`
  (owner, staff; вход платформенного админа пишется в журнал аудита).

## Сборка и точки входа

- Корень композиции — `app/containers/app.py::AppContainer`. Контейнеры по ролям
  зависят только «вниз»: операторы → пайплайны → оркестраторы → use case →
  репозитории, реестры, фасилитаторы, трансформеры, утилиты → адаптеры → клиенты.
  Use case типизированы своим контрактом (`UseCaseContract[вход, выход]`), а
  цепочки `PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(...)))`
  строятся типизированными помощниками `app/containers/provider_chains.py`, поэтому
  вызов каждого `build_<раздел>_router` проверяется mypy и pyright.
- Большие контейнеры ролей собраны из дочерних контейнеров по ограниченным
  контекстам: `app/containers/<роль>/<роль>_container.py` компонует
  `<контекст>_<роль>.py` (use case — по пакетам `app/use_cases/`, оркестраторы,
  пайплайны и операторы — по разделам API: accounts, compliance, knowledge,
  operations, conversations, assistants, channels, billing, platform). Провайдер
  читается по пути контекста: `use_cases.bookings.create_booking_use_case`,
  `operators.billing.end_trials_operator`. Дочерний контейнер получает рёбрами
  только нужные ему контексты; контейнер уровнем выше видит вложенные контексты
  через `composed_container_edge` (`app/containers/container_edges.py`).
- Где модуль нарушает направление ролей, провайдер стоит в контейнере уровнем выше:
  прогон сценария автотеста (use case, которому нужен оркестратор разговора) — в
  `AssistantOrchestratorsContainer`, оркестраторы вебхуков каналов и виджета (им
  нужен пайплайн сообщения клиента) — в `ChannelPipelinesContainer`.
- Синглтоны: клиенты, адаптеры (в том числе все коллекции документов на одном пуле
  Postgres и одном `StorageScopeContext`, дочерний `DocumentCollectionsContainer`
  контейнера адаптеров), репозитории, реестры (общий
  `BusinessLockRegistry`), фасилитаторы, пайплайн сообщения клиента (замки по
  клиенту общие для всех каналов). Use case, оркестраторы и операторы — фабрики.
- Журнал вызовов модели (`llm_trace_facilitator`) живёт в `AdaptersContainer`:
  `TracingLlmAdapter` оборачивает им маршрутизирующий адаптер модели, а
  фасилитаторы сами зависят от адаптеров.
- HTTP: `app/main.py` (фабрика uvicorn) и `app/gateways/http/router_assembly.py`.
  Фоновый воркер: `app/worker_main.py`, задачи перечислены в
  `app/containers/gateways.py`. В разработке без Postgres тот же воркер идёт
  потоком внутри API (`EMBEDDED_WORKER`, жизненный цикл в `app/main.py`): данные в
  памяти видны только своему процессу.
