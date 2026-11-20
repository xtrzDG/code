/**
 * Test helpers of the sign-in screen: the sign-in options of three kinds of
 * deployment, and the API answering them at once or when the test says so
 * (the test file replaces `@/api/client` first, see src/test/fakeApi.ts).
 */

import { answerGet, ok, pending } from "@/test/fakeApi";

import type { LoginOptions } from "./loginOptions";

/** Codes go to phones (SMS) and by e-mail. */
export const everyMethod: LoginOptions = {
  configured_channels: ["email", "sms"],
  is_email_login_available: true,
  is_phone_login_available: true,
  is_sign_up_restricted: false,
  phone_channels: ["sms"],
  terms_version: "2026-09-01",
  privacy_version: "2026-09-01",
};

/** Codes go by e-mail only: no phone channel has a provider, in any country. */
export const emailOnly: LoginOptions = {
  ...everyMethod,
  configured_channels: ["email"],
  is_phone_login_available: false,
  phone_channels: [],
};

/** Codes go to phones only: no e-mail provider is set up. */
export const phoneOnly: LoginOptions = {
  ...everyMethod,
  configured_channels: ["sms"],
  is_email_login_available: false,
};

/** Nothing delivers a code: sign-in is down. */
export const nothingDelivers: LoginOptions = {
  ...everyMethod,
  configured_channels: [],
  is_email_login_available: false,
  is_phone_login_available: false,
  phone_channels: [],
};

function answerSignInCalls(options: () => Promise<unknown>): void {
  answerGet((path) => {
    if (path === "/v1/auth/login-options") {
      return options();
    }
    return path === "/v1/catalog/countries" ? ok({ countries: [] }) : pending();
  });
}

/** The API answers the screen's calls at once. */
export function signInOptions(options: LoginOptions = everyMethod): void {
  answerSignInCalls(() => ok(options));
}

/** The options answer when the test says so: until then the screen knows only its opening method. */
export function signInOptionsLater(options: LoginOptions): () => void {
  let answer: () => void = () => undefined;
  const answered = new Promise<void>((resolve) => {
    answer = resolve;
  });
  answerSignInCalls(() => answered.then(() => ok(options)));
  return answer;
}
