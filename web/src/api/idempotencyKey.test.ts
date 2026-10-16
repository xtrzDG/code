import { afterEach, describe, expect, it, vi } from "vitest";

import { IDEMPOTENCY_KEY_HEADER, idempotencyKeys } from "./idempotencyKey";
import { isStepUpPending, settleStepUp, stepUpRetry, subscribeStepUp } from "./stepUp";

type Hook = (options: never) => unknown;
const addKey = idempotencyKeys.onRequest as unknown as Hook;
const keepCopy = stepUpRetry.onRequest as unknown as Hook;
const retryAfterStepUp = stepUpRetry.onResponse as unknown as Hook;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

function post(): Request {
  return new Request("https://cabinet.example/api/backend/v1/assistants", { method: "POST", body: "{}" });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("idempotency keys", () => {
  it("gives every POST its own key", () => {
    const first = addKey({ request: post(), id: "a" } as never) as Request;
    const second = addKey({ request: post(), id: "b" } as never) as Request;

    expect(first.headers.get(IDEMPOTENCY_KEY_HEADER)).toMatch(UUID);
    expect(second.headers.get(IDEMPOTENCY_KEY_HEADER)).toMatch(UUID);
    expect(first.headers.get(IDEMPOTENCY_KEY_HEADER)).not.toBe(second.headers.get(IDEMPOTENCY_KEY_HEADER));
  });

  it("leaves reads, changes and a key the caller chose alone", () => {
    const read = new Request("https://cabinet.example/api/backend/v1/businesses");
    const change = new Request("https://cabinet.example/api/backend/v1/businesses/b", { method: "PATCH", body: "{}" });
    const chosen = post();
    chosen.headers.set(IDEMPOTENCY_KEY_HEADER, "my-key-0000");

    for (const request of [read, change]) {
      expect((addKey({ request, id: "c" } as never) as Request).headers.has(IDEMPOTENCY_KEY_HEADER)).toBe(false);
    }
    expect((addKey({ request: chosen, id: "d" } as never) as Request).headers.get(IDEMPOTENCY_KEY_HEADER)).toBe("my-key-0000");
  });

  it("sends the same key again when the request is retried after a step-up", async () => {
    const fetchMock = vi.fn(async () => new Response("{}", { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    const unsubscribe = subscribeStepUp(() => {
      if (isStepUpPending()) {
        queueMicrotask(() => settleStepUp(true));
      }
    });
    const request = addKey({ request: post(), id: "e" } as never) as Request;
    keepCopy({ request, id: "e" } as never);

    const refused = new Response("{}", {
      status: 401,
      headers: { "www-authenticate": 'Bearer error="insufficient_user_authentication"' },
    });
    await retryAfterStepUp({ request, response: refused, id: "e" } as never);

    const [copy] = fetchMock.mock.calls[0] as unknown as [Request];
    expect(copy.headers.get(IDEMPOTENCY_KEY_HEADER)).toBe(request.headers.get(IDEMPOTENCY_KEY_HEADER));
    unsubscribe();
  });
});
