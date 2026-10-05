import { describe, expect, it } from "vitest";

import {
  DEMO_MESSAGE_MAX_LENGTH,
  cleanDemoMessage,
  demoFailure,
  messagesLeftNotice,
  newSessionKey,
  replyOutcomes,
  startersFor,
} from "./demoChat";

describe("demo chat", () => {
  it("makes conversation keys the API accepts", () => {
    const key = newSessionKey();
    expect(key).toMatch(/^[A-Za-z0-9_-]{16,64}$/);
    expect(newSessionKey()).not.toBe(key);
    expect(newSessionKey((bytes) => bytes.fill(255))).toBe("_".repeat(22));
  });

  it("offers starters in the visitor's language, else in the demo's own", () => {
    const card = {
      default_language: "ka",
      starters: [
        { language: "ka", text: "გაქვთ მაგიდა?" },
        { language: "ru", text: "Есть столик?" },
        { language: "ru", text: "Какое меню?" },
        { language: "ru", text: "Где вы?" },
        { language: "ru", text: "Парковка?" },
      ],
    };

    expect(startersFor(card, "ru")).toEqual(["Есть столик?", "Какое меню?", "Где вы?"]);
    expect(startersFor(card, "en")).toEqual(["გაქვთ მაგიდა?"]);
    expect(startersFor({ default_language: "en" }, "en")).toEqual([]);
  });

  it("names what a sandbox turn did", () => {
    expect(replyOutcomes({ is_booking_made: true, is_request_made: true, is_handoff_made: true })).toEqual([
      "booking",
      "request",
      "handoff",
    ]);
    expect(replyOutcomes({})).toEqual([]);
  });

  it("sends only real messages within the limit", () => {
    expect(cleanDemoMessage("  Hello  ")).toBe("Hello");
    expect(cleanDemoMessage("   ")).toBeNull();
    expect(cleanDemoMessage("x".repeat(DEMO_MESSAGE_MAX_LENGTH + 1))).toBeNull();
  });

  it("explains a failed send by its code", () => {
    expect(demoFailure("rate_limited")).toBe("limit");
    expect(demoFailure("not_found")).toBe("unavailable");
    expect(demoFailure("network_error")).toBe("offline");
    expect(demoFailure("backend_unavailable")).toBe("offline");
    expect(demoFailure("internal_error")).toBe("failed");
    expect(demoFailure(null)).toBe("failed");
  });

  it("counts down only the last few messages", () => {
    expect(messagesLeftNotice(12)).toBeNull();
    expect(messagesLeftNotice(5)).toBe(5);
    expect(messagesLeftNotice(-1)).toBe(0);
  });
});
