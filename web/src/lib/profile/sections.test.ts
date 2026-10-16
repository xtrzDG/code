import { describe, expect, it } from "vitest";

import {
  gapsBySection,
  isProfileSection,
  PROFILE_SECTIONS,
  profilePath,
  profileSectionPath,
  questionStepsOf,
  SECTION_OF_STEP,
  sectionQuestions,
  sectionOfGap,
  sectionOfStepParam,
} from "./sections";

describe("profile sections", () => {
  it("are the tunnel's screens a live owner edits, plus the rules", () => {
    expect(PROFILE_SECTIONS).toEqual(["business", "place", "offer", "hours", "people", "rules"]);
    expect(isProfileSection("hours")).toBe(true);
    expect(isProfileSection("launch")).toBe(false);
    expect(isProfileSection(null)).toBe(false);
  });

  it("live under Assistant → Business profile", () => {
    expect(profilePath("biz 1")).toBe("/b/biz%201/assistant/profile");
    expect(profileSectionPath("biz_1", "offer")).toBe("/b/biz_1/assistant/profile/offer");
  });

  it("send the old six steps' addresses to the section that edits them now", () => {
    expect(sectionOfStepParam("booking_rules")).toBe("hours");
    expect(sectionOfStepParam(["faq_and_handoff", "offer"])).toBe("rules");
    expect(sectionOfStepParam("channels")).toBe("business");
    expect(sectionOfStepParam("launch")).toBeNull();
    expect(sectionOfStepParam("constructor")).toBeNull();
    expect(sectionOfStepParam(undefined)).toBeNull();
  });

  it("ask every niche question in exactly one section", () => {
    const asked = PROFILE_SECTIONS.flatMap((section) => [...questionStepsOf(section)]);
    expect(asked.sort()).toEqual(Object.keys(SECTION_OF_STEP).sort());
    expect([...questionStepsOf("hours")].sort()).toEqual(["booking_rules", "contacts_and_hours"]);
    expect(questionStepsOf("people").size).toBe(0);
  });

  it("ask a section's own niche questions, in the profile's order", () => {
    const question = (key: string, step: "niche_and_languages" | "channels" | "offer") => ({
      question: { key, fact_key: key, step, answer_type: "short_text" as const, is_required: false, label: key },
    });
    const wizard = { steps: [{ questions: [question("cuisine", "niche_and_languages"), question("menu", "offer")] }, { questions: [question("instagram", "channels")] }, {}] };
    expect(sectionQuestions(wizard, "business").map((item) => item.question.key)).toEqual(["cuisine", "instagram"]);
    expect(sectionQuestions(wizard, "offer").map((item) => item.question.key)).toEqual(["menu"]);
    expect(sectionQuestions(wizard, "rules")).toEqual([]);
  });

  it("place each kind of “what to add” item in its section", () => {
    expect(sectionOfGap({ kind: "no_address", step: "contacts_and_hours" })).toBe("place");
    expect(sectionOfGap({ kind: "no_handoff_contact", step: "faq_and_handoff" })).toBe("people");
    expect(sectionOfGap({ kind: "missing_required_answer", step: "offer" })).toBe("offer");
    expect(sectionOfGap({ kind: "unanswered_question", step: "faq_and_handoff" })).toBe("rules");
  });

  it("count blocking items and advice per section", () => {
    const counts = gapsBySection([
      { kind: "no_opening_hours", step: "contacts_and_hours", is_blocking: true },
      { kind: "no_booking_rules", step: "booking_rules", is_blocking: false },
      { kind: "no_faq", step: "faq_and_handoff", is_blocking: false },
      { kind: "unanswered_question", step: "faq_and_handoff", is_blocking: false },
    ]);
    expect(counts.hours).toEqual({ blocking: 1, advice: 1 });
    expect(counts.rules).toEqual({ blocking: 0, advice: 2 });
    expect(counts.business).toEqual({ blocking: 0, advice: 0 });
  });
});
