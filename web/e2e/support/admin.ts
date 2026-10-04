/**
 * Platform admins sign in with two factors: the login code, then a code
 * from their authenticator app. The first sign-in of a run sets the app up
 * (the API's in-memory storage starts empty); its key is kept in the run's
 * artifacts, so later spec files sign in with it. An address gets a login
 * code at most every 30 seconds and each app code works once: both waits
 * happen here.
 */

import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

import { expect, type APIRequestContext } from "@playwright/test";

import { API_URL, ARTIFACTS_DIRECTORY } from "./env";
import { apiLogSize, waitForLoginCode } from "./login-codes";
import { freshTotpCode } from "./totp";

/** The admins' authenticator keys in this run, by e-mail. */
const AUTHENTICATORS_PATH = path.join(ARTIFACTS_DIRECTORY, "authenticators.json");
const LOGIN_CODE_COOLDOWN_MS = 31_000;

export interface Authenticator {
  secret: string;
  lastStep: number | null;
}

function readAuthenticators(): Record<string, Authenticator> {
  try {
    return JSON.parse(readFileSync(AUTHENTICATORS_PATH, "utf8")) as Record<string, Authenticator>;
  } catch {
    return {};
  }
}

/** The app of this admin as the tests know it (null before it is set up in this run). */
export function readAuthenticator(email: string): Authenticator | null {
  return readAuthenticators()[email] ?? null;
}

export function rememberAuthenticator(email: string, authenticator: Authenticator): void {
  writeFileSync(AUTHENTICATORS_PATH, JSON.stringify({ ...readAuthenticators(), [email]: authenticator }));
}

/** A code the app shows now, never one of a step this admin already used. */
export async function nextAuthenticatorCode(email: string): Promise<string> {
  const authenticator = readAuthenticator(email);
  if (!authenticator) {
    throw new Error(`No authenticator is set up for ${email} in this run.`);
  }
  const { code, step } = await freshTotpCode(authenticator.secret, authenticator.lastStep);
  rememberAuthenticator(email, { ...authenticator, lastStep: step });
  return code;
}

/** The login code step; the API answers the second step's challenge. */
async function passLoginCode(request: APIRequestContext, email: string): Promise<Record<string, unknown>> {
  for (let attempt = 0; ; attempt += 1) {
    const since = apiLogSize();
    const start = await request.post(`${API_URL}/v1/auth/otp/start`, { data: { email, locale: "en" } });
    if (start.status() === 429 && attempt === 0) {
      // Another spec asked for a code for this address moments ago.
      await new Promise((resolve) => setTimeout(resolve, LOGIN_CODE_COOLDOWN_MS));
      continue;
    }
    expect(start.status(), await start.text()).toBe(200);
    const challengeId = ((await start.json()) as { challenge_id: string }).challenge_id;
    const code = await waitForLoginCode({ since });
    const verify = await request.post(`${API_URL}/v1/auth/otp/verify`, { data: { challenge_id: challengeId, code } });
    expect(verify.status(), await verify.text()).toBe(200);
    return (await verify.json()) as Record<string, unknown>;
  }
}

/** Signs a platform admin in with both factors (setting the app up the first time); the bearer token. */
export async function signInAsPlatformAdmin(request: APIRequestContext, email: string): Promise<string> {
  const answer = await passLoginCode(request, email);
  expect(answer.mfa_required, "platform admins take the second step").toBe(true);
  const challenge = answer.mfa_challenge as { mfa_challenge_id: string; requires_enrollment: boolean };
  if (challenge.requires_enrollment) {
    const enroll = await request.post(`${API_URL}/v1/auth/mfa/enroll`, {
      data: { mfa_challenge_id: challenge.mfa_challenge_id },
    });
    expect(enroll.status(), await enroll.text()).toBe(200);
    rememberAuthenticator(email, { secret: ((await enroll.json()) as { secret: string }).secret, lastStep: null });
  }
  const verify = await request.post(`${API_URL}/v1/auth/mfa/verify`, {
    data: { mfa_challenge_id: challenge.mfa_challenge_id, code: await nextAuthenticatorCode(email) },
  });
  expect(verify.status(), await verify.text()).toBe(200);
  return ((await verify.json()) as { access_token: string }).access_token;
}
