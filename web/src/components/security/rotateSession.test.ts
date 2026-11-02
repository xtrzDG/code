import { afterEach, describe, expect, it, vi } from "vitest";

import { ROTATE_SESSION_ROUTE, rotateSessionIfRaised } from "./rotateSession";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("rotateSessionIfRaised: a fresh token once a step-up raised the session", () => {
  it("asks the cabinet's server for a new token only when the level was raised", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await rotateSessionIfRaised({ is_level_raised: false });
    await rotateSessionIfRaised(undefined);
    await rotateSessionIfRaised({ is_level_raised: true });

    expect(fetchMock.mock.calls).toEqual([[ROTATE_SESSION_ROUTE, { method: "POST" }]]);
  });

  it("never throws when the server is out of reach", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("offline"))));

    await expect(rotateSessionIfRaised({ is_level_raised: true })).resolves.toBeUndefined();
  });
});
