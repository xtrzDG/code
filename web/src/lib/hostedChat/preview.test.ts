import { describe, expect, it } from "vitest";

import {
  PREVIEW_LOOK_MESSAGE,
  PREVIEW_READY_MESSAGE,
  buildChatPreviewPath,
  isPreviewReady,
  isPreviewRequest,
  previewLookMessage,
  readPreviewLook,
} from "./preview";

describe("the live preview's address", () => {
  it("carries the first look so the chat starts in the chosen colour, corner and language", () => {
    const path = buildChatPreviewPath("cafe-batumi", { color: "#8A4B2F", position: "left", language: "ka" });

    expect(path).toBe("/c/cafe-batumi?preview=1&color=%238a4b2f&position=left&lang=ka");
  });

  it("leaves out what is not well formed", () => {
    expect(buildChatPreviewPath("cafe", { color: "red", position: null, language: "<script>" })).toBe("/c/cafe?preview=1");
  });

  it("reads the look back on the hosted page, and nothing without ?preview=1", () => {
    expect(readPreviewLook({ preview: "1", color: "#AABBCC", position: "right", lang: "pt-BR" })).toEqual({
      color: "#aabbcc",
      position: "right",
      language: "pt-BR",
    });
    expect(readPreviewLook({ preview: "1", position: "top", lang: ["ka", "en"] })).toEqual({
      color: null,
      position: null,
      language: null,
    });
    expect(readPreviewLook({ src: "qr" })).toBeNull();
    expect(readPreviewLook({ preview: "true" })).toBeNull();
  });

  it("tells the proxy which requests may be framed by the cabinet", () => {
    expect(isPreviewRequest(new URLSearchParams("preview=1&lang=ka"))).toBe(true);
    expect(isPreviewRequest(new URLSearchParams("src=qr"))).toBe(false);
    expect(isPreviewRequest(new URLSearchParams("preview=0"))).toBe(false);
  });
});

describe("the messages between the Channels page and its preview", () => {
  it("sends only a clean look", () => {
    expect(previewLookMessage({ color: "#123456", position: "left", language: "ru" })).toEqual({
      type: PREVIEW_LOOK_MESSAGE,
      color: "#123456",
      position: "left",
      language: "ru",
    });
  });

  it("listens only to its own frame on its own origin", () => {
    const frame = {} as Window;
    const other = {} as Window;
    const ready = { data: { type: PREVIEW_READY_MESSAGE }, origin: "https://app.example", source: frame };

    expect(isPreviewReady(ready, frame, "https://app.example")).toBe(true);
    expect(isPreviewReady({ ...ready, source: other }, frame, "https://app.example")).toBe(false);
    expect(isPreviewReady({ ...ready, origin: "https://evil.example" }, frame, "https://app.example")).toBe(false);
    expect(isPreviewReady({ ...ready, data: "ready" }, frame, "https://app.example")).toBe(false);
    expect(isPreviewReady(ready, null, "https://app.example")).toBe(false);
  });
});
