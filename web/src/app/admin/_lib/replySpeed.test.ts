import { describe, expect, it } from "vitest";

import { channelRows, formatWait, isSlowPercentile, SLOW_REPLY_P95_MS } from "./replySpeed";

describe("formatWait", () => {
  it("shows short waits in seconds with one decimal", () => {
    expect(formatWait(800, "en")).toEqual({ value: "0.8", unit: "seconds" });
    expect(formatWait(2_450, "en")).toEqual({ value: "2.5", unit: "seconds" });
  });

  it("drops the decimal from ten seconds on", () => {
    expect(formatWait(12_400, "en")).toEqual({ value: "12", unit: "seconds" });
    expect(formatWait(95_000, "en")).toEqual({ value: "95", unit: "seconds" });
  });

  it("switches to whole minutes from two minutes on", () => {
    expect(formatWait(180_000, "en")).toEqual({ value: "3", unit: "minutes" });
  });

  it("uses the reader's decimal separator", () => {
    expect(formatWait(2_450, "ru").value).toBe("2,5");
  });
});

describe("isSlowPercentile", () => {
  it("flags only a 95th percentile above 15 s", () => {
    expect(isSlowPercentile(SLOW_REPLY_P95_MS)).toBe(false);
    expect(isSlowPercentile(SLOW_REPLY_P95_MS + 1)).toBe(true);
    expect(isSlowPercentile(null)).toBe(false);
    expect(isSlowPercentile(undefined)).toBe(false);
  });
});

describe("channelRows", () => {
  it("lists the busiest channel first", () => {
    const rows = channelRows({
      reply_count: 30,
      channels: [
        { channel: "telegram", reply_count: 5, p50_ms: 1_000, p95_ms: 2_000 },
        { channel: "whatsapp", reply_count: 25, p50_ms: 2_000, p95_ms: 9_000 },
      ],
    });
    expect(rows.map((row) => row.channel)).toEqual(["whatsapp", "telegram"]);
  });

  it("is empty without a summary", () => {
    expect(channelRows(undefined)).toEqual([]);
  });
});
