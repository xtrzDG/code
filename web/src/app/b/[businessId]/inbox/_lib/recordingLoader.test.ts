import { describe, expect, it } from "vitest";

import { loadRecording } from "./recordingLoader";

const URL_OF_RECORDING = "/api/backend/v1/businesses/b1/calls/c1/recording";

function fakeFetch(answer: () => Promise<Response>) {
  const calls: { url: string; init: RequestInit | undefined }[] = [];
  const fetchImpl = ((input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ url: String(input), init });
    return answer();
  }) as typeof fetch;
  return { calls, fetchImpl };
}

describe("loading a call recording", () => {
  it("downloads the audio once, with the session cookie", async () => {
    const audio = new Uint8Array([73, 68, 51, 4, 0, 1, 2, 3]);
    const { calls, fetchImpl } = fakeFetch(async () => new Response(audio, { headers: { "content-type": "audio/mpeg" } }));

    const load = await loadRecording(URL_OF_RECORDING, fetchImpl);

    expect(load.ok).toBe(true);
    expect(load.ok && load.blob.size).toBe(audio.length);
    expect(load.ok && load.blob.type).toBe("audio/mpeg");
    expect(calls).toEqual([{ url: URL_OF_RECORDING, init: { credentials: "same-origin", cache: "no-store" } }]);
  });

  it("tells an expired session, a missing recording and an outage apart", async () => {
    const answer = (status: number) =>
      fakeFetch(async () => new Response(JSON.stringify({ error: "x", message: "y" }), { status })).fetchImpl;

    expect(await loadRecording(URL_OF_RECORDING, answer(401))).toEqual({ ok: false, failure: "expired" });
    expect(await loadRecording(URL_OF_RECORDING, answer(404))).toEqual({ ok: false, failure: "missing" });
    expect(await loadRecording(URL_OF_RECORDING, answer(502))).toEqual({ ok: false, failure: "unavailable" });
    const offline = fakeFetch(() => Promise.reject(new TypeError("Failed to fetch"))).fetchImpl;
    expect(await loadRecording(URL_OF_RECORDING, offline)).toEqual({ ok: false, failure: "unavailable" });
  });
});
