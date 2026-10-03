/**
 * The demo restaurant (SEED_DEMO_DATA): live, with its website chat on, so
 * a visitor's message through the real widget API reaches its assistant.
 * The suite's API has no model key, so the assistant passes every
 * conversation to a person: a handoff, its live event and the team's
 * notifications, as in production.
 *
 * The demo owner's address may ask for a login code every 30 seconds, and
 * several spec files sign in as them: one sign-in per worker, shared here,
 * waiting out the cooldown when a new worker (a retry) asks too early.
 */

import { expect, type APIRequestContext } from "@playwright/test";

import { uniqueSuffix } from "./api";
import { API_URL } from "./env";
import { apiLogSize, waitForLoginCode } from "./login-codes";

export const DEMO_OWNER_EMAIL = "demo@example.com";
export const DEMO_RESTAURANT = "Mtsvane Ezo";

/** An address may ask for a login code every 30 seconds. */
const LOGIN_CODE_COOLDOWN_MS = 31_000;

export interface DemoOwner {
  token: string;
  businessId: string;
}

let demoOwner: Promise<DemoOwner> | undefined;

/** The demo owner, signed in once per worker, with the demo restaurant's id. */
export function signInAsDemoOwner(request: APIRequestContext): Promise<DemoOwner> {
  demoOwner ??= signInOnce(request).catch((error: unknown) => {
    demoOwner = undefined;
    throw error;
  });
  return demoOwner;
}

async function startSignIn(request: APIRequestContext, email: string): Promise<{ challengeId: string; since: number }> {
  for (let attempt = 0; ; attempt += 1) {
    const since = apiLogSize();
    const start = await request.post(`${API_URL}/v1/auth/otp/start`, { data: { email, locale: "en" } });
    if (start.status() === 429 && attempt === 0) {
      // Another worker asked for a code for this address moments ago.
      await new Promise((resolve) => setTimeout(resolve, LOGIN_CODE_COOLDOWN_MS));
      continue;
    }
    expect(start.status(), await start.text()).toBe(200);
    return { challengeId: ((await start.json()) as { challenge_id: string }).challenge_id, since };
  }
}

async function signInOnce(request: APIRequestContext): Promise<DemoOwner> {
  const { challengeId, since } = await startSignIn(request, DEMO_OWNER_EMAIL);
  const code = await waitForLoginCode({ since });
  const verify = await request.post(`${API_URL}/v1/auth/otp/verify`, { data: { challenge_id: challengeId, code } });
  expect(verify.status(), await verify.text()).toBe(200);
  const token = ((await verify.json()) as { access_token: string }).access_token;

  const response = await request.get(`${API_URL}/v1/businesses`, { headers: { authorization: `Bearer ${token}` } });
  expect(response.ok(), await response.text()).toBe(true);
  const businesses = (await response.json()) as { id: string; name: string }[];
  const restaurant = businesses.find((business) => business.name === DEMO_RESTAURANT);
  expect(restaurant, "the demo restaurant is seeded").toBeDefined();
  return { token, businessId: restaurant!.id };
}

export interface Visitor {
  name: string;
  /** The website chat's session (the X-Widget-Session-Key of its polls). */
  sessionKey: string;
}

/**
 * A visitor writes in the website chat; the assistant hands the chat to a
 * person. The API accepts the message at once (202) and its worker answers,
 * so the handoff is read from the widget's poll.
 */
export async function visitorAsksForPerson(request: APIRequestContext, businessId: string, name: string): Promise<Visitor> {
  const sessionKey = `e2e_${uniqueSuffix()}_visitor`;
  const url = `${API_URL}/v1/widget/${businessId}/messages`;
  const response = await request.post(url, {
    data: { session_key: sessionKey, text: "Hello, can I talk to a manager?", contact_name: name },
  });
  expect(response.status(), await response.text()).toBe(202);
  await expect
    .poll(
      async () => {
        const poll = await request.get(url, { headers: { "X-Widget-Session-Key": sessionKey } });
        return poll.ok() && ((await poll.json()) as { is_handed_off: boolean }).is_handed_off;
      },
      { message: "the worker handed the chat to a person", timeout: 15_000 },
    )
    .toBe(true);
  return { name, sessionKey };
}

/**
 * What the visitor's chat shows besides their own messages (the widget's
 * poll): the texts of the assistant's and the team's messages after the
 * visitor's latest one. A first poll gives only that position.
 */
export async function visitorTranscript(request: APIRequestContext, businessId: string, visitor: Visitor): Promise<string[]> {
  const poll = async (after?: string) => {
    const response = await request.get(`${API_URL}/v1/widget/${businessId}/messages`, {
      headers: { "X-Widget-Session-Key": visitor.sessionKey },
      params: after ? { after } : {},
    });
    expect(response.ok(), await response.text()).toBe(true);
    return (await response.json()) as { cursor?: string | null; items: { text: string }[] };
  };
  const { cursor } = await poll();
  expect(cursor, "the visitor has a conversation").toBeTruthy();
  return (await poll(cursor!)).items.map((item) => item.text);
}
