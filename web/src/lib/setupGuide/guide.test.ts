import { describe, expect, it } from "vitest";

import type { Schema } from "@/api/types";

import { guideFixture } from "./fixtures";
import { CELEBRATE_WITHIN_MS, guideCard, guideRows, pendingCelebrations, reachedWins, showsRing } from "./guide";

type SetupView = Schema<"SetupView">;
type StepCode = Schema<"SetupStepCode">;
type Status = Schema<"SetupStepStatus">;

const SETUP_CODES: StepCode[] = ["business", "offer", "hours_and_bookings", "staff_contact", "channels", "test", "launch"];
const NOW_MS = Date.UTC(2026, 9, 3, 12);

function setup(extra: Partial<SetupView> = {}, statuses: Partial<Record<StepCode, Status>> = {}): SetupView {
  return {
    business_id: "business_1",
    language: "en",
    steps: SETUP_CODES.map((code) => ({
      code,
      status: statuses[code] ?? "done",
      is_required: code !== "offer" && code !== "channels" && code !== "test",
      title: code,
      description: code,
      minutes: 2,
      action:
        code === "staff_contact"
          ? { target: "staff_contacts", label: code }
          : code === "launch"
            ? { target: "apply_changes", label: code }
            : { target: "profile", profile_step: "contacts_and_hours", label: code },
      missing: [],
    })),
    next_action: { target: "overview", label: "Overview" },
    percent: 70,
    minutes_left: 10,
    can_go_live: true,
    is_live: true,
    is_complete: true,
    apply: { business_id: "business_1", is_in_progress: false, has_unapplied_changes: false },
    guide: guideFixture(),
    ...extra,
  };
}

function milestone(kind: Schema<"ActivationEventKind">, ageMs: number, celebrated = false): Schema<"ActivationMilestoneView"> {
  return { kind, occurred_at: (NOW_MS - ageMs) * 1000, celebrated_at: celebrated ? NOW_MS * 1000 : null };
}

describe("the setup guide", () => {
  it("before the launch lists the setup's steps into the tunnel, then the ones after it", () => {
    const rows = guideRows(setup({ is_live: false }, { staff_contact: "next", launch: "todo" }), "business_1");

    expect(rows.map((row) => row.step.code)).toEqual([...SETUP_CODES, "phone_test", "second_channel", "share"]);
    const staff = rows.find((row) => row.step.code === "staff_contact");
    expect(staff).toMatchObject({ kind: "tunnel", href: "/b/business_1/setup?step=people", canSkip: false });
    expect(rows.find((row) => row.step.code === "hours_and_bookings")?.href).toBeNull();
  });

  it("once live shows the steps to the first customers, each with its place", () => {
    const rows = guideRows(setup(), "business_1");

    expect(rows.map((row) => [row.step.code, row.kind, row.href])).toEqual([
      ["phone_test", "phone", null],
      ["second_channel", "page", "/b/business_1/assistant/channels"],
      ["share", "page", "/b/business_1/assistant/channels#share"],
    ]);
    expect(rows.every((row) => row.canSkip)).toBe(true);
  });

  it("brings a setup step back only when the live guide needs it again", () => {
    const needed = setup({ guide: guideFixture({}, { next_step: "hours_and_bookings" }) }, { hours_and_bookings: "next" });

    const rows = guideRows(needed, "business_1");

    expect(rows[0]?.step.code).toBe("hours_and_bookings");
    expect(rows[0]?.href).toBe("/b/business_1/assistant/profile");
  });

  it("is shown to owners until finished, then briefly, then never", () => {
    expect(guideCard(setup(), true)).toBe("guide");
    expect(guideCard(setup(), false)).toBe("hidden");
    expect(guideCard(undefined, true)).toBe("hidden");
    expect(guideCard(setup({ guide: guideFixture({}, { is_complete: true }) }), true)).toBe("finished");
    expect(guideCard(setup({ guide: guideFixture({}, { is_complete: true, is_dismissed: true }) }), true)).toBe("hidden");
    expect(showsRing(setup(), true)).toBe(true);
    expect(showsRing(setup({ guide: guideFixture({}, { is_complete: true }) }), true)).toBe(false);
  });

  it("celebrates recent milestones and quietly acknowledges old ones and the owner's own test", () => {
    const tested = milestone("first_conversation", 1000);
    const view = setup({
      milestones: [
        milestone("went_live", 5000),
        milestone("first_booking", 2000),
        tested,
        milestone("first_after_hours_booking", CELEBRATE_WITHIN_MS + 1),
        milestone("first_handoff", 10),
      ],
      guide: guideFixture({}, { phone_tested_at: tested.occurred_at }),
    });

    const pending = pendingCelebrations(view, NOW_MS);

    expect(pending.show.map((item) => item.kind)).toEqual(["first_booking"]);
    expect(pending.quiet.map((item) => item.kind)).toEqual(["first_after_hours_booking", "first_conversation"]);
    expect(pendingCelebrations(undefined, NOW_MS)).toEqual({ show: [], quiet: [] });
  });

  it("lists the wins reached, oldest first", () => {
    const view = setup({
      milestones: [milestone("first_booking", 10, true), milestone("went_live", 50), milestone("first_conversation", 20, true)],
    });

    expect(reachedWins(view).map((item) => item.kind)).toEqual(["first_conversation", "first_booking"]);
  });
});
