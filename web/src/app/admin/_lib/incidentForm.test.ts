import { describe, expect, it } from "vitest";

import {
  buildIncidentBody,
  emptyIncidentForm,
  localInputToMicros,
  microsToLocalInput,
  noticeFill,
  parseBusinessIds,
  withKind,
  type IncidentForm,
  type NoticeTexts,
} from "./incidentForm";

const BUSINESS_A = "business_0f8b8f0e-8d3a-4a49-9f39-3c4f2b0a9e11";
const BUSINESS_B = "business_6a1d3c52-1f0e-4b7a-8c55-0d2e9f6b7a34";
const NOW = localInputToMicros("2026-10-04T12:00") ?? 0;

function notice(text = "Text"): NoticeTexts {
  return {
    nature: `${text}: what happened`,
    subject_categories: `${text}: people`,
    record_categories: `${text}: records`,
    likely_consequences: `${text}: consequences`,
    measures: `${text}: measures`,
  };
}

function outage(overrides: Partial<IncidentForm> = {}): IncidentForm {
  return {
    ...emptyIncidentForm(NOW),
    title: "  WhatsApp replies   delayed ",
    startedAt: "2026-10-04T10:15",
    detectedAt: "2026-10-04T10:20",
    businesses: BUSINESS_A,
    ...overrides,
  };
}

function breach(overrides: Partial<IncidentForm> = {}): IncidentForm {
  const form = withKind(outage(), "data_breach");
  return {
    ...form,
    subjectCount: "120",
    recordCount: "240",
    notices: { ...form.notices, en: notice("en") },
    ...overrides,
  };
}

describe("times", () => {
  it("reads and writes datetime-local values in the device's time zone", () => {
    const micros = localInputToMicros("2026-10-04T09:30");

    expect(micros).not.toBeNull();
    expect(microsToLocalInput(micros ?? 0)).toBe("2026-10-04T09:30");
    expect(localInputToMicros("2026-02-30T09:30")).toBeNull();
    expect(localInputToMicros("yesterday")).toBeNull();
  });
});

describe("parseBusinessIds", () => {
  it("takes ids and client page links, each once, and names what is neither", () => {
    const parsed = parseBusinessIds(
      `${BUSINESS_A}\nhttps://cabinet.example/admin/clients/${BUSINESS_B.toUpperCase().replace("BUSINESS", "business")}, ${BUSINESS_A}; acme`,
    );

    expect(parsed.ids).toEqual([BUSINESS_A, BUSINESS_B]);
    expect(parsed.unknown).toEqual(["acme"]);
    expect(parseBusinessIds("  \n ")).toEqual({ ids: [], unknown: [] });
  });
});

describe("buildIncidentBody", () => {
  it("builds an outage without a notice", () => {
    const built = buildIncidentBody(outage({ severity: "sev1" }), NOW);

    expect(built).toEqual({
      ok: true,
      body: {
        kind: "outage",
        severity: "sev1",
        title: "WhatsApp replies delayed",
        started_at: localInputToMicros("2026-10-04T10:15"),
        detected_at: localInputToMicros("2026-10-04T10:20"),
        affected_business_ids: [BUSINESS_A],
        approximate_subject_count: null,
        approximate_record_count: null,
        notice_texts: [],
      },
    });
  });

  it("leaves the detection time to the server when it is empty", () => {
    const built = buildIncidentBody(outage({ detectedAt: "" }), NOW);

    expect(built.ok && built.body.detected_at).toBeNull();
  });

  it("refuses a missing title, times in the future or out of order, and unknown businesses", () => {
    const built = buildIncidentBody(
      outage({ title: "ok", startedAt: "2026-10-04T12:30", detectedAt: "2026-10-04T10:00", businesses: "acme" }),
      NOW,
    );

    expect(built.ok).toBe(false);
    if (!built.ok) {
      expect(built.errors.fields).toEqual({ title: "title", startedAt: "future", businesses: "businessIds" });
      expect(built.errors.unknownBusinesses).toEqual(["acme"]);
    }
    const ordered = buildIncidentBody(outage({ startedAt: "2026-10-04T10:30", detectedAt: "2026-10-04T10:00" }), NOW);
    expect(!ordered.ok && ordered.errors.fields).toEqual({ detectedAt: "order" });
    const empty = buildIncidentBody(outage({ title: " ", startedAt: "", businesses: "" }), NOW);
    expect(!empty.ok && empty.errors.fields).toEqual({ title: "required", startedAt: "required", businesses: "required" });
    const later = buildIncidentBody(outage({ detectedAt: "2026-10-04T12:01" }), NOW);
    expect(!later.ok && later.errors.fields).toEqual({ detectedAt: "future" });
  });

  it("makes a breach SEV1 and sends the complete notices only", () => {
    const form = breach({ notices: { en: notice("en"), ka: notice("ka"), ru: { ...notice("ru"), measures: "" } } });

    const built = buildIncidentBody(form, NOW);
    expect(built.ok).toBe(false);
    expect(!built.ok && built.errors.notices).toEqual({ ru: "noticeIncomplete" });

    const fixed = buildIncidentBody({ ...form, notices: { ...form.notices, ru: notice("") } }, NOW);
    expect(fixed.ok).toBe(true);
    if (fixed.ok) {
      expect(fixed.body.severity).toBe("sev1");
      expect(fixed.body.approximate_subject_count).toBe(120);
      expect(fixed.body.approximate_record_count).toBe(240);
      expect(fixed.body.notice_texts?.map((text) => text.language)).toEqual(["en", "ka", "ru"]);
    }
    const englishOnly = buildIncidentBody(breach(), NOW);
    expect(englishOnly.ok && englishOnly.body.notice_texts?.map((text) => text.language)).toEqual(["en"]);
  });

  it("needs the English notice and both counts for a breach", () => {
    const built = buildIncidentBody(
      breach({ subjectCount: "", recordCount: "1.5", notices: { en: notice(""), ka: notice("ka"), ru: notice("ru") } }),
      NOW,
    );

    expect(built.ok).toBe(false);
    if (!built.ok) {
      expect(built.errors.fields).toEqual({ subjectCount: "required", recordCount: "count" });
      expect(built.errors.notices).toEqual({});
    }
    const missing = buildIncidentBody(breach({ notices: emptyIncidentForm(NOW).notices }), NOW);
    expect(!missing.ok && missing.errors.notices).toEqual({ en: "noticeRequired" });
  });
});

describe("withKind and noticeFill", () => {
  it("keeps the chosen severity for an outage and forces SEV1 for a breach", () => {
    const form = outage({ severity: "sev3" });

    expect(withKind(form, "degradation").severity).toBe("sev3");
    expect(withKind(form, "data_breach").severity).toBe("sev1");
  });

  it("tells a complete notice from an empty or a partial one", () => {
    expect(noticeFill(notice())).toBe("complete");
    expect(noticeFill({ ...notice(), nature: " " })).toBe("partial");
    expect(noticeFill(emptyIncidentForm(NOW).notices.ka)).toBe("empty");
  });
});
