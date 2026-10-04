/**
 * The cabinet's live preview of the website chat: the Channels page frames
 * the hosted chat page of its own origin (/c/{address}?preview=1) and tells
 * it the colour, corner and language the owner is choosing, before anything
 * is saved. The page shows the chat open over a sketch of a website; the
 * widget (data-preview="live") sends nothing and keeps nothing.
 *
 * The first look rides in the address (no flash of the saved one); later
 * changes go by window.postMessage, same origin only, once the widget says
 * it is ready. The message names match widget.js (header.js).
 */

export const PREVIEW_QUERY = "preview";
const PREVIEW_ON = "1";

export const PREVIEW_LOOK_MESSAGE = "assistant-workshop:preview-look";
export const PREVIEW_READY_MESSAGE = "assistant-workshop:preview-ready";

export type PreviewPosition = "left" | "right";

export interface PreviewLook {
  color: string | null;
  position: PreviewPosition | null;
  language: string | null;
}

const COLOR_PATTERN = /^#[0-9a-f]{6}$/i;
const LANGUAGE_PATTERN = /^[a-z]{2,3}(?:-[a-z0-9]{2,8}){0,3}$/i;

/** The address the Channels page frames: /c/{address}?preview=1&color=…&position=…&lang=… */
export function buildChatPreviewPath(address: string, look: PreviewLook): string {
  const query = new URLSearchParams({ [PREVIEW_QUERY]: PREVIEW_ON });
  const { color, position, language } = cleanPreviewLook(look);
  if (color) {
    query.set("color", color);
  }
  if (position) {
    query.set("position", position);
  }
  if (language) {
    query.set("lang", language);
  }
  return `/c/${encodeURIComponent(address)}?${query.toString()}`;
}

/** Whether a hosted chat request is the cabinet's preview (it may then be framed by the cabinet). */
export function isPreviewRequest(query: URLSearchParams): boolean {
  return query.get(PREVIEW_QUERY) === PREVIEW_ON;
}

type SearchParams = Record<string, string | string[] | undefined>;

function single(value: string | string[] | undefined): string | null {
  return typeof value === "string" ? value : null;
}

/** The first look of a preview page, from its address; null when the page is not a preview. */
export function readPreviewLook(searchParams: SearchParams): PreviewLook | null {
  if (single(searchParams[PREVIEW_QUERY]) !== PREVIEW_ON) {
    return null;
  }
  return cleanPreviewLook({
    color: single(searchParams.color),
    position: single(searchParams.position) as PreviewPosition | null,
    language: single(searchParams.lang),
  });
}

/** Only well-formed values: the widget gets nothing it would have to guess about. */
export function cleanPreviewLook(look: PreviewLook): PreviewLook {
  return {
    color: look.color && COLOR_PATTERN.test(look.color) ? look.color.toLowerCase() : null,
    position: look.position === "left" || look.position === "right" ? look.position : null,
    language: look.language && LANGUAGE_PATTERN.test(look.language) ? look.language : null,
  };
}

/** The message that changes the framed preview's look. */
export function previewLookMessage(look: PreviewLook): { type: string } & PreviewLook {
  return { type: PREVIEW_LOOK_MESSAGE, ...cleanPreviewLook(look) };
}

/** Whether a window message is the framed preview saying it is ready (same origin, our frame). */
export function isPreviewReady(event: Pick<MessageEvent, "data" | "origin" | "source">, frame: Window | null, origin: string): boolean {
  const data: unknown = event.data;
  return (
    frame !== null &&
    event.source === frame &&
    event.origin === origin &&
    typeof data === "object" &&
    data !== null &&
    (data as { type?: unknown }).type === PREVIEW_READY_MESSAGE
  );
}
