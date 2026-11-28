import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { queryCache } from "@/api/queryCache";
import type { CurrentUserView, Schema } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { answerGet, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business } from "../../../settings/_lib/settingsFixtures";
import { CallForwardingCard } from "./CallForwardingCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn() } }));

const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const code = (condition: Schema<"CallForwardingCondition">, dial_code: string) => ({ condition, dial_code, description: `${condition} calls` });

/** A US business's guide (+1 212-555-0123): carriers first, the standard codes for the rest. */
const US_GUIDE = {
  business_id: business.id,
  country_code: "US",
  display_language: "en",
  assistant_phone_number: "+12125550123",
  assistant_phone_number_display: "+1 212-555-0123",
  codes: [code("no_answer", "**61*12125550123#"), code("cancel_all", "##002#")],
  carriers: [
    {
      carrier_name: "Verizon",
      codes: [],
      note: "Verizon has one code for busy and unanswered calls.",
      star_codes: [
        { condition: "cancel_all", dial_code: "*73", description: "Switch call forwarding off." },
        { condition: "no_answer_or_busy", dial_code: "*712125550123", description: "Unanswered and busy calls." },
      ],
    },
    { carrier_name: "T-Mobile", codes: [code("no_answer", "**61*12125550123#")], note: null },
  ],
  steps: ["Open your carrier below and dial its codes one at a time."],
  notes: ["Codes differ by carrier."],
  is_carrier_choice_needed: true,
} as unknown as Schema<"CallForwardingInstructions">;

function renderCard(guide: Schema<"CallForwardingInstructions">) {
  answerGet((path) => (path === "/v1/businesses/{business_id}/call-forwarding-instructions" ? ok(guide) : pending()));
  renderInLocale(
    <BusinessProvider business={business} me={me}>
      <CallForwardingCard />
    </BusinessProvider>,
  );
}

const headings = () => screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent);

describe("CallForwardingCard", () => {
  const { t } = textsIn("en");
  beforeEach(() => queryCache.clear());

  it("puts the carriers first where each takes its own codes, then the standard codes for the others", async () => {
    renderCard(US_GUIDE);

    await screen.findByText("+1 212-555-0123");
    expect(headings()).toEqual([
      t("channels.forwarding.stepsTitle"),
      t("channels.forwarding.chooseCarrierTitle"),
      t("channels.forwarding.otherCarriersTitle"),
      t("channels.forwarding.notesTitle"),
    ]);
    // Verizon has star codes only: forwarding first, then switching off, each with its label and a dial link.
    const verizon = screen.getByText("Verizon").closest("details")!;
    const rows = within(verizon).getAllByRole("listitem");
    expect(rows.map((row) => row.querySelector("code")?.textContent)).toEqual(["*712125550123", "*73"]);
    expect(within(rows[0]!).getByText(t("channels.forwarding.starCondition.no_answer_or_busy"))).toBeTruthy();
    expect(within(rows[0]!).getByRole("link", { name: t("channels.forwarding.dialLabel", { code: "*712125550123" }) }).getAttribute("href")).toBe(
      "tel:*712125550123",
    );
  });

  it("keeps the standard codes first elsewhere, and an API without the new fields reads as before", async () => {
    const { is_carrier_choice_needed: _, ...older } = US_GUIDE;
    renderCard({ ...older, carriers: [{ carrier_name: "TIM", codes: [code("no_answer", "**61*+390612345678#")], note: null }] } as never);

    await screen.findByText("+1 212-555-0123");
    expect(headings()).toEqual([
      t("channels.forwarding.stepsTitle"),
      t("channels.forwarding.codesTitle"),
      t("channels.forwarding.carriersTitle"),
      t("channels.forwarding.notesTitle"),
    ]);
    expect(within(screen.getByText("TIM").closest("details")!).getByText("**61*+390612345678#")).toBeTruthy();
  });
});
