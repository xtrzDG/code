import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AutotestScenarioResult } from "@/lib/assistant/autotests";
import { renderInLocale, textsIn } from "@/test/render";

import { ScenarioResult } from "./ScenarioResult";

function result(channel: AutotestScenarioResult["channel"]): AutotestScenarioResult {
  return {
    scenario_key: channel === "phone" ? "phone__booking__ka" : "booking__ka",
    kind: "booking",
    language: "ka",
    outcome: "passed",
    scores: [{ criterion: "booking_data", score: 5 }],
    judge_notes: [],
    check_notes: [],
    check_codes: [],
    transcript: [],
    cost_micro_usd: 0,
    channel,
  };
}

describe("ScenarioResult: a voice check says it was a phone call", () => {
  it.each(["en", "ru", "ka", "he", "de"] as const)("labels the simulated call in %s", (locale) => {
    const { t } = textsIn(locale);
    renderInLocale(
      <ul>
        <ScenarioResult result={result("phone")} />
      </ul>,
      { locale },
    );

    const label = screen.getByText(t("assistant.autotests.phoneCall"), { exact: false });
    expect(label.getAttribute("title")).toBe(t("assistant.autotests.phoneCallHint"));
  });

  it("leaves a test chat as it was", () => {
    const { t } = textsIn("en");
    renderInLocale(
      <ul>
        <ScenarioResult result={result(null)} />
      </ul>,
    );

    expect(screen.queryByText(t("assistant.autotests.phoneCall"), { exact: false })).toBeNull();
  });
});
