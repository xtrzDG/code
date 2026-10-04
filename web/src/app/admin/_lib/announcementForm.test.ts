import { describe, expect, it } from "vitest";

import {
  buildCreateBody,
  buildUpdateBody,
  cleanText,
  emptyAnnouncementForm,
  formFromAnnouncement,
  needsComponents,
  type AdminAnnouncement,
  type AnnouncementForm,
} from "./announcementForm";
import { localInputToMicros } from "./incidentForm";

const NOW = localInputToMicros("2026-10-04T12:00") ?? 0;
const HOUR = 3_600_000_000;

function form(overrides: Partial<AnnouncementForm> = {}): AnnouncementForm {
  return {
    ...emptyAnnouncementForm(),
    level: "outage",
    components: ["meta"],
    texts: { en: "  WhatsApp replies\nare slow.  ", ka: "", ru: "Ответы в WhatsApp идут медленно." },
    ...overrides,
  };
}

function published(overrides: Partial<AdminAnnouncement> = {}): AdminAnnouncement {
  return {
    id: "announcement_1",
    level: "outage",
    status: "active",
    components: ["meta"],
    messages: [
      { language: "en", text: "WhatsApp replies are slow." },
      { language: "ru", text: "Ответы в WhatsApp идут медленно." },
    ],
    starts_at: NOW - HOUR,
    expected_end_at: null,
    resolved_at: null,
    created_by: "user_1",
    created_at: NOW - HOUR,
    updated_at: NOW - HOUR,
    updated_by: null,
    ...overrides,
  };
}

describe("a new announcement", () => {
  it("sends one-line texts in the languages filled in, starting now", () => {
    expect(buildCreateBody(form(), NOW)).toEqual({
      ok: true,
      body: {
        level: "outage",
        components: ["meta"],
        messages: [
          { language: "en", text: "WhatsApp replies are slow." },
          { language: "ru", text: "Ответы в WhatsApp идут медленно." },
        ],
        starts_at: null,
        expected_end_at: null,
      },
    });
  });

  it("plans maintenance ahead with an expected end", () => {
    const built = buildCreateBody(form({ level: "maintenance", startsAt: "2026-10-05T02:00", expectedEnd: "2026-10-05T04:00" }), NOW);
    expect(built.ok && built.body.starts_at).toBe(localInputToMicros("2026-10-05T02:00"));
    expect(built.ok && built.body.expected_end_at).toBe(localInputToMicros("2026-10-05T04:00"));
  });

  it("names no part for a notice", () => {
    const built = buildCreateBody(form({ level: "info", components: ["chat"] }), NOW);
    expect(built.ok && built.body.components).toEqual([]);
    expect(needsComponents("info")).toBe(false);
  });

  it("explains what is missing or wrong", () => {
    expect(
      buildCreateBody(form({ components: [], texts: { en: " ", ka: "აბ", ru: "" }, startsAt: "soon", expectedEnd: "2026-10-04T11:00" }), NOW),
    ).toEqual({
      ok: false,
      errors: { texts: { en: "textRequired", ka: "textShort" }, components: "componentsRequired", startsAt: "time", expectedEnd: "endBeforeStart" },
    });
    expect(buildCreateBody(form({ startsAt: "2027-01-01T00:00", expectedEnd: "later" }), NOW)).toEqual({
      ok: false,
      errors: { texts: {}, startsAt: "startTooLate", expectedEnd: "time" },
    });
  });
});

describe("updating an announcement", () => {
  it("starts from what is published", () => {
    const start = formFromAnnouncement(published({ expected_end_at: NOW + HOUR, messages: [{ language: "de", text: "Langsam." }] }));
    expect(start.texts).toEqual({ en: "", ka: "", ru: "" });
    expect(start.expectedEnd).not.toBe("");
  });

  it("sends only what changed", () => {
    const original = published();
    const unchanged = formFromAnnouncement(original);
    expect(buildUpdateBody(unchanged, original, NOW)).toEqual({ ok: true, body: null });

    const changed = { ...unchanged, level: "degraded" as const, components: ["meta", "chat"] as AnnouncementForm["components"], expectedEnd: "2026-10-04T14:00" };
    expect(buildUpdateBody({ ...changed, texts: { ...changed.texts, ka: "WhatsApp ნელა მუშაობს." } }, original, NOW)).toEqual({
      ok: true,
      body: {
        level: "degraded",
        components: ["meta", "chat"],
        messages: [
          { language: "en", text: "WhatsApp replies are slow." },
          { language: "ka", text: "WhatsApp ნელა მუშაობს." },
          { language: "ru", text: "Ответы в WhatsApp идут медленно." },
        ],
        expected_end_at: localInputToMicros("2026-10-04T14:00"),
      },
    });
  });

  it("keeps an expected end that already passed, but refuses a new one in the past", () => {
    const original = published({ expected_end_at: NOW - 30 * 60_000_000 });
    expect(buildUpdateBody(formFromAnnouncement(original), original, NOW)).toEqual({ ok: true, body: null });
    expect(buildUpdateBody({ ...formFromAnnouncement(original), expectedEnd: "2026-10-04T11:45" }, original, NOW)).toEqual({
      ok: false,
      errors: { texts: {}, expectedEnd: "endBeforeStart" },
    });
  });
});

describe("cleanText", () => {
  it("makes one line without spaces around it", () => {
    expect(cleanText("  a\n\n b\t ")).toBe("a b");
  });
});
