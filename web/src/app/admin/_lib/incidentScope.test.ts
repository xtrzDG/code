import { describe, expect, it } from "vitest";

import { buildIncidentBody, emptyIncidentForm, withAnnouncement, withKind, type IncidentForm } from "./incidentForm";
import { localInputToMicros } from "./localTime";

const NOW = localInputToMicros("2026-10-04T12:00") ?? 0;

function outage(overrides: Partial<IncidentForm> = {}): IncidentForm {
  return {
    ...emptyIncidentForm(NOW),
    title: "Replies are late on every channel",
    startedAt: "2026-10-04T10:15",
    ...overrides,
  };
}

describe("every business", () => {
  it("needs no business list and sends the scope for the worker to walk", () => {
    const built = buildIncidentBody(outage({ scope: "all_businesses", businesses: "" }), NOW);

    expect(built.ok).toBe(true);
    expect(built.ok && built.body.scope).toBe("all_businesses");
    expect(built.ok && built.body.affected_business_ids).toEqual([]);
  });

  it("ignores what is left in the list once every business is chosen", () => {
    const built = buildIncidentBody(outage({ scope: "all_businesses", businesses: "acme" }), NOW);

    expect(built.ok && built.body.affected_business_ids).toEqual([]);
  });

  it("still needs the list for listed businesses", () => {
    const built = buildIncidentBody(outage({ businesses: "" }), NOW);

    expect(!built.ok && built.errors.fields).toEqual({ businesses: "required" });
  });
});

describe("the status announcement", () => {
  it("is not published unless offered", () => {
    const built = buildIncidentBody(outage({ scope: "all_businesses" }), NOW);

    expect(built.ok && built.body.announcement).toBeNull();
  });

  it("starts from the incident's title and level, and goes with the incident", () => {
    const form = withAnnouncement(withKind(outage({ scope: "all_businesses" }), "degradation"), true);

    expect(form.announcement.texts.en).toBe("Replies are late on every channel");
    const built = buildIncidentBody(form, NOW);
    expect(built.ok && built.body.announcement).toEqual({
      level: "degraded",
      components: ["chat", "meta", "telegram"],
      messages: [{ language: "en", text: "Replies are late on every channel" }],
      starts_at: null,
      expected_end_at: null,
    });
  });

  it("keeps a text already written when offered again", () => {
    const written = { ...outage(), announcement: { ...outage().announcement, texts: { en: "Our own words", ka: "", ru: "" } } };

    expect(withAnnouncement(written, true).announcement.texts.en).toBe("Our own words");
  });

  it("names its problems next to the incident's", () => {
    const form = withAnnouncement(outage({ title: "", scope: "all_businesses" }), true);
    const built = buildIncidentBody({ ...form, announcement: { ...form.announcement, components: [] } }, NOW);

    expect(built.ok).toBe(false);
    if (!built.ok) {
      expect(built.errors.fields).toEqual({ title: "required" });
      expect(built.errors.announcement).toEqual({ texts: { en: "textRequired" }, components: "componentsRequired" });
    }
  });

  it("is not offered for a data breach, whose owners are told directly", () => {
    const offered = withAnnouncement(outage(), true);

    expect(withKind(offered, "data_breach").announce).toBe(false);
    expect(withKind(offered, "outage").announcement.level).toBe("outage");
  });
});
