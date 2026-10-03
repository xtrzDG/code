import { describe, expect, it } from "vitest";

import type { Schema } from "@/api/types";

import { finaleNextSteps } from "./finale";

type StepCode = Schema<"SetupStepCode">;
type Status = Schema<"SetupStepStatus">;

function setup(statuses: Partial<Record<StepCode, Status>> = {}): Schema<"SetupView"> {
  const codes: StepCode[] = ["business", "offer", "hours_and_bookings", "staff_contact", "channels", "test", "launch"];
  const action = { target: "overview", label: "Done" } as const;
  return {
    business_id: "business_1",
    language: "en",
    steps: codes.map((code) => ({
      code,
      status: statuses[code] ?? "done",
      is_required: true,
      title: code,
      description: code,
      minutes: 1,
      action,
    })),
    next_action: action,
    percent: 100,
    minutes_left: 0,
    can_go_live: true,
    is_live: true,
    is_complete: true,
    apply: { business_id: "business_1", is_in_progress: false, has_unapplied_changes: false },
  };
}

describe("finale next steps", () => {
  it("name the messengers that are not connected yet, two at most", () => {
    const steps = finaleNextSteps(setup(), ["web_chat"]);
    expect(steps.map((step) => step.key)).toEqual(["channels", "knowledge", "messages"]);
    expect(steps[0]?.channels).toEqual(["whatsapp", "instagram"]);
  });

  it("skip a connected WhatsApp and name what is left", () => {
    expect(finaleNextSteps(setup(), ["web_chat", "whatsapp"])[0]?.channels).toEqual(["instagram", "telegram"]);
    expect(finaleNextSteps(setup(), ["whatsapp", "instagram", "telegram"])[0]?.channels).toEqual(["messenger"]);
  });

  it("leave channels out when every messenger is connected", () => {
    const steps = finaleNextSteps(setup(), ["whatsapp", "instagram", "telegram", "messenger", "web_chat"]);
    expect(steps.map((step) => step.key)).toEqual(["knowledge", "messages"]);
  });

  it("bring back a skipped offer step first", () => {
    const steps = finaleNextSteps(setup({ offer: "skipped" }), ["whatsapp", "instagram", "telegram", "messenger"]);
    expect(steps.map((step) => [step.key, step.page])).toEqual([
      ["offer", "assistant/knowledge"],
      ["knowledge", "assistant/knowledge"],
      ["messages", "inbox"],
    ]);
  });
});
