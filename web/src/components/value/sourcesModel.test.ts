import { describe, expect, it } from "vitest";

import { conversationShare, hasTaggedSources, sourceNameOf, sourceTotals, type CustomerSourceRow } from "./sourcesModel";

function row(overrides: Partial<CustomerSourceRow>): CustomerSourceRow {
  return {
    kind: "tagged",
    acquisition_source: "table",
    channels: ["whatsapp"],
    source_count: 1,
    conversation_count: 0,
    booking_count: 0,
    request_count: 0,
    estimated_value_minor: null,
    ...overrides,
  };
}

describe("sourceNameOf", () => {
  it("reads the share card's places by their names", () => {
    expect(sourceNameOf("table")).toEqual({ kind: "place", key: "share.sources.table" });
    expect(sourceNameOf("google")).toEqual({ kind: "place", key: "share.sources.google" });
  });

  it("reads the line called, ads and other tags", () => {
    expect(sourceNameOf("tel-995322190020")).toEqual({ kind: "phone", number: "+995322190020" });
    expect(sourceNameOf("ad-120208")).toEqual({ kind: "ad", id: "120208" });
    expect(sourceNameOf("ad")).toEqual({ kind: "ad", id: null });
    expect(sourceNameOf("qr-menu")).toEqual({ kind: "tag", tag: "qr-menu" });
    expect(sourceNameOf("adverts")).toEqual({ kind: "tag", tag: "adverts" });
  });
});

describe("sourceTotals", () => {
  it("sums the rows, the value only over rows that have one", () => {
    const rows = [
      row({ conversation_count: 6, booking_count: 2, estimated_value_minor: 18_000 }),
      row({ kind: "untagged", acquisition_source: null, conversation_count: 4, request_count: 1 }),
    ];

    const totals = sourceTotals(rows);

    expect(totals).toEqual({ conversations: 10, bookings: 2, requests: 1, valueMinor: 18_000 });
    expect(conversationShare(rows[0]!, totals)).toBe(60);
  });

  it("has no value when nothing prices the rows, and no share of nothing", () => {
    const totals = sourceTotals([row({})]);

    expect(totals.valueMinor).toBeNull();
    expect(conversationShare(row({}), totals)).toBe(0);
  });
});

describe("hasTaggedSources", () => {
  it("tells tables split only by channel", () => {
    expect(hasTaggedSources([row({ kind: "untagged", acquisition_source: null })])).toBe(false);
    expect(hasTaggedSources([row({}), row({ kind: "other", acquisition_source: null })])).toBe(true);
  });
});
