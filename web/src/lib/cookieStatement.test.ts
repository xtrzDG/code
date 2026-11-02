import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { LOCALE_COOKIE } from "@/i18n/config";
import { ATTRIBUTION_COOKIE } from "@/lib/attribution";
import { MOTION_COOKIE } from "@/lib/motionPreference";
import { SIDEBAR_COOKIE } from "@/lib/shellPreferences";
import { THEME_COOKIE } from "@/lib/theme";
import { VIEWER_TIME_ZONE_COOKIE } from "@/lib/viewerTimeZone";
import { CONSENT_COOKIE, CONSENT_MAX_AGE_SECONDS } from "@/server/consentCookie";
import { SECURE_SESSION_COOKIE } from "@/server/sessionCookie";

/**
 * Every cookie the cabinet sets is in the published cookie statement
 * (docs/legal/cookies-<date>.<language>.md, served by GET /v1/legal/cookies),
 * in each of its languages, with what it does and how long it lives. The
 * plain-HTTP name of the session cookie (aw_session: development and local
 * runs only) is the same cookie as __Host-aw_session. The cookie that needs
 * consent says so, and the consent cookie lives as long as it says.
 */
const COOKIES = [
  SECURE_SESSION_COOKIE,
  LOCALE_COOKIE,
  THEME_COOKIE,
  SIDEBAR_COOKIE,
  ATTRIBUTION_COOKIE,
  MOTION_COOKIE,
  VIEWER_TIME_ZONE_COOKIE,
  CONSENT_COOKIE,
];

/** A row's cells: name, purpose, lifetime. */
function rowOf(text: string, cookie: string): string[] | undefined {
  return text
    .split("\n")
    .find((line) => line.startsWith(`| ${cookie} |`))
    ?.split("|")
    .map((cell) => cell.trim())
    .filter((cell) => cell !== "");
}

const LEGAL_DIRECTORY = path.resolve(__dirname, "..", "..", "..", "docs", "legal");

/** The newest statement's files by language: the one in force or announced next. */
function latestStatement(): Map<string, string> {
  const files = readdirSync(LEGAL_DIRECTORY).filter((name) => /^cookies-\d{4}-\d{2}-\d{2}\.[a-z]{2}\.md$/.test(name));
  const latest = files.map((name) => name.slice("cookies-".length, "cookies-".length + 10)).sort().at(-1);
  return new Map(
    files
      .filter((name) => name.includes(`-${latest}.`))
      .map((name) => [name.split(".").at(-2) ?? "", readFileSync(path.join(LEGAL_DIRECTORY, name), "utf8")]),
  );
}

describe("the cookie statement", () => {
  const statement = latestStatement();

  it("is published in English, the legal texts' only language today (docs/legal/README.md)", () => {
    expect([...statement.keys()].sort()).toEqual(["en"]);
  });

  it.each(COOKIES)("lists %s with its purpose and lifetime in every language", (cookie) => {
    for (const [language, text] of statement) {
      const row = rowOf(text, cookie);
      expect(row, `${cookie} in the ${language} statement`).toBeDefined();
      // Name, purpose, lifetime.
      expect(row).toHaveLength(3);
    }
  });

  it("says that the attribution cookie needs consent, and keeps the consent cookie six months", () => {
    // The banner (components/consent) asks for aw_attr; aw_consent lives CONSENT_MAX_AGE_SECONDS.
    expect(CONSENT_MAX_AGE_SECONDS).toBeGreaterThanOrEqual(182 * 24 * 60 * 60);
    expect(CONSENT_MAX_AGE_SECONDS).toBeLessThanOrEqual(184 * 24 * 60 * 60);
    for (const text of statement.values()) {
      expect(rowOf(text, ATTRIBUTION_COOKIE)?.[1]).toMatch(/^Only with your consent\./);
      expect(rowOf(text, CONSENT_COOKIE)?.[2]).toBe("6 months");
      expect(text).toContain("Cookie settings");
    }
  });
});

const REPOSITORY = path.resolve(__dirname, "..", "..", "..");
const WIDGET_DIRECTORY = path.join(REPOSITORY, "app", "gateways", "http", "static", "widget");
const BOOKING_PAGE_SESSION = path.join(REPOSITORY, "web", "src", "app", "r", "[token]", "_lib", "pageSession.ts");

/** The widget's scripts (app/gateways/http/static/widget/*.js), joined. */
function widgetSource(): string {
  return readdirSync(WIDGET_DIRECTORY)
    .filter((name) => name.endsWith(".js"))
    .sort()
    .map((name) => readFileSync(path.join(WIDGET_DIRECTORY, name), "utf8"))
    .join("\n");
}

/** The keys the widget keeps directly in one storage (not in the conversation's own storage). */
function keysKeptIn(source: string, storage: "localStorageOrNull" | "sessionStorageOrNull"): string[] {
  const pattern = new RegExp(`\\(${storage}\\(\\), storagePrefix \\+ "([a-z-]+)"`, "g");
  return [...new Set([...source.matchAll(pattern)].map((match) => match[1] ?? ""))].sort();
}

/** The widget's other uses of one storage: those that do not name their key in place, trimmed. */
function otherUsesOf(source: string, storage: "localStorageOrNull" | "sessionStorageOrNull"): string[] {
  return source
    .split("\n")
    .map((line) => line.trim())
    .filter(
      (line) =>
        line.includes(`${storage}()`) &&
        !line.includes(`${storage}(), storagePrefix + "`) &&
        !line.startsWith(`function ${storage}()`),
    )
    .sort();
}

/** CONVERSATION_IDLE_EXPIRY_MS of the widget, in hours. */
function idleExpiryHours(source: string): number {
  const product = /var CONVERSATION_IDLE_EXPIRY_MS = ([\d\s*]+);/.exec(source)?.[1];
  expect(product, "CONVERSATION_IDLE_EXPIRY_MS in the widget").toBeDefined();
  const milliseconds = (product ?? "0").split("*").reduce((total, factor) => total * Number(factor.trim()), 1);
  return milliseconds / (60 * 60 * 1000);
}

/** Section 4 of a statement, on one line. */
function storageSection(text: string): string {
  const start = text.indexOf("## 4. Storage in your browser");
  expect(start, "section 4 of the statement").toBeGreaterThanOrEqual(0);
  return text.slice(start, text.indexOf("\n## 5.", start)).replace(/\s+/g, " ");
}

describe("the cookie statement's storage section", () => {
  const statement = latestStatement();
  const widget = widgetSource();

  it("says the chat page keeps the conversation for the tab only and removes an older copy", () => {
    // storage.js: the chat page (data-mode="page") keeps the conversation in
    // sessionStorage and forgets one an earlier version left in localStorage.
    expect(widget).toContain("return isPageMode ? sessionStorageOrNull() : localStorageOrNull();");
    expect(widget).toMatch(/if \(isPageMode\) \{\s*forgetConversationOn\(localStorageOrNull\(\)\);/);
    for (const text of statement.values()) {
      const section = storageSection(text);
      expect(section).toContain("in the storage of the browser tab only, so it is gone when the tab is closed");
      expect(section).toContain(
        "removes a conversation that an earlier version of the page kept in the browser's local storage",
      );
    }
  });

  it("names everything else the widget keeps in local storage and in the tab", () => {
    expect(keysKeptIn(widget, "localStorageOrNull")).toEqual(["language", "rated"]);
    expect(keysKeptIn(widget, "sessionStorageOrNull")).toEqual(["open"]);
    // The visit source (data-source, ?src=, ?utm_source=) is kept for the tab too.
    expect(widget).toMatch(/function loadVisitSource\(\) \{\s*var storage = sessionStorageOrNull\(\);/);
    // Nothing else reaches either storage: the conversation's own choice of
    // storage, the removal of an older copy and the visit source are all.
    const conversationChoice = "return isPageMode ? sessionStorageOrNull() : localStorageOrNull();";
    expect(otherUsesOf(widget, "localStorageOrNull")).toEqual(
      [conversationChoice, "forgetConversationOn(localStorageOrNull());"].sort(),
    );
    expect(otherUsesOf(widget, "sessionStorageOrNull")).toEqual(
      [conversationChoice, "var storage = sessionStorageOrNull();"].sort(),
    );
    expect(widget.split("window.localStorage").length - 1).toBe(1);
    expect(widget.split("window.sessionStorage").length - 1).toBe(1);
    for (const text of statement.values()) {
      const section = storageSection(text);
      expect(section).toContain("Only the language you chose and the answers you rated stay in local storage.");
      expect(section).toContain("for the tab only, whether the chat is open and the source the page names");
    }
  });

  it("keeps a site's widget conversation as long as the widget does", () => {
    const hours = idleExpiryHours(widget);
    expect(hours).toBe(24);
    for (const text of statement.values()) {
      expect(storageSection(text)).toContain(`for up to ${hours} hours after the last message`);
    }
  });

  it("says the booking page keeps its short credential for the tab only", () => {
    const pageSession = readFileSync(BOOKING_PAGE_SESSION, "utf8");
    expect(pageSession).toContain("window.sessionStorage.setItem(STORAGE_KEY");
    expect(pageSession).not.toContain("localStorage");
    for (const text of statement.values()) {
      expect(storageSection(text)).toContain("keeps it in the storage of the browser tab only");
    }
  });
});
