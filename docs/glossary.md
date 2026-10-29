# Glossary of the owner cabinet

The words owners and staff read in the cabinet, the staff notifications and
the texts the platform writes for them, in English and Italian (the two
interface languages, `CABINET_LANGUAGES`), with the Russian and Georgian
wording the staff notifications and the customer-facing texts still carry. A
new text uses these words; a text that needs a word missing here adds it
first. Staff are small-business people, not engineers: no developer jargon,
no calques, nothing they would have to look up.

The Italian wording is a team draft that still needs a review by a native
speaker (see "Review" below), as do the Russian and Georgian notification
texts; until then this file is the reference the agents and the reviewers
work from.

## Terms

| Concept (code name) | English | Italian (draft) | Russian | Georgian | Never write |
|---|---|---|---|---|---|
| The AI front-line assistant | assistant | assistente | помощник | ასისტენტი | a "helper" or "bot" in the Italian cabinet; ассистент in Russian staff texts (the product's own name „Мастерская ассистентов“ keeps it; customers read „AI-ассистент“, see "Words customers read") |
| The team's one list of conversations (`inbox`) | Inbox | Conversazioni (the phone's tab bar: Chat) | Входящие | შემოსული (everywhere: the navigation, the page and sentences, „შემოსულში“) | Messages, Posta, Сообщения, Мессенджер, შემოსულები |
| The inbox views (`needs_person`, `requests`, `mine`, `unassigned`, `all`) | Needs a person, Requests, Mine, Unassigned, All | Serve una persona, Richieste, Mie, Non assegnate, Tutte | Нужен человек, Заявки, Мои, Без ответственного, Все | ადამიანის დახმარება, მოთხოვნები, ჩემი, დაუნიშნავი, ყველა | Queue, Coda, Очередь, Тикеты |
| Who handles a conversation (`assignee`, `assign`) | Handled by {name}; Assign; Take it; Unassign | Gestita da {name}; Assegna; Prendila in carico; Rimuovi assegnazione | Отвечает: {name}; Назначить; Взять себе; Снять назначение | პასუხისმგებელი: {name}; დანიშვნა; ჩემზე აღება; დანიშვნის მოხსნა | assignee, исполнитель, тикет, ticket |
| An internal note on a conversation (`conversation note`) | note; "Only your team sees this" | nota; "Le vede solo il tuo team" | заметка; «Это видит только ваша команда» | შენიშვნა; „ამას მხოლოდ თქვენი გუნდი ხედავს“ | comment (it is not sent), commento, комментарий |
| A saved reply staff insert with "/" (`quick reply`) | quick reply | risposta rapida | быстрый ответ | სწრაფი პასუხი | template (that is WhatsApp's), modello, canned response, шаблон |
| The section with conversations the assistant passed to a person (`handoffs`) | Needs a person | Serve una persona | Нужен человек | ადამიანის დახმარება | Handoffs (as a section), Передачи, გადაცემები |
| One such conversation (`handoff`) | handoff; "needs a person" in lists and counters | conversazione che aspetta una persona; "Serve una persona" in lists and counters | разговор, где нужен человек; «Нужен человек» в счётчиках | საუბარი, სადაც ადამიანია საჭირო; „ადამიანის დახმარება“ მთვლელებში | передача, перевод (alone), გადაცემა |
| Passing a conversation to staff | pass to a person | passare a una persona | передать человеку / позвать человека | თანამშრომელთან გადამისამართება | передача (noun), escalation |
| Waiting / resolved | Waiting / Resolved | In attesa / Risolto | Ждут / Решённые, «Решено» | ელოდება / მოგვარებული, „მოგვარდა“ | Открытые / Закрытые передачи |
| A built assistant (`assistant version`) | update | aggiornamento | обновление | განახლება | version, versione, версия, ვერსია (except agreement versions) |
| Building a version | prepare an update | prepara un aggiornamento | подготовить обновление | განახლების მომზადება | build, compilare, собрать, сборка, აწყობა |
| Rolling back | bring back an update | ripristina un aggiornamento | вернуть обновление | განახლების დაბრუნება | roll back, rollback, откат, откатить |
| Automatic test conversations (`autotests`) | checks | verifiche | проверки | შემოწმებები | autotests, autotest, автотесты, ავტოტესტები, judge, giudice, судья, მსაჯი |
| Lead | request | richiesta | заявка | მოთხოვნა | lead, лид |
| Business profile | profile | profilo dell'attività | анкета | ანკეტა | профиль, პროფილი |
| Knowledge base | knowledge (base) | conoscenze | знания, база знаний | ცოდნა, ცოდნის ბაზა | — |
| Test chat, test data (`sandbox`) | test chat, test | chat di prova, prova | тестовый чат, тест | სატესტო ჩატი, ტესტი | sandbox, песочница |
| Platform pages for the platform team (`/admin`) | Platform | Piattaforma | Платформа | პლატფორმა | Admin, Админка |
| The model's system prompt (`instruction`) | shown only to platform admins | solo per gli amministratori della piattaforma | только для администраторов платформы | მხოლოდ პლატფორმის ადმინისტრატორებისთვის | — |
| Model, tokens, AI cost per message | shown only to platform admins | solo per gli amministratori della piattaforma | только для администраторов платформы | მხოლოდ პლატფორმის ადმინისტრატორებისთვის | tokens, token, токены in owner pages |
| A staff Telegram chat | `@username`, or the contact's name and "Telegram chat" | `@username`, or the contact's name and "Chat Telegram" | `@username` или имя и «Чат в Telegram» | `@username` ან სახელი და „Telegram-ის ჩატი“ | the numeric chat id |

The Italian column follows the dictionaries in `web/src/i18n/messages/`
(`it.ts`, `sections/*/*.it.ts`); the Russian and Georgian columns are the
wording of the staff notifications (`app/transformers/notifications/`) and of
the customer-facing texts, which the cabinet no longer shows but staff still
read in their messages.

## Words customers read

The website chat (`widget.js`, the hosted chat page `/c/{slug}`, the
`/widget/demo` page), the assistant's first message and the platform's
notices to customers are read by the business's customers, not by staff.
They come in the customers' languages (the widget speaks 30), whatever the
owner's interface language. There the assistant is an **"AI-ассистент"**,
not a "помощник":

| Where | English | Russian | Georgian | Never write |
|---|---|---|---|---|
| The header, the greeting, the footer, the AI disclosure | AI assistant | AI-ассистент | AI-ასისტენტი | помощник, бот, чат-бот, ИИ-ассистент |
| Short form inside the chat ("…is typing") | the assistant | ассистент | ასისტენტი | помощник, бот |
| A late answer ("We'll answer as soon as we can") | our team answers | «Мы ответим, как только сможем.» | „გიპასუხებთ, როგორც კი შევძლებთ.“ | "error", «ошибка» |

Why two words: the customer must learn at once that a machine answers
(the AI disclosure), and "помощник" alone reads as a person's assistant;
"AI" is written in Latin letters in every language, as the disclosure says
it (`app/utilities/conversations/assistant_texts/ai_disclosure_texts.py`).
The owner, on the other hand, sets up and teaches *their* assistant; the
Italian cabinet says "assistente" (and "assistente AI" where the AI must be
named, as in "Crea un assistente AI"), never a helper or a bot
(`web/src/i18n/glossary.test.ts`). The privacy notice of the chat describes
the assistant to customers in the cabinet's words and stays as it is until
the legal review.

`web/src/i18n/widgetGlossary.test.ts` reads the widget's text bundles
(`app/gateways/http/static/widget/texts_*.js`): every language in its own
script, the Russian, English and Georgian header, greeting and footer
naming the AI assistant, no "помощник", "бот" or "ИИ" in the Russian chat.

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
  Italian and Russian, „…“ in Georgian.

## Dates in sentences

A formatted date never ends a sentence: the Russian format ends with
"г." ("16 окт. 2026 г."), and a full stop after it reads "г.."; an Italian
date with its month abbreviated ("16 ott 2026") reads better before the verb
too. Put the date before the verb ("Paga entro {date} per…"), after a colon
as a label ("Ultimo avvio: {date}"), or in parentheses.
`src/i18n/i18n.test.ts` fails on a `{date}.`, `{when}.`, `{until}.` (or
another date placeholder) before a full stop in any dictionary.

## Length

Italian texts run up to 30 % longer than English (Russian and Georgian
notification texts 20–40 %). Every layout is checked with the pseudo-locale
(the cabinet started with `PSEUDO_LOCALE=true` and the `aw_locale=en-XA`
cookie: English padded by 40 % with accented letters;
`web/e2e/pseudo-locale-*.spec.ts`) at 1440 and 390 px: no horizontal
overflow, no clipped button or tab.

## Dates and numbers in Georgian on customer pages

Chrome has no Georgian Intl and would write "8 hours ago" and "Oct 16, 2026"
on a Georgian page. The cabinet's languages read from the browser's Intl
(Italian and English are everywhere), but the customers' pages (the guest
booking page `/r/{token}`, the hosted chat) write Georgian dates, numbers,
lists and relative times from CLDR tables of their own (`web/src/lib/intl/`),
the same on the server and in every browser: "16 ოქტ. 2026, 12:00", "8 საათის
წინ", "18,50 ₾", "ა, ბ და გ".

## Review

Before launch in a market, a native speaker reads the cabinet in its
language against this glossary (owner pages, notifications, the texts
above) and marks every unnatural or ambiguous phrase. For Italy this is the
review of the Italian drafts: the cabinet dictionaries, the owner texts
(`app/registries/localization/texts/it.json`), the help articles
(`docs/help/it/`) and the DPA draft (`docs/legal/drafts/`). Changes go to the
section dictionaries in `web/src/i18n/messages/` and, for staff
notifications, to `app/transformers/notifications/`.
