/**
 * The website chat widget (app/gateways/http/static/widget.js) on a host
 * site, against a fake widget API: polling, page changes, several tabs,
 * screen readers and text direction. No server is needed; the shipped
 * script is served as it is.
 */

import { readFileSync } from "node:fs";
import path from "node:path";

import type { BrowserContext, Page, Route } from "@playwright/test";

import { REPOSITORY_ROOT } from "./support/env";
import { expect, test } from "./support/fixtures";

const WIDGET_SOURCE = readFileSync(path.join(REPOSITORY_ROOT, "app/gateways/http/static/widget.js"), "utf8");
const SITE = "https://shop.example";
const API = "https://api.example";
const BUSINESS = "business_0b6c2f5e-1d1a-4c55-9a3e-2f1d5b7c9e01";
const STORAGE_PREFIX = `aw-chat:${BUSINESS}:`;
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
class FakeWidgetApi {
  messages: FakeMessage[] = [];
  isHandedOff = false;
  /** POSTs are recorded and answered on the server, but the page never gets the reply. */
  holdPosts = false;
  /** The next POSTs are refused with 429 and this Retry-After (seconds). */
  refusePostsFor: number | null = null;
  polls: { url: string; sessionKey: string | null }[] = [];
  private nextId = 1;

  async handle(route: Route): Promise<void> {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: CORS_HEADERS });
      return;
    }
    if (url.pathname.endsWith("/config")) {
      await this.json(route, {
        is_enabled: true,
        business_name: "Cafe Batumi",
        languages: [{ tag: "en", direction: "ltr", native_name: "English" }],
        default_language: "en",
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
      const body = JSON.parse(request.postData() ?? "{}") as { text: string };
      const question = this.add("customer", body.text);
      const answer = this.add("assistant", `Answer to ${body.text}`);
      const reply = { text: answer.text, message_id: answer.id, cursor: question.id, is_handed_off: false, direction: "ltr" };
      if (this.holdPosts) {
        // The visitor leaves before the answer arrives: the request is
        // never answered and the browser drops it on navigation.
        return;
      }
      await this.json(route, reply);
      return;
    }
    this.polls.push({ url: request.url(), sessionKey: request.headers()["x-widget-session-key"] ?? null });
    await this.json(route, this.page(url.searchParams.get("after")));
  }

  add(author: FakeMessage["author"], text: string, direction: "ltr" | "rtl" = "ltr"): FakeMessage {
    const message = { id: `m${this.nextId++}`, author, text, direction };
    this.messages.push(message);
    return message;
  }

  private page(after: string | null) {
    const index = after === null ? -1 : this.messages.findIndex((message) => message.id === after);
    const latest = this.messages.at(-1)?.id ?? null;
    if (index === -1) {
      const ownLatest = this.messages.filter((message) => message.author === "customer").at(-1)?.id;
      return { items: [], cursor: ownLatest ?? latest, has_more: false, is_handed_off: this.isHandedOff };
    }
    const items = this.messages.slice(index + 1).filter((message) => message.author !== "customer");
    return { items, cursor: latest, has_more: false, is_handed_off: this.isHandedOff };
  }

  private async json(route: Route, body: unknown): Promise<void> {
    await route.fulfill({ headers: CORS_HEADERS, json: body });
  }
}

/** A two-page host site with the widget snippet, and the fake API behind it. */
async function serveSite(context: BrowserContext, api: FakeWidgetApi, options: { dataOpen?: boolean } = {}) {
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
        `<script src="${API}/widget.js" data-tenant="${BUSINESS}"${options.dataOpen ? ' data-open="true"' : ""} async></script>` +
        `</body></html>`,
    });
  });
  await context.route(`${API}/widget.js`, (route) =>
    route.fulfill({ contentType: "application/javascript", body: WIDGET_SOURCE }),
  );
  await context.route(`${API}/v1/widget/**`, (route) => api.handle(route));
}

/** The chat panel (the status line for screen readers repeats some texts). */
function chat(page: Page) {
  return page.getByRole("dialog");
}

async function ask(page: Page, question: string): Promise<void> {
  await page.getByRole("textbox").fill(question);
  await page.getByRole("textbox").press("Enter");
}

/** The texts of the chat's message bubbles, greeting first. */
async function chatTexts(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const root = document.querySelector("[data-assistant-workshop-chat]")?.shadowRoot;
    return Array.from(root?.querySelectorAll(".aw-message") ?? []).map((row) => row.textContent ?? "");
  });
}

test("an open chat shows a staff message written without a handoff", async ({ page }) => {
  const api = new FakeWidgetApi();
  await page.clock.install();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await ask(page, "Is the terrace open?");
  await expect(chat(page).getByText("Answer to Is the terrace open?")).toBeVisible();
  api.add("staff", "Correction: the terrace opens at 18:00.");
  // The widget schedules its next poll after it has drawn the answer, so a
  // single jump can land before that timer exists. Keep moving the clock
  // until the staff message arrives.
  await expect(async () => {
    await page.clock.fastForward(15_000);
    await expect(chat(page).getByText("Correction: the terrace opens at 18:00.")).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: 30_000 });
  // The visitor key travels in a header, never in the URL.
  expect(api.polls.length).toBeGreaterThan(1);
  for (const poll of api.polls) {
    expect(poll.url).not.toContain("session_key");
    expect(poll.sessionKey).toMatch(/^v1_/);
  }
});

test("a message refused as too fast can be retried once the API's wait is over", async ({ page, consoleErrors }) => {
  consoleErrors.allow(/status of 429/);
  const api = new FakeWidgetApi();
  api.refusePostsFor = 8;
  await page.clock.install();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await ask(page, "Table for two?");

  await expect(chat(page).getByText("Too many messages. Please wait a moment and try again.")).toBeVisible();
  const retry = chat(page).getByRole("button", { name: "Retry" });
  await expect(retry).toBeDisabled();
  await page.getByRole("textbox").fill("Hello?");
  await expect(chat(page).getByRole("button", { name: "Send" })).toBeDisabled();
  expect(api.messages).toEqual([]);

  api.refusePostsFor = null;
  await page.clock.runFor(8_100);
  await expect(retry).toBeEnabled();
  await expect(chat(page).getByRole("button", { name: "Send" })).toBeEnabled();
  await retry.click();

  await expect(chat(page).getByText("Answer to Table for two?")).toBeVisible();
  await expect(chat(page).getByText("Too many messages. Please wait a moment and try again.")).toBeHidden();
});

test("a closed chat without any exchange does not poll", async ({ page }) => {
  const api = new FakeWidgetApi();
  await page.clock.install();
  await serveSite(page.context(), api);
  await page.goto(`${SITE}/`);
  await expect(page.getByRole("button", { name: "Open chat" })).toBeVisible();

  await page.clock.fastForward(120_000);

  expect(api.polls).toEqual([]);
});

test("closing the chat keeps it closed on the next page despite data-open", async ({ page }) => {
  const api = new FakeWidgetApi();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);
  await expect(page.getByRole("textbox")).toBeVisible();

  await page.getByRole("button", { name: "Close chat", expanded: true }).click();
  await page.getByRole("link", { name: "Next page" }).click();

  await expect(page.getByRole("heading", { name: "Shop page /next" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Open chat", expanded: false })).toBeVisible();
  await expect(page.getByRole("textbox")).toBeHidden();
});

test("a reply to a closed chat is announced and named on the launcher", async ({ page }) => {
  const api = new FakeWidgetApi();
  const question = api.add("customer", "Can I talk to someone?");
  api.add("staff", "Hi, this is Anna");
  api.isHandedOff = true;
  await page.addInitScript(
    ({ prefix, cursor }) => {
      window.localStorage.setItem(`${prefix}handoff`, "1");
      window.localStorage.setItem(`${prefix}cursor`, cursor);
    },
    { prefix: STORAGE_PREFIX, cursor: question.id },
  );
  await serveSite(page.context(), api);
  await page.goto(`${SITE}/`);

  await expect(page.getByRole("button", { name: "Open chat (New reply)", expanded: false })).toBeVisible();
  await expect(page.getByRole("status")).toHaveText("New reply");

  await page.getByRole("button", { name: "Open chat (New reply)" }).click();
  await expect(chat(page).getByText("Hi, this is Anna")).toBeVisible();
  await page.getByRole("button", { name: "Close chat", expanded: true }).click();
  await expect(page.getByRole("button", { name: "Open chat", exact: true })).toBeVisible();
});

test("an answer written after the visitor left the page appears on the next page", async ({ page }) => {
  const api = new FakeWidgetApi();
  api.holdPosts = true;
  await page.clock.install();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await ask(page, "Do you deliver to Batumi?");
  await expect.poll(() => api.messages.length).toBe(2);
  await page.getByRole("link", { name: "Next page" }).click();
  await expect(page.getByRole("heading", { name: "Shop page /next" })).toBeVisible();
  await expect(chat(page).getByText("Do you deliver to Batumi?")).toBeVisible();

  // The new page asks for its position, then for what came after it.
  await expect(async () => {
    await page.clock.fastForward(5_000);
    await expect(chat(page).getByText("Answer to Do you deliver to Batumi?")).toBeVisible({ timeout: 500 });
  }).toPass({ timeout: 20_000 });
  expect((await chatTexts(page)).slice(1)).toEqual(["Do you deliver to Batumi?", "Answer to Do you deliver to Batumi?"]);
});

test("two tabs keep one ordered chat history", async ({ context }) => {
  const api = new FakeWidgetApi();
  await serveSite(context, api, { dataOpen: true });
  const first = await context.newPage();
  const second = await context.newPage();
  await first.goto(`${SITE}/`);
  await second.goto(`${SITE}/`);

  await ask(first, "parking");
  await expect(chat(first).getByText("Answer to parking")).toBeVisible();
  await ask(second, "hours");
  await expect(chat(second).getByText("Answer to hours")).toBeVisible();
  const third = await context.newPage();
  await third.goto(`${SITE}/`);

  await expect(chat(third).getByText("Answer to hours")).toBeVisible();
  expect((await chatTexts(third)).slice(1)).toEqual(["parking", "Answer to parking", "hours", "Answer to hours"]);
});

test("business messages marked right-to-left stay right-to-left", async ({ page }) => {
  const api = new FakeWidgetApi();
  await page.addInitScript((prefix) => {
    window.localStorage.setItem(
      `${prefix}history`,
      JSON.stringify([
        { role: "visitor", text: "iPhone شاشة مكسورة" },
        { role: "assistant", id: "m1", text: "Pizza Roma مفتوح يوميًا من 10:00 إلى 22:00.", direction: "rtl" },
        { role: "staff", id: "m2", text: "Hello, I will check that for you.", direction: "rtl" },
        { role: "staff", id: "m3", text: "+995 555 12 34 56", direction: "rtl" },
      ]),
    );
  }, STORAGE_PREFIX);
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await expect(chat(page).getByText("Pizza Roma", { exact: false })).toHaveAttribute("dir", "rtl");
  await expect(chat(page).getByText("Hello, I will check that for you.")).toHaveAttribute("dir", "auto");
  await expect(chat(page).getByText("+995 555 12 34 56")).toHaveAttribute("dir", "auto");
  await expect(chat(page).getByText("iPhone شاشة مكسورة")).toHaveAttribute("dir", "auto");
});
