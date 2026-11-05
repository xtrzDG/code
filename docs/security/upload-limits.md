# Upload and download limits

Every surface that takes a file or reads one from an address, with the
types it accepts, how the type is checked and its size limits. No surface
accepts an archive (zip, DOCX, XLSX), so an unpacked size applies only to
compressed HTTP answers, which are counted after decompression. The
numbers below are the code's defaults;
`tests/security/test_upload_limits_document.py` fails when this page and
the code disagree.

| Surface | Accepted types | Type check | Size limits | Stored as |
| --- | --- | --- | --- | --- |
| Website chat photo (`POST /v1/widget/{business_id}/attachments`) | JPEG, PNG, WebP | declared type and first bytes must agree (`app/utilities/media/upload_checks.py`, `media_sniffing.py`); metadata stripped | `MEDIA_MAX_IMAGE_BYTES` (default 5 MiB); request body 26 MiB (413 above); 4 files per message | encrypted, server-generated id under the business's path; served with `nosniff`, a sandbox CSP and `no-store` |
| Website chat voice note (same route) | WebM or Ogg with Opus, MP4 with AAC or Opus | declared type, first bytes and audio tracks; length read from the audio | `MEDIA_MAX_VOICE_BYTES` (default 16 MiB), `MEDIA_MAX_VOICE_SECONDS` (default 300 s); request body 26 MiB | as above |
| Messenger media (WhatsApp, Telegram, Instagram, Messenger) | pictures and audio | first bytes (`sniff_media_type`); HTML, SVG and PDF refused | the same `MEDIA_MAX_*` caps, while downloading (`app/clients/http/media_download.py`) | as above |
| Menu import file (`POST /v1/businesses/{business_id}/knowledge/import`) | JPEG, PNG, WebP, GIF, PDF, UTF-8 text and CSV; never HTML or SVG | declared type and first bytes must agree; text must be UTF-8 without NUL bytes and not markup (`app/use_cases/menu_import/menu_upload_checks.py`) | 15 MB file (20 MiB of base64); request body 21 MiB (413 above); text read up to 60,000 characters | not stored: sent to the model provider once, never parsed locally |
| Menu link (same route, `url`) | the served type, HTML included | served type checked by `SafeHttpFetcher` | 10 MiB after decompression | not stored |
| Website import (`POST /v1/businesses/{business_id}/knowledge/import-website`) | HTML, XHTML, plain text; sitemaps as XML | served type | 15 pages, 5 MiB each after decompression, 30,000 characters read per page | knowledge drafts (text only) |
| Calendar feed (ICS address) | iCalendar | served type | 4 MiB after decompression | busy times only |
| Telegram bot picture | pictures | first bytes | 96 KiB | channel avatar |

Outbound answers that are not files (provider APIs) are capped by the
shared HTTP client (`app/clients/http/provider_http_client.py`).

## Not done yet

- Antivirus scanning: none of these files is scanned. The owner decides
  between a scanning service (for example ClamAV beside the API) and a
  reviewed risk acceptance; until then the type checks above, the
  encryption at rest and the download headers are the controls.
- Container parsers of voice notes (MP4, Ogg, WebM length readers) run in
  the API process without a worker of their own; the request deadline
  (170 s) bounds them.
