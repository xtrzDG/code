/**
 * A guide as GET …/setup reports it, for tests of what reads it: nothing
 * done after the launch, nothing listening.
 */

import type { Schema } from "@/api/types";

type SetupGuideView = Schema<"SetupGuideView">;
type StepCode = Schema<"SetupStepCode">;
type Status = Schema<"SetupStepStatus">;

const AFTER_LAUNCH: readonly StepCode[] = ["phone_test", "second_channel", "share"];

export function guideFixture(
  statuses: Partial<Record<StepCode, Status>> = {},
  extra: Partial<SetupGuideView> = {},
): SetupGuideView {
  return {
    steps_after_launch: AFTER_LAUNCH.map((code) => ({
      code,
      status: statuses[code] ?? "todo",
      is_required: false,
      title: code,
      description: code,
      minutes: 2,
      action: { target: code === "share" ? "share" : code === "phone_test" ? "phone_test" : "channels", label: code },
      missing: [],
    })),
    next_step: null,
    next_action: { target: "overview", label: "Overview" },
    percent: 70,
    minutes_left: 10,
    is_complete: false,
    is_dismissed: false,
    is_phone_check_listening: false,
    phone_check_until: null,
    phone_tested_at: null,
    ...extra,
  };
}
