import { describe, expect, it } from "vitest";

import {
  BodyTooLargeError,
  DEFAULT_BODY_LIMIT_BYTES,
  MENU_IMPORT_BODY_LIMIT_BYTES,
  bodyLimitFor,
  isDeclaredTooLarge,
  limitBodyStream,
  readLimitedText,
} from "./bodyLimits";

function streamOf(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

describe("BFF body limits", () => {
  it("gives the menu import room for a 15 MB file and everything else 256 KB", () => {
    expect(bodyLimitFor("/v1/businesses/biz_1/knowledge/import")).toBe(MENU_IMPORT_BODY_LIMIT_BYTES);
    expect(bodyLimitFor("/v1/businesses/biz_1/knowledge/import/confirm")).toBe(DEFAULT_BODY_LIMIT_BYTES);
    expect(bodyLimitFor("/v1/businesses/biz_1/profile")).toBe(DEFAULT_BODY_LIMIT_BYTES);
  });

  it("refuses a declared length over the limit", () => {
    expect(isDeclaredTooLarge(new Headers({ "content-length": "11" }), 10)).toBe(true);
    expect(isDeclaredTooLarge(new Headers({ "content-length": "10" }), 10)).toBe(false);
    expect(isDeclaredTooLarge(new Headers({ "content-length": "x" }), 10)).toBe(false);
    expect(isDeclaredTooLarge(new Headers(), 10)).toBe(false);
  });

  it("passes a streamed body within the limit and cuts one that grows over it", async () => {
    await expect(new Response(limitBodyStream(streamOf("12345", "67890"), 10)).text()).resolves.toBe("1234567890");
    await expect(new Response(limitBodyStream(streamOf("12345", "678901"), 10)).text()).rejects.toBeInstanceOf(
      BodyTooLargeError,
    );
  });

  it("reads a small body as text and refuses a large one with the limit in KB", async () => {
    const small = new Request("https://cabinet.example/api/auth/verify", { method: "POST", body: "{}" });
    const large = new Request("https://cabinet.example/api/auth/verify", {
      method: "POST",
      body: "x".repeat(DEFAULT_BODY_LIMIT_BYTES + 1),
    });

    await expect(readLimitedText(small, DEFAULT_BODY_LIMIT_BYTES)).resolves.toBe("{}");
    await expect(readLimitedText(large, DEFAULT_BODY_LIMIT_BYTES)).rejects.toThrow(
      "The request body is larger than the 256 KB allowed here.",
    );
    await expect(
      readLimitedText(new Request("https://cabinet.example/", { method: "POST" }), 10),
    ).resolves.toBe("");
  });
});
