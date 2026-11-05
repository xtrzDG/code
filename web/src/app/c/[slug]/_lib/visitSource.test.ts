import { describe, expect, it } from "vitest";

import { normalizeVisitSource, visitSourceOf } from "./visitSource";

describe("normalizeVisitSource", () => {
  it("reads tags as the API records them", () => {
    expect(normalizeVisitSource("table")).toBe("table");
    expect(normalizeVisitSource("  QR Tables!! ")).toBe("qr-tables");
    expect(normalizeVisitSource("--flyer__")).toBe("flyer");
    expect(normalizeVisitSource("a".repeat(40))).toBe("a".repeat(32));
  });

  it("has no source when nothing of the tag is left", () => {
    expect(normalizeVisitSource("")).toBeNull();
    expect(normalizeVisitSource("  ")).toBeNull();
    expect(normalizeVisitSource("ქართ")).toBeNull();
    expect(normalizeVisitSource(undefined)).toBeNull();
  });
});

describe("visitSourceOf", () => {
  it("takes src, else utm_source, the first of repeated ones", () => {
    expect(visitSourceOf({ src: "window", utm_source: "google" })).toBe("window");
    expect(visitSourceOf({ utm_source: "Google" })).toBe("google");
    expect(visitSourceOf({ src: ["flyer", "table"] })).toBe("flyer");
    expect(visitSourceOf({ src: "!!", utm_source: "instagram" })).toBe("instagram");
    expect(visitSourceOf({})).toBeNull();
  });
});
