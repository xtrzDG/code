/**
 * The bot check (Cloudflare Turnstile) the API may ask for before it sends a
 * login code: a 403 whose reason `challenge_required` names the widget's
 * site key. The page then shows the check and sends the request again with
 * its one-time token.
 */

import type { ApiError } from "@/api/errors";
import type { Theme } from "@/lib/theme";

export const BOT_CHECK_REASON = "challenge_required";
/** Loaded only when the API asks for the check (allowed by the page's CSP). */
export const TURNSTILE_SCRIPT_URL = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
/** The API accepts tokens of this action only. */
export const LOGIN_ACTION = "login";
const SITE_KEY_PATTERN = /^[0-9A-Za-z_-]{1,64}$/;

/** The widget's site key when the API wants a passed bot check first; else null. */
export function findBotCheckSiteKey(error: ApiError): string | null {
  if (error.status !== 403) {
    return null;
  }
  const siteKey = error.reasons.find((reason) => reason.code === BOT_CHECK_REASON)?.details[0];
  return siteKey && SITE_KEY_PATTERN.test(siteKey) ? siteKey : null;
}

/** Turnstile's colours: the cabinet's theme ("system" follows the browser). */
export function turnstileTheme(theme: Theme): "light" | "dark" | "auto" {
  return theme === "system" ? "auto" : theme;
}

/** Turnstile speaks the interface language (ka has no translation: English). */
export function turnstileLanguage(locale: string): string {
  return locale === "ka" ? "en" : locale;
}
