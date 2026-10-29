import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AutotestRunComparison } from "@/lib/assistant/autotestComparison";
import { renderInLocale, textsIn } from "@/test/render";

import { RunComparison } from "./RunComparison";

type OutcomeChange = AutotestRunComparison["new_failures"][number];

const chatFailure: OutcomeChange = {
  scenario_key: "booking__ka",
  kind: "booking",
  language: "ka",
  outcome: "failed",
  baseline_outcome: "passed",
  check_codes: [],
  channel: null,
};
const phoneFailure: OutcomeChange = { ...chatFailure, scenario_key: "phone__booking__ka", channel: "phone" };

function comparison(): AutotestRunComparison {
  return {
    baseline_run_id: "autotest_run_1",
    baseline_version_id: "assistant_version_1",
    baseline_version_number: 3,
    baseline_average_score: null,
    average_score_change: null,
    shared_scenario_count: 2,
    new_failures: [chatFailure, phoneFailure],
    fixed: [],
    score_changes: [
      { scenario_key: "phone__booking__ka", kind: "booking", language: "ka", channel: "phone", average_score: 2.5, baseline_average_score: 5, change: -2.5 },
    ],
    criterion_changes: [],
  };
}

describe("RunComparison: a voice check change names the phone call", () => {
  it.each(["en", "it"] as const)("tells the chat and the call apart in %s", (locale) => {
    const { t } = textsIn(locale);
    renderInLocale(<RunComparison comparison={comparison()} />, { locale });

    const phoneCall = t("assistant.autotests.phoneCall");
    const failures = screen.getAllByText(new RegExp(t("assistant.autotests.kinds.booking")));
    const names = failures.map((element) => element.textContent ?? "");
    // The chat failure, the phone failure and the phone score drop.
    expect(names).toHaveLength(3);
    expect(names.filter((name) => name.includes(phoneCall))).toHaveLength(2);
    expect(new Set(names).size).toBe(2);
  });
});
