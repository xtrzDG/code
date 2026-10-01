import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { lookupMessage } from "@/i18n/translate";

import { isOpenHandoff, sortHandoffs } from "./handoffs";
import { allLabelKeys, BOOKING_STATUS, HANDOFF_STATUS, HANDOFF_URGENCY, LEAD_STATUS } from "./labels";
import { formatMicroUsd, formatPercent, sharePercent } from "./numbers";
import { afterFirstPageError, appendPage, MAX_PAGE_SIZE, PAGE_SIZE, reloadLimit } from "./paging";

describe("enum labels", () => {
  it("point at texts that exist in the English dictionary", () => {
    const missing = allLabelKeys().filter((key) => typeof lookupMessage(en, key) !== "string");
    expect(missing).toEqual([]);
  });

  it("use alarming tones only where staff must act", () => {
    expect(HANDOFF_URGENCY.critical.tone).toBe("danger");
    expect(HANDOFF_URGENCY.low.tone).toBe("neutral");
    expect(HANDOFF_STATUS.notification_failed.tone).toBe("danger");
    expect(HANDOFF_STATUS.resolved.tone).toBe("success");
    expect(BOOKING_STATUS.pending.tone).toBe("warning");
    expect(BOOKING_STATUS.cancelled.tone).toBe("neutral");
    expect(LEAD_STATUS.won.tone).toBe("success");
  });
});

describe("numbers", () => {
  it("formats model costs with enough digits for fractions of a cent", () => {
    expect(formatMicroUsd(7200, "en")).toBe("$0.0072");
    expect(formatMicroUsd(1_250_000, "en")).toBe("$1.25");
    expect(formatMicroUsd(0, "en")).toBe("$0.00");
  });

  it("computes bar shares safely", () => {
    expect(sharePercent(1, 4)).toBe(25);
    expect(sharePercent(3, 0)).toBe(0);
    expect(sharePercent(5, 4)).toBe(100);
    expect(formatPercent(37.5, "en")).toBe("38%");
  });
});

describe("handoffs", () => {
  const handoff = (id: string, status: "pending" | "notified" | "resolved", urgency: "low" | "normal" | "high" | "critical", createdAt: number, resolvedAt: number | null = null) => ({
    id,
    status,
    urgency,
    created_at: createdAt,
    resolved_at: resolvedAt,
  });

  it("puts open handoffs first, most urgent and longest waiting on top", () => {
    const sorted = sortHandoffs([
      handoff("resolved-old", "resolved", "critical", 1, 5),
      handoff("normal-new", "notified", "normal", 30),
      handoff("critical", "pending", "critical", 40),
      handoff("normal-old", "notified", "normal", 10),
      handoff("resolved-new", "resolved", "low", 2, 50),
    ]);
    expect(sorted.map((item) => item.id)).toEqual(["critical", "normal-old", "normal-new", "resolved-new", "resolved-old"]);
  });

  it("treats every unresolved status as open", () => {
    expect(isOpenHandoff({ status: "notification_failed" })).toBe(true);
    expect(isOpenHandoff({ status: "resolved" })).toBe(false);
  });
});

describe("server paging", () => {
  it("reloads as many items as are shown, within one API page", () => {
    expect(reloadLimit(0)).toBe(PAGE_SIZE);
    expect(reloadLimit(50)).toBe(50);
    expect(reloadLimit(51)).toBe(100);
    expect(reloadLimit(1000)).toBe(MAX_PAGE_SIZE);
  });

  it("appends a page without repeating items that moved", () => {
    const shown = [{ id: "a" }, { id: "b" }];
    expect(appendPage(shown, [{ id: "b" }, { id: "c" }]).map((item) => item.id)).toEqual(["a", "b", "c"]);
    expect(appendPage([], [{ id: "x" }])).toEqual([{ id: "x" }]);
  });
});

describe("afterFirstPageError", () => {
  const shown = { page: { items: [{ id: "lead_6" }], next_cursor: "6" }, items: [{ id: "lead_6" }], nextCursor: "6" };

  it("keeps the list when a reload of the same filters fails", () => {
    expect(afterFirstPageError(shown, true)).toEqual(shown);
  });

  it("drops another filter's list and its cursor, so show more cannot mix the two", () => {
    expect(afterFirstPageError(shown, false)).toEqual({ page: undefined, items: undefined, nextCursor: null });
    expect(afterFirstPageError(null, true)).toEqual({ page: undefined, items: undefined, nextCursor: null });
  });
});
