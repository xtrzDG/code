import { beforeEach, describe, expect, it, vi } from "vitest";

import { getServerApi } from "@/server/api";
import { failure, ok } from "@/test/fakeApi";

import type { LoginOptions } from "./loginOptions";
import { loadOpeningLoginMethod } from "./openingMethod";

vi.mock("@/server/api", () => ({ getServerApi: vi.fn() }));

const options: LoginOptions = {
  configured_channels: ["sms", "email"],
  is_email_login_available: true,
  is_phone_login_available: true,
  is_sign_up_restricted: false,
  phone_channels: ["sms"],
};

const emailOnly: LoginOptions = {
  ...options,
  configured_channels: ["email"],
  is_phone_login_available: false,
  phone_channels: [],
};

interface OptionsRequest {
  params?: { query?: Record<string, string> };
  signal?: AbortSignal;
}

/** The server's API client answers the one call the page makes. */
function serverApiAnswers(answer: () => Promise<unknown>) {
  const get = vi.fn<(path: string, init?: OptionsRequest) => Promise<unknown>>(() => answer());
  vi.mocked(getServerApi).mockResolvedValue({ GET: get } as never);
  return get;
}

describe("the form of the sign-in page's first HTML", () => {
  beforeEach(() => {
    vi.mocked(getServerApi).mockReset();
  });

  it("is e-mail where codes go by e-mail only", async () => {
    const get = serverApiAnswers(() => ok(emailOnly));

    expect(await loadOpeningLoginMethod()).toBe("email");
    // No country: the configured channels are the same for all of them.
    expect(get).toHaveBeenCalledTimes(1);
    expect(get.mock.calls[0]?.[0]).toBe("/v1/auth/login-options");
    expect(get.mock.calls[0]?.[1]?.params).toEqual({ query: {} });
  });

  it("is phone where a phone channel delivers codes", async () => {
    serverApiAnswers(() => ok(options));

    expect(await loadOpeningLoginMethod()).toBe("phone");
  });

  it("is phone when the API refuses or cannot be reached", async () => {
    serverApiAnswers(() => failure(503, { code: "service_unavailable" }));
    expect(await loadOpeningLoginMethod()).toBe("phone");

    serverApiAnswers(() => Promise.reject(new TypeError("fetch failed")));
    expect(await loadOpeningLoginMethod()).toBe("phone");
  });

  it("is phone when the server has no API address", async () => {
    vi.mocked(getServerApi).mockRejectedValue(new Error("BACKEND_URL is not set"));

    expect(await loadOpeningLoginMethod()).toBe("phone");
  });

  it("gives the API two seconds, then opens on phone", async () => {
    const get = serverApiAnswers(() => ok(emailOnly));
    const timeout = vi.spyOn(AbortSignal, "timeout");

    await loadOpeningLoginMethod();

    expect(timeout).toHaveBeenCalledWith(2_000);
    expect(get.mock.calls[0]?.[1]?.signal).toBe(timeout.mock.results[0]?.value);
    timeout.mockRestore();

    // What an aborted request does: it rejects, and the page opens on phone.
    serverApiAnswers(() => Promise.reject(new DOMException("The operation timed out.", "TimeoutError")));
    expect(await loadOpeningLoginMethod()).toBe("phone");
  });
});
