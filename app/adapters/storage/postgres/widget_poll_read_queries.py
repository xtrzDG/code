"""
The statement of a website-widget poll (`PostgresWidgetPollReadAdapter`).

One statement reads what three repositories read in four (the business's
widget limits, the visitor's conversations, the newest positions, the
messages after the cursor): `workshop.read_widget_poll` (migration 1216),
a PL/pgSQL function so the database keeps its plan (the application sends
no prepared statements). Each part reads by the index the repositories
use:

- `business_limits` by its key (the derived id of the business);
- `conversations` by `(business_id, doc_channel_user_id)`, numbered in the
  repositories' order (last message first, ties in first-write order);
- per shown conversation (web chat, not sandbox) its newest `window`
  messages backwards on `(business_id, doc_conversation_id,
  doc_created_at)`, then the newest `window` of them all (several
  conversations of one visitor are rare; each reads at most `window` rows);
- the documents of those that come after the cursor in answer order
  (created_at, then id in code-point order, as `message_order`), and no
  other document (a poll that finds nothing new decodes none).

Every row carries its kind; the business filter is explicit on every
table besides row-level security (the caller's scope).
"""

from typing import LiteralString

ORIGINS_ROW: str = "origins"
CONVERSATION_ROW: str = "conversation"
MESSAGE_ROW: str = "message"

WIDGET_POLL_READ: LiteralString = """
select kind, poll_position, row_key, is_shown, row_document
from workshop.read_widget_poll(
    %(business_id)s::text,
    %(visitor)s::text,
    %(web_chat)s::text,
    %(limits_key)s::text,
    %(window)s::integer,
    %(after)s::text
)
"""
