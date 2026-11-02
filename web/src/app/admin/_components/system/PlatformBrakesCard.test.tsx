import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { answerGet, failure, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import {
  brakeState,
  hasMismatches,
  type PaymentReconciliation,
  type PlatformBrakes,
} from "../../_lib/platformBrakes";
import { PaymentReconciliationCard } from "./PaymentReconciliationCard";
import { PlatformBrakesCard } from "./PlatformBrakesCard";

vi.mock("@/api/client", () => ({
  api: {
    GET: vi.fn(),
    POST: vi.fn(),
    PUT: vi.fn(),
    PATCH: vi.fn(),
    DELETE: vi.fn(),
  },
}));

const running: PlatformBrakes = {
  is_paused: false,
  reason: null,
  changed_by: null,
  changed_at: null,
  stop_percent: 100,
  budget_used_percent: 42,
  brake: null,
};
const paused: PlatformBrakes = {
  ...running,
  is_paused: true,
  reason: "Prompt injection wave, stop now",
  changed_by: "user_1",
  changed_at: Date.UTC(2026, 10, 2, 9, 0) * 1000,
  brake: "paused",
};
const reconciliation: PaymentReconciliation = {
  day: "2026-11-02",
  ran_at: Date.UTC(2026, 10, 2, 0, 5) * 1000,
  checked_count: 12,
  unreadable_count: 1,
  mismatches: [
    {
      payment_order_id: "payment_order_1",
      business_id: "business_7",
      business_name: "Trattoria del Sole",
      provider: "flitt",
      recorded_status: "created",
      provider_status: "approved",
      kind: "paid_at_provider",
    },
  ],
};

describe("PlatformBrakesCard: the global pause and the budget stop", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.PUT).mockReset();
  });

  it.each(["en", "it"] as const)(
    "shows a paused platform with its reason in %s",
    async (locale) => {
      const { t } = textsIn(locale);
      answerGet(() => ok(paused));
      renderInLocale(<PlatformBrakesCard canPause={false} />, { locale });

      const card = await screen.findByRole("region", {
        name: t("platformBrakes.brakes.title"),
      });
      expect(
        await within(card).findByText(t("platformBrakes.brakes.states.paused")),
      ).toBeTruthy();
      expect(within(card).getByText(paused.reason ?? "")).toBeTruthy();
      // Only a SUPER admin gets the button.
      expect(
        within(card).queryByRole("button", {
          name: t("platformBrakes.brakes.resume"),
        }),
      ).toBeNull();
    },
  );

  it("lets a SUPER admin pause every assistant with a reason", async () => {
    const { t } = textsIn("en");
    answerGet(() => ok(running));
    vi.mocked(api.PUT).mockImplementation((() => ok(paused)) as never);
    renderInLocale(<PlatformBrakesCard canPause />);

    fireEvent.click(
      await screen.findByRole("button", {
        name: t("platformBrakes.brakes.pause"),
      }),
    );
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByRole("textbox"), {
      target: { value: "  Prompt injection wave, stop now " },
    });
    fireEvent.click(
      within(dialog).getByRole("button", {
        name: t("platformBrakes.brakes.pause"),
      }),
    );

    await waitFor(() => expect(api.PUT).toHaveBeenCalledTimes(1));
    expect(vi.mocked(api.PUT).mock.calls[0]).toEqual([
      "/v1/admin/platform/pause",
      { body: { is_paused: true, reason: "Prompt injection wave, stop now" } },
    ]);
  });

  it("is hidden from an admin whose role may not see operations", async () => {
    answerGet(() =>
      failure(403, {
        detail: "Your platform admin role does not include this.",
      }),
    );
    const { container } = renderInLocale(
      <PlatformBrakesCard canPause={false} />,
    );

    await waitFor(() => expect(api.GET).toHaveBeenCalled());
    await waitFor(() => expect(container.textContent).toBe(""));
  });
});

describe("PaymentReconciliationCard: payments that differ from Flitt and Stripe", () => {
  beforeEach(() => {
    queryCache.clear();
  });

  it.each(["en", "it"] as const)(
    "lists each mismatch with its client in %s",
    async (locale) => {
      const { t } = textsIn(locale);
      answerGet(() => ok(reconciliation));
      renderInLocale(<PaymentReconciliationCard />, { locale });

      const table = await screen.findByRole("table", {
        name: t("platformBrakes.reconciliation.title"),
      });
      expect(within(table).getByText("Trattoria del Sole")).toBeTruthy();
      expect(
        within(table).getByText(
          t("platformBrakes.reconciliation.kinds.paid_at_provider"),
        ),
      ).toBeTruthy();
      expect(
        within(table).getByText(
          t("platformBrakes.reconciliation.statuses.approved"),
        ),
      ).toBeTruthy();
    },
  );

  it("says so when every payment matches", async () => {
    const { t } = textsIn("en");
    answerGet(() => ok({ ...reconciliation, mismatches: [] }));
    renderInLocale(<PaymentReconciliationCard />);

    expect(
      await screen.findByText(t("platformBrakes.reconciliation.allMatch")),
    ).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });
});

describe("platformBrakes", () => {
  it("tells running, paused and stopped apart", () => {
    expect(brakeState(running)).toBe("running");
    expect(brakeState(paused)).toBe("paused");
    expect(brakeState({ ...running, brake: "budget_stop" })).toBe("stopped");
    expect(hasMismatches(reconciliation)).toBe(true);
    expect(hasMismatches({ mismatches: [] })).toBe(false);
  });
});
