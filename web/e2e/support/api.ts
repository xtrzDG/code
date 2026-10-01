/** Direct calls to the Python API for test setup (what the UI does is tested elsewhere). */

import { expect, type APIRequestContext } from "@playwright/test";

import { API_URL } from "./env";
import { apiLogSize, waitForLoginCode } from "./login-codes";

/** A short random suffix that keeps test data apart between runs and tests. */
export function uniqueSuffix(): string {
  return crypto.randomUUID().replaceAll("-", "").slice(0, 10);
}

/** A fresh e-mail address on its own domain, so its logged code is easy to find. */
export function uniqueEmail(): string {
  return `owner@e2e-${uniqueSuffix()}.example.com`;
}

/** Signs in (or up) by e-mail through the API and returns the bearer token. */
export async function signInByEmail(request: APIRequestContext, email: string): Promise<string> {
  const since = apiLogSize();
  const start = await request.post(`${API_URL}/v1/auth/otp/start`, { data: { email, locale: "en" } });
  expect(start.status(), await start.text()).toBe(200);
  const { challenge_id: challengeId } = (await start.json()) as { challenge_id: string };
  const code = await waitForLoginCode({ since, destinationSuffix: email.slice(email.indexOf("@")) });
  const verify = await request.post(`${API_URL}/v1/auth/otp/verify`, { data: { challenge_id: challengeId, code } });
  expect(verify.status(), await verify.text()).toBe(200);
  return ((await verify.json()) as { access_token: string }).access_token;
}

export interface NewBusiness {
  name: string;
  niche_key: string;
  country_code: string;
  city?: string;
  languages: string[];
  default_language?: string;
}

/** Creates a business for the signed-in user and returns its id. */
export async function createBusiness(request: APIRequestContext, token: string, business: NewBusiness): Promise<string> {
  const response = await request.post(`${API_URL}/v1/businesses`, {
    data: business,
    headers: { authorization: `Bearer ${token}` },
  });
  expect(response.status(), await response.text()).toBe(201);
  return ((await response.json()) as { id: string }).id;
}
