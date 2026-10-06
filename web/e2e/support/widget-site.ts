/**
 * A host site with the website chat widget on it, and a fake widget API
 * behind it. The script is the one the real API serves at /widget.js
 * (loaded once per worker with loadWidgetSource); everything else is faked.
 */

import type { BrowserContext, Page, Route } from "@playwright/test";

import { API_URL } from "./env";
import { expect } from "./fixtures";

let WIDGET_SOURCE = "";

/** Fetch the widget script the real API serves; call it from test.beforeAll. */
export async function loadWidgetSource(): Promise<void> {
  const response = await fetch(`${API_URL}/widget.js`);
  expect(response.ok).toBe(true);
  WIDGET_SOURCE = await response.text();
}

export const SITE = "https://shop.example";
export const API = "https://api.example";
export const BUSINESS = "business_0b6c2f5e-1d1a-4c55-9a3e-2f1d5b7c9e01";
export const STORAGE_PREFIX = `aw-chat:${BUSINESS}:`;
/** A stream ticket of the API's shape (66 url-safe characters); the fake API checks nothing. */
export const STREAM_TICKET = `AQ${"x".repeat(64)}`;
const CORS_HEADERS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "Content-Type, X-Widget-Session-Key",
};

interface FakeMessage {
  id: string;
  author: "customer" | "assistant" | "staff";
  text: string;
  direction?: "ltr" | "rtl";
}

/** The widget API of one business, as GetWidgetMessagesUseCase answers. */
export class FakeWidgetApi {
  messages: FakeMessage[] = [];
  isHandedOff = false;
  /** POSTs are recorded and answered on the server, but the page never gets the reply. */
  holdPosts = false;
  /** Answers wait for releaseAnswers(), like a worker still writing them. */
  holdAnswers = false;
  private heldAnswers: string[] = [];
  /** The next POSTs are refused with 429 and this Retry-After (seconds). */
  refusePostsFor: number | null = null;
  polls: { url: string; sessionKey: string | null }[] = [];
  /** More config fields (starter questions, privacy link, other channels). */
  configExtras: Record<string, unknown> = {};
  /** The visitor keys of the messages sent, in order. */
  sessionKeys: string[] = [];
  /** "Talk to a person" requests (and the widget's own, reason no_answer). */
  handoffs: { session_key: string; language: string; reason?: string }[] = [];
  /** Answers with a stream ticket (202s and polls): the widget opens its live stream. */
  streamTickets = false;
  /** The live stream's requests and the events its next connection sends. */
  streamRequests: string[] = [];
  private streamEvents: string[] = [];
  /** Stored messages polls do not show yet (an answer the stream announced first). */
  hiddenIds = new Set<string>();
  private nextId = 1;

  async handle(route: Route): Promise<void> {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: CORS_HEADERS });
      return;
    }
    if (url.pathname.endsWith("/events")) {
      // One short connection per call: what is queued, then the browser
      // reconnects (retry) like after a dropped long-lived stream.
      this.streamRequests.push(request.url());
      const body = ["retry: 200\n\n", "event: stream.ready\ndata: {}\n\n", ...this.streamEvents.splice(0)].join("");
      await route.fulfill({ status: 200, headers: { ...CORS_HEADERS, "content-type": "text/event-stream" }, body });
      return;
    }
    if (url.pathname.endsWith("/config")) {
      await this.json(route, {
        is_enabled: true,
        business_name: "Cafe Batumi",
        languages: [{ tag: "en", direction: "ltr", native_name: "English" }],
        default_language: "en",
        ...this.configExtras,
      });
      return;
    }
    if (request.method() === "POST" && url.pathname.endsWith("/handoff")) {
      this.handoffs.push(JSON.parse(request.postData() ?? "{}") as FakeWidgetApi["handoffs"][number]);
      this.isHandedOff = true;
      const notice = this.add("assistant", "A person from our team will answer here.");
      await this.json(route, {
        conversation_id: "conversation_1",
        is_handed_off: true,
        message_id: notice.id,
        text: notice.text,
        language: "en",
        direction: "ltr",
      });
      return;
    }
    if (request.method() === "POST" && this.refusePostsFor !== null) {
      await route.fulfill({
        status: 429,
        headers: {
          ...CORS_HEADERS,
          "access-control-expose-headers": "Retry-After",
          "retry-after": String(this.refusePostsFor),
        },
        json: { error: "rate_limited", message: "Too many messages; wait a moment before sending another." },
      });
      return;
    }
    if (request.method() === "POST") {
      const body = JSON.parse(request.postData() ?? "{}") as { text: string; session_key: string };
      this.sessionKeys.push(body.session_key);
      // Accepted at once (202), like the API: a worker answers, the widget polls.
      this.add("customer", body.text);
      if (this.holdAnswers) {
        this.heldAnswers.push(`Answer to ${body.text}`);
      } else {
        this.add("assistant", `Answer to ${body.text}`);
      }
      if (this.holdPosts) {
        // The visitor leaves before the answer arrives: the request is
        // never answered and the browser drops it on navigation.
        return;
      }
      await this.json(route, { event_id: `inbound_event_${this.nextId}`, ...this.ticket() }, 202);
      return;
    }
    this.polls.push({ url: request.url(), sessionKey: request.headers()["x-widget-session-key"] ?? null });
    await this.json(route, { ...this.page(url.searchParams.get("after")), ...this.ticket() });
  }

  /** An event the stream sends on its next connection ("typing_started", "answer_ready"). */
  pushEvent(name: string, data: Record<string, unknown>): void {
    this.streamEvents.push(`event: ${name}\ndata: ${JSON.stringify(data)}\n\n`);
  }

  private ticket(): { stream_ticket?: string } {
    return this.streamTickets ? { stream_ticket: STREAM_TICKET } : {};
  }

  /** The worker finishes the answers held so far; the next poll brings them. */
  releaseAnswers(): void {
    for (const text of this.heldAnswers.splice(0)) {
      this.add("assistant", text);
    }
  }

  add(author: FakeMessage["author"], text: string, direction: "ltr" | "rtl" = "ltr"): FakeMessage {
    const message = { id: `m${this.nextId++}`, author, text, direction };
    this.messages.push(message);
    return message;
  }

  private page(after: string | null) {
    // A hidden message is not stored yet as far as polls can tell.
    const stored = this.messages.filter((message) => !this.hiddenIds.has(message.id));
    const index = after === null ? -1 : stored.findIndex((message) => message.id === after);
    const latest = stored.at(-1)?.id ?? null;
    if (index === -1) {
      const ownLatest = stored.filter((message) => message.author === "customer").at(-1)?.id;
      return { items: [], cursor: ownLatest ?? latest, has_more: false, is_handed_off: this.isHandedOff };
    }
    const items = stored.slice(index + 1).filter((message) => message.author !== "customer");
    return { items, cursor: latest, has_more: false, is_handed_off: this.isHandedOff };
  }

  private async json(route: Route, body: unknown, status = 200): Promise<void> {
    await route.fulfill({ status, headers: CORS_HEADERS, json: body });
  }
}

/** A two-page host site with the widget snippet, and the fake API behind it. */
export async function serveSite(
  context: BrowserContext,
  api: FakeWidgetApi,
  options: { dataOpen?: boolean; attributes?: Record<string, string> } = {},
) {
  const extra = Object.entries(options.attributes ?? {})
    .map(([name, value]) => ` ${name}="${value}"`)
    .join("");
  await context.route(`${SITE}/**`, (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/favicon.ico") {
      return route.fulfill({ status: 204 });
    }
    return route.fulfill({
      contentType: "text/html",
      body:
        `<!doctype html><html lang="en"><head><title>Shop ${pathname}</title></head><body>` +
        `<h1>Shop page ${pathname}</h1><a href="/next">Next page</a>` +
        `<script src="${API}/widget.js" data-tenant="${BUSINESS}"${options.dataOpen ? ' data-open="true"' : ""}${extra} async></script>` +
        `</body></html>`,
    });
  });
  await context.route(`${API}/widget.js`, (route) =>
    // UTF-8 like the real API: the host page itself declares no charset.
    route.fulfill({ contentType: "application/javascript; charset=utf-8", body: WIDGET_SOURCE }),
  );
  await context.route(`${API}/v1/widget/**`, (route) => api.handle(route));
}

/** The chat panel (the status line for screen readers repeats some texts). */
export function chat(page: Page) {
  return page.getByRole("dialog");
}

export async function ask(page: Page, question: string): Promise<void> {
  await page.getByRole("textbox").fill(question);
  await page.getByRole("textbox").press("Enter");
}

/** The texts of the chat's message bubbles, greeting first. */
export async function chatTexts(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const root = document.querySelector("[data-assistant-workshop-chat]")?.shadowRoot;
    return Array.from(root?.querySelectorAll(".aw-message") ?? []).map((row) => row.textContent ?? "");
  });
}
