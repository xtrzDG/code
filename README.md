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

## Запуск

```bash
uv sync
cp .env.example .env            # заполнить нужные ключи
uv run uvicorn app.main:create_application --factory --reload
```

Без `DATABASE_URL` данные хранятся в памяти процесса (удобно для демо и тестов).

## Проверки

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pyright
uv run pytest
```
