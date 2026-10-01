/**
 * The `test` of the suite: Playwright's, plus
 *
 *   - a check that the page logged no console errors and threw nothing
 *     (every test, automatically; `consoleErrors.allow(/…/)` accepts an
 *     error the test provokes on purpose);
 *   - `account`: a new account created through the API, with the browser
 *     context signed in as it (interface in English);
 *   - `owner`: the same plus one business (a hair salon in Berlin).
 */

import { test as base, expect, type BrowserContext } from "@playwright/test";

import { createBusiness, signInByEmail, uniqueEmail, type NewBusiness } from "./api";
import { WEB_URL } from "./env";

export interface Account {
  email: string;
  token: string;
}

export interface Owner extends Account {
  businessId: string;
  businessName: string;
}

/** The cabinet's session and language cookies, as the sign-in route sets them. */
async function signInContext(context: BrowserContext, token: string): Promise<void> {
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

export const test = base.extend<{ consoleErrors: ConsoleErrors; account: Account; owner: Owner }>({
  consoleErrors: [
    async ({ page }, use) => {
      const errors: string[] = [];
      const allowed: RegExp[] = [];
      page.on("console", (message) => {
        if (message.type() === "error") {
          errors.push(`console.error: ${message.text()} (${message.location().url})`);
        }
      });
      page.on("pageerror", (error) => errors.push(`uncaught: ${error.message}`));
      await use({ allow: (pattern) => allowed.push(pattern) });
      const unexpected = errors.filter((error) => !allowed.some((pattern) => pattern.test(error)));
      expect(unexpected, "the page logged errors").toEqual([]);
    },
    { auto: true },
  ],

  account: async ({ request, context }, use) => {
    const email = uniqueEmail();
    const token = await signInByEmail(request, email);
    await signInContext(context, token);
    await use({ email, token });
  },

  owner: async ({ request, account }, use) => {
    const businessId = await createBusiness(request, account.token, BERLIN_SALON);
    await use({ ...account, businessId, businessName: BERLIN_SALON.name });
  },
});

export { expect };
