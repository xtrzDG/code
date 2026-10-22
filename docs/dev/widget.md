# The website widget and the hosted chat page

The website chat is one dependency-free script the API serves; the hosted
chat page `/c/{address}` of the cabinet runs the same script in page mode.

## The snippet

The cabinet hands out the code for a website (`GET …/channels/web/snippet`):

```html
<script src="<APP_BASE_URL>/widget.js" data-tenant="<business id>" async></script>
```

`/widget.js` is a script without dependencies or cookies: a button and a
chat window in a shadow DOM (the site's and the widget's styles never mix),
the visitor's browser language among the business's languages,
right-to-left writing for Hebrew and Arabic, a typing indicator, errors with
a retry, a full-screen window on phones, keyboard control. A random key in
`localStorage` recognises the visitor; the last messages are kept there
too. The owner picks the brand colour and the button's corner in the cabinet
(`PUT …/channels/web` with `widget_color` and `widget_position`); the
greeting in every language of the live version comes from
`GET /v1/widget/{id}/config`. Attributes of the snippet win over the
cabinet's settings: `data-color="#ad5732"`, `data-position="left"`,
`data-language="ka"`, and `data-open="true"` (the window opens only on the
visit's first page: once the visitor closed or opened the chat, that choice
holds on the next pages).

## Polling and limits

The widget polls `GET /v1/widget/{id}/messages?after=<message id>` (the
visitor key travels in the `X-Widget-Session-Key` header, never in the URL,
so it stays out of logs) and shows the answers of the assistant and of
staff: while a handoff is open, while the window is open within a day of the
last exchange (staff may write to any website chat), and after the visitor
left the page while an answer was still being written. First every 4 s, then
less often without news (up to 30 s, up to 60 s with the window closed),
never on a hidden tab.

The API limits polling (per minute: 60 per visitor, 300 per network, 6,000
per business, 60,000 for the platform) and messages (each one is a model
call; per minute: 12 per visitor, 60 per network, 120 per business, 1,200
for the platform) and reads only that visitor's conversations and messages.
A network is an IPv4 address or the /64 block of an IPv6 address; the caller
chooses the visitor key itself, so the network, business and platform limits
are what bound the model's cost. A refused request counts against no limit.
The counters are shared by every API instance (the `rate_limit_buckets`
table, migration 1041): a one-minute window plus the previous window weighted
by the part of it still inside the sliding minute. Beyond a limit the answer
is 429 with `Retry-After` (exposed to websites through CORS): the widget says
"too many messages" and enables sending and Retry after exactly that many
seconds; polling waits as well. The API's greeting is translated into every
language of the widget's interface (a test compares the lists). Tabs of one
site share one history: each takes over what the others saved. A site with a
strict CSP must allow the API's address in `script-src` and `connect-src`.
`GET /widget/demo?business_id=…` shows the widget as on a website even while
the chat is off (a preview for the owner and for UI tests); its `color`,
`position`, `theme` (`light`/`dark`) and `lang` (or `language`, any of the
widget's languages) show a choice not saved yet.

## The live stream

The answer to a message (202) and every poll carry a `stream_ticket`: a
signed ticket valid for an hour (an HMAC with a key derived from
`ENCRYPTION_KEY` under its own label, over the business, the visitor's key
hash and the expiry). With it the widget opens
`GET /v1/widget/{id}/events?ticket=…` (EventSource cannot send headers, so
the ticket is in the URL while the visitor key stays in bodies and headers;
the access log masks the ticket). The stream uses the same LISTEN publisher
as the cabinet's stream: `typing_started` when a worker took the message,
then `answer_ready`. The answer's text comes with the event only when the
model's answer passed the reply guard (verdict CLEAN), as a draft the next
poll replaces with the stored text; staff answers, bookings and answers the
guard changed reach the widget by polling. A stream lasts 15 minutes and is
then reopened; one API process holds at most 500 streams per business and 20
per network (beyond that, 429). Without EventSource, on a hidden tab and
while the stream is unavailable the widget polls as before; with a live
stream polling stays as a safety net every 15 s. The chat page `/c/…` runs on
the same widget and stream.

When no answer comes within 90 seconds the typing dots never just vanish:
the visitor reads "We will answer as soon as we can" (in every widget
language) and the conversation goes to staff (`POST …/handoff` with
`reason: "no_answer"`: the reason "unusual request", high urgency, and a
summary with the code "model unavailable" and the last question).

## Look

The widget's colours are warm: paper `#faf7f2`/`#f1ece4` by day, ink
`#1a1816`/`#24211e` at night, by the visitor's system theme or by
`data-theme` (`light`, `dark`). The business's colour appears only on the
header, the chat button and the send button; the text on it is white, else
ink, else the colour darkens until white text reads at WCAG AA (the same
computation on the chat page; a test covers any colour).

Before the first message the widget offers up to three questions from the
business's frequent questions in the visitor's language (`starter_questions`
in the config; for a language without ready questions in the FAQ, the
niche's ready questions from the starter answers in en, ru and ka, but never
a question in another language), a "Talk to a person" button
(`POST /v1/widget/{id}/handoff`: the conversation goes to staff and the
visitor sees that someone will answer), "New conversation" in the header
(after a confirmation: a new visitor key; the old conversation stays with
staff) and the line "AI assistant · may make mistakes · Privacy": the link
goes to the business's policy (the "Privacy policy" link in the profile) or
else to the platform's default policy `/c/{address}/privacy` (en, ru, ka).
Every new text exists in every widget language.

## Photos and voice notes

The paper clip sends photos (JPEG, PNG, WebP); the microphone button records
a voice note while it is held (MediaRecorder; without it there is no
button). Each file goes at once to `POST /v1/widget/{id}/attachments` (the
part `file`, the visitor key in `X-Widget-Session-Key`), and the message only
names the uploads (`attachment_ids`, up to four). The API does not trust the
declared type: it reads the type from the file's bytes, strips EXIF and other
metadata from photos (keeping the rotation), and checks size and length
against `MEDIA_MAX_IMAGE_BYTES`, `MEDIA_MAX_VOICE_BYTES` and
`MEDIA_MAX_VOICE_SECONDS` (a voice note is Opus in WebM or Ogg, AAC or Opus
in MP4; the length is measured from the audio packets themselves, not only
the header, so a forged duration does not get past the limit, and a WebM
with an element running past the end of the file is refused). The body is
streamed and read only up to the limit of its declared kind (a photo no
further than `MEDIA_MAX_IMAGE_BYTES`); one API process holds at most
`MEDIA_MAX_CONCURRENT_UPLOADS` uploads at once (the next gets 429 with
`Retry-After`), and a body that has not arrived within 120 seconds gets 422
`upload_too_slow`. The file is kept in the encrypted media store and bound to
the visitor key: another visitor, another business or a file older than a day
is refused (422 `attachment_unavailable`; the widget offers to send the words
without the file), a repeat of a message already sent gets 422
`attachment_already_sent` (the widget waits for the answer to the first try),
and a daily purge deletes uploads never sent. From there the file follows
the path of WhatsApp attachments: a voice note is transcribed
(`TranscribeVoiceNoteUseCase`), a photo is shown to the model. Erasing a
visitor's data deletes the uploads too.

## Ratings

Under an answer that created a booking or a lead, and after two minutes of
silence, the widget asks "Was this answer helpful?" (thumbs up or down, with
an optional reason for down): `POST /v1/widget/{id}/rating` records the
customer's rating (`rating_by=customer`) only in that visitor's conversation
and only under an assistant answer, never replaces the team's rating, and is
limited per visitor, network, business and platform. A customer's bad rating
appears in "Answers worth improving" marked "Customer rating".

## The hosted chat page

`<CABINET_BASE_URL>/c/{address}` is the business's chat on a page of its own,
for links and QR codes (no website needed): the widget in page mode
(`data-mode="page"`, `data-container`), full-screen on a phone, in the
business's colours, in the visitor's language (Accept-Language among the
business's languages), with links to the other channels. The address is a
slug of the name (`cafe-batumi`) that the owner may change in the cabinet;
an old address and the business id redirect to the current one (308, the
`?src=` label kept). The page is not indexed (`X-Robots-Tag` and meta
robots), its CSP allows only the cabinet itself and the API (`connect-src`),
without frames or forms, and the visitor key never reaches the URL. The
script and the API are reached at `APP_BASE_URL`, or without it at the
cabinet's `BACKEND_URL` (fit only when the browser can see it: locally and in
e2e). In the cabinet, Channels → Share offers the links with a Copy button, a
place label (`?src=`), a QR code (made in the browser), PNG and SVG, and an A6
table card to print in the customers' language.

## Source

The script's source is small parts in `app/gateways/http/static/widget/`
(texts by language group, styles, the chat window, polling, network,
storage); the API joins them at start-up in the order of
`app/gateways/http/widget_script_assembly.py` and serves one file with an
ETag.
