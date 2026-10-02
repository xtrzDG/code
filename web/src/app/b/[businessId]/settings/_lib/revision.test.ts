import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/errors";

import { buildGeneralChanges, generalFormFrom, hasChanges, type BusinessView } from "./general";
import { afterStatusSwitch, changesFromRevision, isStaleRevision, rebaseGeneralForm } from "./revision";
import { business } from "./settingsFixtures";

describe("concurrent saves", () => {
  it("sends the changes with the revision they were made from", () => {
    expect(changesFromRevision({ city: "Batumi" }, business)).toEqual({ city: "Batumi", expected_revision: 4 });
    expect(hasChanges({})).toBe(false);
  });

  it("recognises a save refused because someone saved since", () => {
    const stale = new ApiError({
      status: 409,
      code: "conflict",
      reasons: [{ code: "stale_revision", message: "Saved by someone else.", details: ["5"] }],
    });
    const otherConflict = new ApiError({ status: 409, code: "conflict", reasons: [{ code: "dpa", message: "", details: [] }] });

    expect(isStaleRevision(stale)).toBe(true);
    expect(isStaleRevision(otherConflict)).toBe(false);
    expect(isStaleRevision(new ApiError({ status: 422, code: "validation_failed" }))).toBe(false);
  });

  it("takes over the revision of the tab's own status switch, not someone else's changes", () => {
    const paused = { ...business, status: "paused" as const, revision: 5 };
    const pausedAfterARename = { ...paused, name: "Café Batumi" };

    expect(afterStatusSwitch(business, paused)).toBe(paused);
    expect(afterStatusSwitch(paused, business)).toBe(paused);
    expect(afterStatusSwitch(business, null)).toBe(business);
    // The form would send the old name back as a change: keep the old revision.
    expect(afterStatusSwitch(business, pausedAfterARename)).toBe(business);
  });
});

describe("rebaseGeneralForm", () => {
  const typed = { ...generalFormFrom(business), name: "Café Batumi", city: "Batumi", retentionDays: "30" };

  it("keeps everything typed when only the revision moved (a manager linked elsewhere)", () => {
    const latest: BusinessView = {
      ...business,
      revision: 5,
      manager_contacts: [{ name: "Levan", channel: "telegram", address: "777000111", language: "ka" }],
    };

    const rebased = rebaseGeneralForm(business, latest, typed);

    expect(rebased).toEqual({ form: typed, conflicts: [] });
    expect(buildGeneralChanges(latest, rebased.form)).toEqual(buildGeneralChanges(business, typed));
  });

  it("takes what someone else changed in other fields and keeps the owner's own", () => {
    const latest: BusinessView = { ...business, revision: 5, timezone: "Europe/Berlin" };

    const rebased = rebaseGeneralForm(business, latest, typed);

    expect(rebased.conflicts).toEqual([]);
    expect(rebased.form).toEqual({ ...typed, timezone: "Europe/Berlin" });
  });

  it("shows the stored value of a field changed on both sides and reports it", () => {
    const differently: BusinessView = { ...business, revision: 5, city: "Kutaisi" };
    const theSame: BusinessView = { ...business, revision: 5, city: "Batumi" };

    expect(rebaseGeneralForm(business, differently, typed)).toEqual({
      form: { ...typed, city: "Kutaisi" },
      conflicts: ["city"],
    });
    expect(rebaseGeneralForm(business, theSame, typed)).toEqual({ form: typed, conflicts: [] });
  });

  it("compares languages by value", () => {
    const latest: BusinessView = { ...business, revision: 5, languages: ["ka", "en"] };
    const withRussian = { ...generalFormFrom(business), languages: ["ka", "en", "ru"] };

    expect(rebaseGeneralForm(business, latest, generalFormFrom(business)).conflicts).toEqual([]);
    expect(rebaseGeneralForm(business, latest, withRussian)).toEqual({ form: withRussian, conflicts: [] });
  });
});
