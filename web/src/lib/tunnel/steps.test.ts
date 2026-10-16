import { describe, expect, it } from "vitest";

import type { Schema } from "@/api/types";
import { guideFixture } from "@/lib/setupGuide/fixtures";

import {
  FINALE,
  direction,
  fixPlace,
  isSkippable,
  isTunnelPlace,
  nextPlace,
  placeIndex,
  placeQuery,
  previousStep,
  resumePlace,
  stepNumber,
  stepStates,
  TUNNEL_STEPS,
} from "./steps";

type SetupView = Schema<"SetupView">;
type StepCode = Schema<"SetupStepCode">;
type Status = Schema<"SetupStepStatus">;

const ACTION = { target: "profile", label: "Fill in" } as const;

function setup(statuses: Partial<Record<StepCode, Status>>, extra: Partial<SetupView> = {}, missing: Partial<Record<StepCode, Schema<"ProfileGapKind">[]>> = {}): SetupView {
  const codes: StepCode[] = ["business", "offer", "hours_and_bookings", "staff_contact", "channels", "test", "launch"];
  return {
    business_id: "business_1",
    language: "en",
    steps: codes.map((code) => ({
      code,
      status: statuses[code] ?? "todo",
      is_required: true,
      title: code,
      description: code,
      minutes: 1,
      action: ACTION,
      missing: missing[code] ?? [],
    })),
    next_action: ACTION,
    percent: 0,
    minutes_left: 10,
    can_go_live: false,
    is_live: false,
    is_complete: false,
    apply: { business_id: "business_1", is_in_progress: false, has_unapplied_changes: true },
    guide: guideFixture(),
    ...extra,
  };
}

describe("tunnel steps", () => {
  it("go in order, eight of them, then the finale", () => {
    expect(TUNNEL_STEPS).toHaveLength(8);
    expect(stepNumber("business")).toBe(1);
    expect(stepNumber("launch")).toBe(8);
    expect(nextPlace("business")).toBe("place");
    expect(nextPlace("launch")).toBe(FINALE);
    expect(previousStep("place")).toBe("business");
    expect(previousStep("business")).toBeNull();
    expect(previousStep(FINALE)).toBe("launch");
    expect(placeIndex(FINALE)).toBe(8);
  });

  it("tell places from other values", () => {
    expect(isTunnelPlace("offer")).toBe(true);
    expect(isTunnelPlace("done")).toBe(true);
    expect(isTunnelPlace("dashboard")).toBe(false);
    expect(isTunnelPlace(null)).toBe(false);
    expect(isTunnelPlace(undefined)).toBe(false);
  });

  it("let only the optional steps be skipped", () => {
    expect(isSkippable("offer")).toBe(true);
    expect(isSkippable("channels")).toBe(true);
    expect(isSkippable("try")).toBe(true);
    expect(isSkippable("people")).toBe(false);
    expect(isSkippable("launch")).toBe(false);
  });

  it("know which way a move goes", () => {
    expect(direction("business", "place")).toBe(1);
    expect(direction("launch", FINALE)).toBe(1);
    expect(direction("hours", "offer")).toBe(-1);
    expect(direction("try", "try")).toBe(0);
  });

  it("write the place into the address", () => {
    expect(placeQuery("hours")).toBe("?step=hours");
  });
});

describe("where an owner continues", () => {
  it("is the first step still to do", () => {
    expect(resumePlace(setup({ business: "done", offer: "skipped", hours_and_bookings: "next" }))).toBe("hours");
  });

  it("is the address screen when only the address is missing", () => {
    const view = setup({ business: "next" }, {}, { business: ["no_address"] });
    expect(stepStates(view).business).toBe("done");
    expect(stepStates(view).place).toBe("todo");
    expect(resumePlace(view)).toBe("place");
  });

  it("is the first screen when a required answer is missing too", () => {
    const view = setup({ business: "next" }, {}, { business: ["missing_required_answer", "no_address"] });
    expect(stepStates(view).business).toBe("todo");
    expect(resumePlace(view)).toBe("business");
  });

  it("is the launch once everything before it is done or skipped", () => {
    const view = setup({
      business: "done",
      offer: "done",
      hours_and_bookings: "done",
      staff_contact: "done",
      channels: "skipped",
      test: "skipped",
      launch: "next",
    });
    expect(stepStates(view).channels).toBe("skipped");
    expect(resumePlace(view)).toBe("launch");
  });

  it("is the finale once the assistant is live", () => {
    const view = setup({ business: "done" }, { is_live: true });
    expect(resumePlace(view)).toBe(FINALE);
    expect(stepStates(view).launch).toBe("done");
  });

  it("treats a step the API does not list as still to do", () => {
    const view = { ...setup({}), steps: [] };
    expect(stepStates(view).offer).toBe("todo");
    expect(stepStates(view).place).toBe("done");
  });
});

describe("where a fix lives", () => {
  it("maps profile steps to the tunnel step asking the same", () => {
    expect(fixPlace({ target: "profile", profile_step: "offer", label: "x" })).toEqual({ kind: "step", step: "offer" });
    expect(fixPlace({ target: "profile", profile_step: "booking_rules", label: "x" })).toEqual({ kind: "step", step: "hours" });
    expect(fixPlace({ target: "profile", profile_step: "contacts_and_hours", label: "x" })).toEqual({ kind: "step", step: "hours" });
    expect(fixPlace({ target: "profile", profile_step: "faq_and_handoff", label: "x" })).toEqual({ kind: "step", step: "business" });
    expect(fixPlace({ target: "profile", label: "x" })).toEqual({ kind: "step", step: "business" });
  });

  it("maps the other targets", () => {
    expect(fixPlace({ target: "staff_contacts", label: "x" })).toEqual({ kind: "step", step: "people" });
    expect(fixPlace({ target: "channels", label: "x" })).toEqual({ kind: "step", step: "channels" });
    expect(fixPlace({ target: "test_chat", label: "x" })).toEqual({ kind: "step", step: "try" });
    expect(fixPlace({ target: "agreement", label: "x" })).toEqual({ kind: "step", step: "launch" });
    expect(fixPlace({ target: "apply_changes", label: "x" })).toEqual({ kind: "step", step: "launch" });
    expect(fixPlace({ target: "billing", label: "x" })).toEqual({ kind: "billing" });
    expect(fixPlace({ target: "checks", label: "x" })).toEqual({ kind: "checks" });
    expect(fixPlace({ target: "overview", label: "x" })).toEqual({ kind: "finale" });
  });
});
