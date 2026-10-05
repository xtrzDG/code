/**
 * The `test` of the suite: Playwright's, plus
 *
 *   - the console-clean gate (support/consoleClean.ts): no page of the
 *     test's context may throw, log a console error the test did not
 *     accept (`consoleErrors.allow(/…/)`) or fail hydration (React #418,
 *     #423: never acceptable); with `cyrillicCheck` on, no English or
 *     Georgian page may show interface text in Cyrillic;
 *   - requests counted on every page, for `waitForNetworkQuiet` (support/network.ts);
 *   - `account`: a new account created through the API, with the browser
 *     context signed in as it (interface in English);
 *   - `newOwner`: the same plus one business (a hair salon in Berlin) whose
 *     assistant does not exist yet: the cabinet shows "Create an AI assistant";
 *   - `owner`: that business with its assistant created (the setup done), so
 *     the five sections are open.
 */

import { test as base, expect, type BrowserContext } from "@playwright/test";

import { createAssistant, createBusiness, signInByEmail, uniqueEmail, type NewBusiness } from "./api";
import { strayCyrillic, unexpectedErrors, watchContext, type ConsoleRecord } from "./consoleClean";
import { WEB_URL } from "./env";
import { trackRequests } from "./network";

export interface Account {
  email: string;
  token: string;
}

export interface Owner extends Account {
  businessId: string;
  businessName: string;
}

/** The cabinet's session and language cookies, as the sign-in route sets them. */
export async function signInContext(context: BrowserContext, token: string): Promise<void> {
  await context.addCookies([
    { name: "aw_session", value: token, url: WEB_URL, httpOnly: true, sameSite: "Lax" },
    { name: "aw_locale", value: "en", url: WEB_URL, sameSite: "Lax" },
  ]);
}

/** A hairdresser in Berlin that speaks German and English. */
export const BERLIN_SALON: NewBusiness = {
  name: "Salon Morgenrot",
  niche_key: "beauty_salon",
  country_code: "DE",
  city: "Berlin",
  languages: ["de", "en"],
  default_language: "de",
};

export interface ConsoleErrors {
  /** Accept console errors matching `pattern` in this test (an expected 4xx, say). */
  allow: (pattern: RegExp) => void;
}

export const test = base.extend<{
  /** Fail on Cyrillic interface text of en/ka pages (support/consoleClean.ts). */
  cyrillicCheck: boolean;
  consoleErrors: ConsoleErrors;
  requestTracking: void;
  account: Account;
  newOwner: Owner;
  owner: Owner;
}>({
  cyrillicCheck: [process.env.E2E_CYRILLIC_CHECK === "1", { option: true }],

  consoleErrors: [
    async ({ page, context, cyrillicCheck }, use) => {
      const record: ConsoleRecord = { errors: [], hydration: [] };
      const allowed: RegExp[] = [];
      watchContext(context, record);
      await use({ allow: (pattern) => allowed.push(pattern) });
      const stray = cyrillicCheck ? await strayCyrillic(page) : [];
      expect(unexpectedErrors(record, allowed), "the page logged errors").toEqual([]);
      expect(stray, "interface text in Cyrillic on an English or Georgian page").toEqual([]);
    },
    { auto: true },
  ],

  requestTracking: [
    async ({ page }, use) => {
      trackRequests(page);
      await use();
    },
    { auto: true },
  ],

  account: async ({ request, context }, use) => {
    const email = uniqueEmail();
    const token = await signInByEmail(request, email);
    await signInContext(context, token);
    await use({ email, token });
  },

  newOwner: async ({ request, account }, use) => {
    const businessId = await createBusiness(request, account.token, BERLIN_SALON);
    await use({ ...account, businessId, businessName: BERLIN_SALON.name });
  },

  owner: async ({ request, newOwner }, use) => {
    await createAssistant(request, newOwner.token, newOwner.businessId);
    await use(newOwner);
  },
});

export { expect };
