# Help center articles

The articles of the cabinet's help center (`/help`, the "?" beside a page's
title), served by `GET /v1/help/{language}` and
`GET /v1/help/{language}/{slug}` (`app/registries/help/`).

- One folder per language (`en`, `ru`, `ka`), the same file names (slugs) in
  every folder: `tests/help/test_help_articles.py` fails otherwise.
- Each file starts with front matter and its `# ` title:

  ```markdown
  ---
  summary: One or two sentences: what the article answers.
  topic: getting_started | channels | daily_work | account
  order: 10
  keywords: words owners search with, in this language
  related: other-slug, another-slug
  ---
  # Title
  ```

- Links: `[text](other-slug)` opens another article in place,
  `[text](cabinet:assistant/channels)` opens that page of the business the
  owner is in (plain text outside a business), `https://` links open in a new
  tab. Headings (`##`), lists, numbered lists, tables, `**bold**`, `` `code` ``
  and `> ` tips are rendered; nothing becomes HTML.
- Which page opens which article: `web/src/lib/help/helpTopics.ts`.
