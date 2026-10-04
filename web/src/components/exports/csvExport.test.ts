import { describe, expect, it } from "vitest";

import { definedQuery, fallbackCsvName, fileNameFromDisposition } from "./csvExport";

describe("fileNameFromDisposition", () => {
  it("reads the quoted name the API sends", () => {
    expect(fileNameFromDisposition('attachment; filename="bookings-2026-10-04.csv"', "x.csv")).toBe(
      "bookings-2026-10-04.csv",
    );
  });

  it("reads an unquoted name and the RFC 5987 form, which wins", () => {
    expect(fileNameFromDisposition("attachment; filename=leads.csv", "x.csv")).toBe("leads.csv");
    expect(
      fileNameFromDisposition("attachment; filename=\"plain.csv\"; filename*=UTF-8''audit-log%202026.csv", "x.csv"),
    ).toBe("audit-log-2026.csv");
  });

  it("falls back on the plain name when the encoded one is broken", () => {
    expect(fileNameFromDisposition("attachment; filename*=UTF-8''%E0%A4%A; filename=\"ok.csv\"", "x.csv")).toBe("ok.csv");
  });

  it("uses the fallback without a header or a name, and keeps paths out", () => {
    expect(fileNameFromDisposition(null, "bookings-2026-10-04.csv")).toBe("bookings-2026-10-04.csv");
    expect(fileNameFromDisposition("attachment", "contacts.csv")).toBe("contacts.csv");
    expect(fileNameFromDisposition('attachment; filename=""', "contacts.csv")).toBe("contacts.csv");
    expect(fileNameFromDisposition('attachment; filename="../../etc/passwd"', "x.csv")).not.toContain("/");
  });
});

describe("fallbackCsvName", () => {
  it("names the table with dashes and the day", () => {
    expect(fallbackCsvName("audit_log", "2026-10-04")).toBe("audit-log-2026-10-04.csv");
    expect(fallbackCsvName("bookings", "2026-10-04")).toBe("bookings-2026-10-04.csv");
  });
});

describe("definedQuery", () => {
  it("drops unset and empty filters", () => {
    expect(definedQuery({ from: "2026-10-01", to: undefined, status: "", order: "earliest_first" })).toEqual({
      from: "2026-10-01",
      order: "earliest_first",
    });
  });
});
