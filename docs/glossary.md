# Glossary of the owner cabinet

The words owners and staff read in the cabinet, the staff notifications and
the texts the platform writes for them, in English, Russian and Georgian. A
new text uses these words; a text that needs a word missing here adds it
first. Staff are small-business people, not engineers: no developer jargon,
no calques, nothing they would have to look up.

The Georgian and Russian wording still needs a review by native speakers
(see "Review" below); until then this file is the reference the agents and
the reviewers work from.

## Terms

| Concept (code name) | English | Russian | Georgian | Never write |
|---|---|---|---|---|
| The section with conversations the assistant passed to a person (`handoffs`) | Needs a person | Нужен человек | ადამიანის დახმარება | Handoffs (as a section), Передачи, გადაცემები |
| One such conversation (`handoff`) | handoff; "needs a person" in lists and counters | разговор, где нужен человек; «Нужен человек» в счётчиках | საუბარი, სადაც ადამიანია საჭირო; „ადამიანის დახმარება“ მთვლელებში | передача, перевод (alone), გადაცემა |
| Passing a conversation to staff | pass to a person | передать человеку / позвать человека | თანამშრომელთან გადამისამართება | передача (noun) |
| Waiting / resolved | Waiting / Resolved | Ждут / Решённые, «Решено» | ელოდება / მოგვარებული, „მოგვარდა“ | Открытые / Закрытые передачи |
| A built assistant (`assistant version`) | update | обновление | განახლება | version, версия, ვერსია (except agreement versions) |
| Building a version | prepare an update | подготовить обновление | განახლების მომზადება | build, собрать, сборка, აწყობა |
| Rolling back | bring back an update | вернуть обновление | განახლების დაბრუნება | roll back, откат, откатить |
| Automatic test conversations (`autotests`) | checks | проверки | შემოწმებები | autotests, автотесты, ავტოტესტები, judge, судья, მსაჯი |
| Lead | request | заявка | მოთხოვნა | lead, лид |
| Business profile | profile | анкета | ანკეტა | профиль, პროფილი |
| Knowledge base | knowledge (base) | знания, база знаний | ცოდნა, ცოდნის ბაზა | — |
| Test chat, test data (`sandbox`) | test chat, test | тестовый чат, тест | სატესტო ჩატი, ტესტი | sandbox, песочница |
| Platform pages for the platform team (`/admin`) | Platform | Платформа | პლატფორმა | Admin, Админка |
| The model's system prompt (`instruction`) | shown only to platform admins | только для администраторов платформы | მხოლოდ პლატფორმის ადმინისტრატორებისთვის | — |
| Model, tokens, AI cost per message | shown only to platform admins | только для администраторов платформы | მხოლოდ პლატფორმის ადმინისტრატორებისთვის | tokens, токены in owner pages |
| A staff Telegram chat | `@username`, or the contact's name and "Telegram chat" | `@username` или имя и «Чат в Telegram» | `@username` ან სახელი და „Telegram-ის ჩატი“ | the numeric chat id |

## Texts the platform writes for staff

Staff never read a system text in another language than their own:

- A handoff the platform creates (the model declined or was unavailable, an
  answer held back for figures missing from the business data, a call that
  named such figures, a reply that never arrived, data erased at the
  customer's request) is stored as a `HandoffSummaryCode` with the quoted
  words and the flagged values. Notifications render it in each contact's
  language (`app/transformers/notifications/handoff_summary_texts.py`), the
  cabinet in the reader's (`handoffs.summaryCodes` in the dictionaries); a
  test keeps the two word for word the same.
- The model writes its own handoff summaries, and the checks' judge its
  notes, in the business's staff language (`owner_language`).
- Quotes keep the customer's own words and language: “…” in English, «…» in
  Russian, „…“ in Georgian.

## Dates in sentences

A formatted date never ends a sentence: the Russian format ends with
"г." ("16 окт. 2026 г."), and a full stop after it reads "г..". Put the date
before the verb ("Оплатите до {date}, чтобы…"), after a colon as a label
("Последний запуск: {date}"), or in parentheses. `src/i18n/i18n.test.ts`
fails on a `{date}.`, `{when}.` or `{until}.` in any dictionary.

## Length

Russian and Georgian texts run 20–40 % longer than English. Every layout is
checked with the pseudo-locale (`NEXT_PUBLIC_PSEUDO_LOCALE=true`, English
padded by 40 % with accented letters; `web/e2e/pseudo-locale.spec.ts`) at
1440 and 390 px: no horizontal overflow, no clipped button or tab.

## Review

Before launch in a market, a native speaker reads the cabinet in its
language against this glossary (owner pages, notifications, the texts
above) and marks every unnatural or ambiguous phrase. Changes go to the
section dictionaries in `web/src/i18n/messages/` and, for staff
notifications, to `app/transformers/notifications/`.
