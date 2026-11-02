import { afterEach, describe, expect, it, vi } from "vitest";

import { ROTATE_SESSION_ROUTE, rotateSessionIfRaised } from "./rotateSession";

const TICKET = "q3Jt0bW8yJ1x2Zc4l5mN6oP7rS8tU9vW0xY1zA2bC3d";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("rotateSessionIfRaised: a fresh token once a proof raised the session", () => {
  it("sends the answer's ticket to the cabinet's server only when the level was raised", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await rotateSessionIfRaised({ is_level_raised: false, rotation_ticket: null });
    await rotateSessionIfRaised(undefined);
    await rotateSessionIfRaised({ is_level_raised: true, rotation_ticket: TICKET });

    expect(fetchMock.mock.calls).toEqual([
      [
        ROTATE_SESSION_ROUTE,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ rotation_ticket: TICKET }),
        },
      ],
    ]);
  });

  it("asks nothing without a ticket", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await rotateSessionIfRaised({ is_level_raised: true });
    await rotateSessionIfRaised({ is_level_raised: true, rotation_ticket: null });

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("never throws when the server is out of reach", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("offline"))));

    await expect(rotateSessionIfRaised({ is_level_raised: true, rotation_ticket: TICKET })).resolves.toBeUndefined();
  });
});
