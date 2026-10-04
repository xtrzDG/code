import { describe, expect, it } from "vitest";

import { emptyKnowledgeForm, knowledgeCreateBody, knowledgeFormFromItem, knowledgePatchBody, validateKnowledgeForm, type KnowledgeForm } from "./form";
import { MAX_BUFFER_MINUTES } from "./offerFields";
import {
  MAX_SEASONS,
  daysInMonth,
  emptySeasonRow,
  monthNames,
  overlappingSeasons,
  sameRates,
  seasonDay,
  seasonDays,
  seasonLabel,
  seasonRowsFromRates,
  validateSeasonRows,
  type SeasonRow,
} from "./seasons";

const row = (patch: Partial<SeasonRow> = {}): SeasonRow => ({ ...emptySeasonRow(), rate: "150", ...patch });

describe("season days", () => {
  it("builds MM-DD only for days the month has (29 February counts)", () => {
    expect(seasonDay("6", "1")).toBe("06-01");
    expect(seasonDay("2", "29")).toBe("02-29");
    expect(seasonDay("2", "30")).toBeNull();
    expect(seasonDay("4", "31")).toBeNull();
    expect(seasonDay("13", "1")).toBeNull();
    expect(seasonDay("x", "1")).toBeNull();
    expect(daysInMonth(2)).toBe(29);
    expect(daysInMonth(99)).toBe(31);
  });

  it("lists the days of a season, over New Year too", () => {
    expect(seasonDays("06-01", "06-03")).toEqual(["06-01", "06-02", "06-03"]);
    expect(seasonDays("12-31", "01-01")).toEqual(["01-01", "12-31"]);
    expect(seasonDays("01-01", "12-31")).toHaveLength(366);
  });

  it("finds the first two seasons that share a day", () => {
    expect(overlappingSeasons([{ starts_on: "06-01", ends_on: "08-31" }, { starts_on: "09-01", ends_on: "05-31" }])).toBeNull();
    expect(
      overlappingSeasons([
        { starts_on: "06-01", ends_on: "08-31" },
        { starts_on: "12-20", ends_on: "01-10" },
        { starts_on: "01-05", ends_on: "01-06" },
      ]),
    ).toEqual([1, 2]);
  });
});

describe("season rows", () => {
  it("round-trips stored rates in major units", () => {
    const rows = seasonRowsFromRates([{ starts_on: "06-15", ends_on: "08-31", nightly_rate_minor: 15050, name: "Summer" }], "EUR");
    expect(rows[0]).toMatchObject({ name: "Summer", startMonth: "6", startDay: "15", endMonth: "8", endDay: "31", rate: "150.5" });
    const result = validateSeasonRows(rows, "EUR");
    expect(result).toEqual({ ok: true, rates: [{ starts_on: "06-15", ends_on: "08-31", nightly_rate_minor: 15050, name: "Summer" }] });
    expect(seasonRowsFromRates([{ starts_on: "01-01", ends_on: "01-02", nightly_rate_minor: 9000 }], "JPY")[0]?.name).toBe("");
  });

  it("reports impossible days, missing or bad rates, long names and overlaps", () => {
    const result = validateSeasonRows(
      [row({ startMonth: "2", startDay: "30" }), row({ rate: "" }), row({ rate: "abc", name: "x".repeat(101) })],
      "EUR",
    );
    expect(result).toEqual({
      ok: false,
      overlap: null,
      rows: [{ dates: "knowledge.offer.errors.seasonDate" }, { rate: "validation.required" }, { rate: "validation.number", name: "validation.tooLong" }],
    });
    expect(validateSeasonRows([row(), row({ startMonth: "8", startDay: "1", endMonth: "9", endDay: "30" })], "EUR")).toEqual({
      ok: false,
      overlap: [0, 1],
      rows: [{}, {}],
    });
  });

  it("compares rates and names months and seasons in the UI language", () => {
    const summer = { starts_on: "06-01", ends_on: "08-31", nightly_rate_minor: 100, name: null };
    expect(sameRates([summer], [{ ...summer }])).toBe(true);
    expect(sameRates([summer], [{ ...summer, nightly_rate_minor: 101 }])).toBe(false);
    expect(monthNames("en")[0]).toBe("January");
    expect(monthNames("ru")).toHaveLength(12);
    expect(seasonLabel(summer, "en")).toBe("Jun 1 – Aug 31");
    expect(emptySeasonRow().key).not.toBe(emptySeasonRow().key);
  });
});

describe("the bookable part of the item form", () => {
  const service = (patch: Partial<KnowledgeForm> = {}): KnowledgeForm => ({
    ...emptyKnowledgeForm("service"),
    title: "Haircut",
    price: "35",
    duration: "45",
    ...patch,
  });

  it("validates the break and the seasons", () => {
    expect(validateKnowledgeForm(service({ buffer: "10" }), "EUR")).toEqual({});
    expect(validateKnowledgeForm(service({ buffer: "1.5" }), "EUR")).toEqual({ buffer: "validation.wholeNumber" });
    expect(validateKnowledgeForm(service({ buffer: String(MAX_BUFFER_MINUTES + 1) }), "EUR")).toEqual({
      buffer: "knowledge.offer.errors.bufferRange",
    });
    // A room type has no break: a stale value is not checked or sent.
    expect(validateKnowledgeForm(service({ kind: "room_type", buffer: "x" }), "EUR")).toEqual({});
    const overlapping = service({ kind: "room_type", seasons: [row(), row()] });
    expect(validateKnowledgeForm(overlapping, "EUR").seasons?.overlap).toEqual([0, 1]);
    const many = Array.from({ length: MAX_SEASONS + 1 }, (_, index) =>
      row({ startMonth: String((index % 12) + 1), startDay: String(Math.floor(index / 12) + 1), endMonth: String((index % 12) + 1), endDay: String(Math.floor(index / 12) + 1) }),
    );
    expect(validateKnowledgeForm(service({ kind: "room_type", seasons: many }), "EUR").seasons?.tooMany).toBe(true);
  });

  it("sends only what the kind may have", () => {
    expect(knowledgeCreateBody(service({ buffer: "10", performerIds: ["nino", "nino"], seasons: [row()] }), "EUR")).toMatchObject({
      duration_minutes: 45,
      buffer_minutes: 10,
      performer_resource_ids: ["nino"],
    });
    expect(knowledgeCreateBody(service({ buffer: "0" }), "EUR")).not.toHaveProperty("buffer_minutes");
    const room = knowledgeCreateBody(service({ kind: "room_type", duration: "", buffer: "10", performerIds: ["r1"], seasons: [row()] }), "EUR");
    expect(room).toMatchObject({ performer_resource_ids: ["r1"], seasonal_rates: [{ starts_on: "06-01", ends_on: "08-31", nightly_rate_minor: 15000 }] });
    expect(room).not.toHaveProperty("buffer_minutes");
    expect(knowledgeCreateBody(service({ kind: "faq", performerIds: ["nino"] }), "EUR")).not.toHaveProperty("performer_resource_ids");
  });

  it("patches only changed offer fields and clears what a new kind cannot have", () => {
    const initial = knowledgeFormFromItem(
      {
        kind: "service",
        title: "Haircut",
        body: null,
        price_minor: 3500,
        duration_minutes: 45,
        buffer_minutes: 10,
        performer_resource_ids: ["nino"],
      },
      "EUR",
    );
    expect(initial).toMatchObject({ buffer: "10", performerIds: ["nino"], seasons: [] });
    expect(knowledgePatchBody({ ...initial }, initial, "EUR")).toEqual({});
    expect(knowledgePatchBody({ ...initial, performerIds: ["lena", "nino"], buffer: "" }, initial, "EUR")).toEqual({
      performer_resource_ids: ["lena", "nino"],
      buffer_minutes: null,
    });
    expect(knowledgePatchBody({ ...initial, kind: "faq", body: "Yes" }, initial, "EUR")).toEqual({
      kind: "faq",
      body: "Yes",
      price_minor: null,
      buffer_minutes: null,
      performer_resource_ids: [],
    });
    const room = knowledgeFormFromItem(
      {
        kind: "room_type",
        title: "Deluxe",
        body: null,
        price_minor: 10000,
        duration_minutes: null,
        seasonal_rates: [{ starts_on: "06-01", ends_on: "08-31", nightly_rate_minor: 15000 }],
      },
      "EUR",
    );
    expect(knowledgePatchBody({ ...room, seasons: [] }, room, "EUR")).toEqual({ seasonal_rates: [] });
  });
});
