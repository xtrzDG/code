import { afterEach, describe, expect, it, vi } from "vitest";

import { isStepUpPending, requestStepUp, settleStepUp, stepUpRetry, subscribeStepUp } from "./stepUp";

type Hook = (options: never) => unknown;
const onRequest = stepUpRetry.onRequest as unknown as Hook;
const onResponse = stepUpRetry.onResponse as unknown as Hook;
const onError = stepUpRetry.onError as unknown as Hook;

const CHALLENGE = { "www-authenticate": 'Bearer error="insufficient_user_authentication", max_age=600' };

function refused(): Response {
  return new Response(JSON.stringify({ error: "authentication_required" }), { status: 401, headers: CHALLENGE });
}

/** A dialog on the page that answers every opening with `confirmed`. */
function dialogAnswering(confirmed: boolean): () => void {
  return subscribeStepUp(() => {
    if (isStepUpPending()) {
      queueMicrotask(() => settleStepUp(confirmed));
    }
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the step-up broker", () => {
  it("refuses at once when no dialog is on the page", async () => {
    await expect(requestStepUp()).resolves.toBe(false);
    expect(isStepUpPending()).toBe(false);
  });

  it("opens one dialog for every request refused meanwhile", async () => {
    const opened = vi.fn();
    const unsubscribe = subscribeStepUp(opened);

    const first = requestStepUp();
    const second = requestStepUp();
    expect(isStepUpPending()).toBe(true);
    settleStepUp(true);

    await expect(first).resolves.toBe(true);
    await expect(second).resolves.toBe(true);
    expect(isStepUpPending()).toBe(false);
    // Opened once, closed once.
    expect(opened).toHaveBeenCalledTimes(2);
    unsubscribe();
  });
});

describe("the retry middleware", () => {
  it("sends the request again once the person confirms", async () => {
    const retried = new Response("{}", { status: 201 });
    const fetchMock = vi.fn(async () => retried);
    vi.stubGlobal("fetch", fetchMock);
    const unsubscribe = dialogAnswering(true);
    const request = new Request("https://cabinet.example/api/backend/v1/x", { method: "POST", body: '{"a":1}' });

    onRequest({ request, id: "r1" } as never);
    const answer = await onResponse({ request, response: refused(), id: "r1" } as never);

    expect(answer).toBe(retried);
    const [copy] = fetchMock.mock.calls[0] as unknown as [Request];
    expect(copy.method).toBe("POST");
    expect(await copy.text()).toBe('{"a":1}');
    unsubscribe();
  });

  it("leaves the refusal when the person cancels", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const unsubscribe = dialogAnswering(false);
    const request = new Request("https://cabinet.example/api/backend/v1/x", { method: "DELETE" });

    onRequest({ request, id: "r2" } as never);
    const answer = await onResponse({ request, response: refused(), id: "r2" } as never);

    expect(answer).toBeUndefined();
    expect(fetchMock).not.toHaveBeenCalled();
    unsubscribe();
  });

  it("lets every other answer through untouched", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const request = new Request("https://cabinet.example/api/backend/v1/x");

    onRequest({ request, id: "r3" } as never);
    const ended = await onResponse({ request, response: new Response(null, { status: 401 }), id: "r3" } as never);
    onRequest({ request, id: "r4" } as never);
    onError({ request, error: new Error("offline"), id: "r4" } as never);
    const unknown = await onResponse({ request, response: refused(), id: "r4" } as never);

    expect(ended).toBeUndefined();
    expect(unknown).toBeUndefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
