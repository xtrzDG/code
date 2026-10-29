import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderInLocale, textsIn } from "@/test/render";

import { circuitProvider, openCircuitCount, type CircuitSummary } from "../../_lib/circuits";
import { CircuitsCard } from "./CircuitsCard";

const meta: CircuitSummary = {
  circuit: "provider:meta",
  state: "open",
  workers_not_closed: 2,
  workers_reporting: 3,
  recent_failures: 0,
  opened_at: Date.UTC(2026, 9, 22, 9, 0) * 1000,
};
const model: CircuitSummary = {
  circuit: "openai:gpt-5-mini",
  state: "closed",
  workers_not_closed: 0,
  workers_reporting: 3,
  recent_failures: 2,
  opened_at: null,
};

describe("CircuitsCard: the providers' circuit breakers", () => {
  it.each(["en", "it"] as const)("names providers and states in %s", async (locale) => {
    const { t } = textsIn(locale);
    renderInLocale(<CircuitsCard circuits={[meta, model]} />, { locale });

    const table = await screen.findByRole("table", { name: t("providerCircuits.title") });
    const rows = within(table).getAllByRole("row");
    const metaRow = rows.find((row) => within(row).queryByText(t("providerCircuits.providers.meta")) !== null);
    const modelRow = rows.find((row) => within(row).queryByText(model.circuit) !== null);
    if (!metaRow || !modelRow) throw new Error("both circuits are listed");
    expect(within(metaRow).getByText(t("providerCircuits.states.open"))).toBeTruthy();
    expect(within(modelRow).getByText(t("providerCircuits.states.closed"))).toBeTruthy();
    expect(within(modelRow).getByText("—")).toBeTruthy();
  });

  it("says so when no worker reported its circuits", () => {
    const { t } = textsIn("en");
    renderInLocale(<CircuitsCard circuits={[]} />);

    expect(screen.getByText(t("providerCircuits.none"))).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });
});

describe("circuits", () => {
  it("knows the provider of a provider circuit only", () => {
    expect(circuitProvider("provider:meta")).toBe("meta");
    expect(circuitProvider("provider:platform_bot")).toBe("platform_bot");
    expect(circuitProvider("provider:elevenlabs")).toBe("elevenlabs");
    expect(circuitProvider("provider:pigeon")).toBeNull();
    expect(circuitProvider("anthropic:claude-sonnet-5-5")).toBeNull();
  });

  it("counts the circuits that are not closed", () => {
    expect(openCircuitCount([meta, model, { ...model, circuit: "provider:smtp", state: "half_open" }])).toBe(2);
    expect(openCircuitCount([])).toBe(0);
  });
});
