import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { queryCache } from "@/api/queryCache";
import type { CurrentUserView } from "@/api/types";
import { business } from "@/app/b/[businessId]/settings/_lib/settingsFixtures";
import { BusinessProvider } from "@/components/business/BusinessContext";
import type { Locale } from "@/i18n/config";
import type { AnswerToImprove } from "@/lib/teaching";
import { answerGet, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { AnswersToImproveCard } from "./AnswersToImproveCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const AT = Date.UTC(2026, 9, 1, 9, 30) * 1000;

const byTeam: AnswerToImprove = {
  kind: "bad_rating",
  at: AT,
  conversation_id: "conversation_team",
  message_id: "message_team",
  customer_message: "Do you have parking?",
  answer: "We are open until ten.",
  rating_by: "team",
  rating_reason: "tone",
};

const byCustomer: AnswerToImprove = {
  kind: "bad_rating",
  at: AT,
  conversation_id: "conversation_widget",
  message_id: "message_widget",
  customer_message: "A table for two tomorrow at eight",
  answer: "Booked for Friday.",
  rating_by: "customer",
  rating_reason: "wrong_info",
};

function renderCard(items: AnswerToImprove[], locale: Locale = "en") {
  answerGet(() => ok({ items, bad_rating_count: items.length, unanswered_count: 0 }));
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <AnswersToImproveCard />
    </BusinessProvider>,
    { locale },
  );
}

describe("AnswersToImproveCard: whose bad rating it is", () => {
  beforeEach(() => {
    queryCache.clear();
  });

  it("marks only the answer the customer rated in the website chat", async () => {
    const { t } = textsIn("en");
    renderCard([byTeam, byCustomer]);

    const customerRow = (await screen.findByText(byCustomer.customer_message ?? "")).closest("li");
    const teamRow = screen.getByText(byTeam.customer_message ?? "").closest("li");
    expect(customerRow).not.toBeNull();
    expect(teamRow).not.toBeNull();

    expect(within(customerRow as HTMLElement).getByText(t("teaching.improve.byCustomer"))).toBeTruthy();
    expect(within(customerRow as HTMLElement).getByText(t("teaching.rating.reasons.wrong_info"))).toBeTruthy();
    expect(within(teamRow as HTMLElement).queryByText(t("teaching.improve.byCustomer"))).toBeNull();
    expect(screen.getAllByText(t("teaching.improve.badRating"))).toHaveLength(2);
  });

  it("says so in the cabinet's language", async () => {
    const { t } = textsIn("ka");
    renderCard([byCustomer], "ka");

    expect(await screen.findByText(t("teaching.improve.byCustomer"))).toBeTruthy();
    expect(screen.queryByText(textsIn("en").t("teaching.improve.byCustomer"))).toBeNull();
  });
});
