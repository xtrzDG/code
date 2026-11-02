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
