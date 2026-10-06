import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { answerGet, failure, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import type { ErrorBudget } from "../../_lib/errorBudget";
import { ErrorBudgetCard } from "./ErrorBudgetCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const HOUR = 3_600_000_000;
const SINCE = Date.UTC(2026, 8, 8, 12) * 1000;

const budget: ErrorBudget = {
  objectives: [
    {
      series: "api_availability",
      objective: 0.999,
      events: 120_000,
      good_events: 119_940,
      budget_left_permille: 500,
      burn_rate_last_hour_percent: 1500,
    },
    {
      series: "inbound_answered",
      objective: 0.995,
      events: 6200,
      good_events: 6190,
      budget_left_permille: 968,
      burn_rate_last_hour_percent: 0,
    },
  ],
  latency: { target_ms: 15_000, last_hour_p95_ms: 4200, hours_over_target: 3, measured_hours: 640 },
  measured_since: SINCE,
  measured_until: SINCE + 672 * HOUR,
};

/** The budget figures count up once seen; jsdom has no IntersectionObserver. */
class NeverSeen {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

describe("ErrorBudgetCard: what is left of each SLO's budget", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.stubGlobal("IntersectionObserver", NeverSeen);
  });

  it.each(["en", "ru", "ka"] as const)("shows both budgets and the answer p95 in %s", async (locale) => {
    const { t } = textsIn(locale);
    answerGet(() => ok(budget));
    renderInLocale(<ErrorBudgetCard />, { locale });

    const answered = await screen.findByRole("meter", {
      name: t("adminSystem.errorBudget.meterLabel", { name: t("adminSystem.errorBudget.objectives.inbound_answered") }),
    });
    const api = screen.getByRole("meter", {
      name: t("adminSystem.errorBudget.meterLabel", { name: t("adminSystem.errorBudget.objectives.api_availability") }),
    });
    expect(answered.getAttribute("aria-valuenow")).toBe("97");
    expect(api.getAttribute("aria-valuenow")).toBe("50");
    expect(screen.getByText(t("adminSystem.errorBudget.states.success"))).toBeTruthy();
    expect(screen.getByRole("region", { name: t("adminSystem.errorBudget.latency.title") })).toBeTruthy();
  });

  it("says when the measured hours held no event instead of counting 0 of 0", async () => {
    const { t } = textsIn("en");
    const quiet: ErrorBudget = {
      ...budget,
      objectives: budget.objectives.map((objective) => ({ ...objective, events: 0, good_events: 0 })),
      latency: { ...budget.latency, last_hour_p95_ms: null },
    };
    answerGet(() => ok(quiet));
    renderInLocale(<ErrorBudgetCard />);

    expect(await screen.findByText(t("adminSystem.errorBudget.noEvents.inbound_answered"))).toBeTruthy();
    expect(screen.getByText(t("adminSystem.errorBudget.noEvents.api_availability"))).toBeTruthy();
    expect(screen.getByText(t("adminSystem.errorBudget.latency.noLastHour"))).toBeTruthy();
    expect(screen.queryByText(/0 of 0/)).toBeNull();
  });

  it("says so before the first hourly row", async () => {
    const { t } = textsIn("en");
    answerGet(() => ok({ ...budget, measured_since: null, measured_until: null }));
    renderInLocale(<ErrorBudgetCard />);

    expect(await screen.findByText(t("adminSystem.errorBudget.noRows"))).toBeTruthy();
    expect(screen.queryByRole("meter")).toBeNull();
  });

  it("stays hidden from an admin who may not see operations", async () => {
    answerGet(() => failure(403, { error: "forbidden", message: "No." }));
    const { container } = renderInLocale(<ErrorBudgetCard />);

    await vi.waitFor(() => expect(vi.mocked(api.GET)).toHaveBeenCalled());
    await vi.waitFor(() => expect(container.textContent).toBe(""));
  });
});
