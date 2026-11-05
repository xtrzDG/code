import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { buildBackendPath } from "./backend";
import { relayToBackend } from "./relay";
import { answersWithSessionToken } from "./sessionTokenPaths";

const TOKEN_ANSWER = { access_token: "tok_new", expires_at: 1, auth_level: "two_factor" };

/** The API, answering every call with a session token. */
function stubApi(): string[] {
  const called: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      called.push(url);
      return Response.json(TOKEN_ANSWER);
    }),
  );
  return called;
}

/** A same-origin POST to the generic relay at /api/backend/<segments>. */
function relayed(segments: string[]): Promise<Response> {
  const backendPath = buildBackendPath(segments);
  if (backendPath === null) {
    throw new Error(`not relayed: ${segments.join("/")}`);
  }
  const request = new NextRequest(`https://cabinet.example/api/backend${backendPath}`, {
    method: "POST",
    body: JSON.stringify({ rotation_ticket: "t".repeat(43) }),
    headers: { "content-type": "application/json", cookie: "aw_session=tok", "sec-fetch-site": "same-origin" },
  });
  return relayToBackend(request, backendPath, { useSession: true });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("answersWithSessionToken", () => {
  it("names the sign-in steps and the rotation, however the path is spelt", () => {
    for (const path of [
      "/v1/auth/otp/verify",
      "/v1/auth/mfa/verify",
      "/v1/auth/mfa/passkey/verify",
      "/v1/auth/mfa/passkey/enroll/finish",
      "/v1/auth/session/rotate",
      "/v1/auth/session%2Frotate",
      "/v1/auth/session/rotate%2F",
      "/v1/auth//session/rotate",
      "/v1/auth/session/rotate?x=1",
    ]) {
      expect(answersWithSessionToken(path), path).toBe(true);
    }
  });

  it("leaves every other path alone", () => {
    for (const path of [
      "/v1/auth/otp/start",
      "/v1/auth/step-up/verify",
      "/v1/auth/step-up/passkey/verify",
      "/v1/me/mfa/totp/confirm",
      "/v1/auth/session/rotate-later",
      "/v1/auth/session%252Frotate",
    ]) {
      expect(answersWithSessionToken(path), path).toBe(false);
    }
  });
});

describe("the generic relay and session tokens", () => {
  it("never hands the browser an answer that carries a session token", async () => {
    const called = stubApi();

    for (const segments of [
      ["v1", "auth", "session", "rotate"],
      ["v1", "auth", "session/rotate"],
      ["v1", "auth", "otp", "verify"],
      ["v1", "auth", "mfa", "passkey", "enroll", "finish"],
    ]) {
      const response = await relayed(segments);

      expect(response.status, segments.join("/")).toBe(404);
      expect(JSON.stringify(await response.json())).not.toContain("tok_new");
    }
    expect(called).toEqual([]);
  });

  it("still relays the step-up answer whose ticket the cabinet's own route uses", async () => {
    const called = stubApi();

    const response = await relayed(["v1", "auth", "step-up", "verify"]);

    expect(response.status).toBe(200);
    expect(called).toHaveLength(1);
  });
});
