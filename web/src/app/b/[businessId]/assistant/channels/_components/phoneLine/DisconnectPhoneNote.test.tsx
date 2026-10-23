import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { answerGet, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business } from "../../../../settings/_lib/settingsFixtures";
import type { PhoneLineView, RentedPhoneNumber } from "../../_lib/phoneLine";
import { numberInText } from "../../_lib/phoneLine";
import { DisconnectPhoneNote } from "./DisconnectPhoneNote";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn() } }));

const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const LINE: PhoneLineView = {
  business_id: business.id,
  are_numbers_self_serve: true,
  self_serve_countries: ["US"],
  default_country_code: "US",
};
const RENTED: RentedPhoneNumber = {
  phone_number: "+15125550142",
  display_number: "+1 512-555-0142",
  country_code: "US",
  number_type: "local",
  locality: "Austin",
  monthly_price: { money: { amount_minor: 500, currency_code: "GEL" }, text: "5.00 ₾", is_estimated: false },
  status: "active",
  is_attached: true,
  has_answering_agent: true,
  rented_at: 1,
};

function renderNote(line: PhoneLineView) {
  answerGet(() => ok(line));
  renderInLocale(
    <BusinessProvider business={business} me={me}>
      <DisconnectPhoneNote />
    </BusinessProvider>,
  );
}

describe("what turning the phone channel off means", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.GET).mockReset();
  });

  it("warns that a rented number goes back to the carrier", async () => {
    const { t } = textsIn("en");
    renderNote({ ...LINE, rented_number: RENTED });

    expect(
      await screen.findByText(t("phoneNumbers.panel.disconnectReleases", { number: numberInText("+1 512-555-0142") })),
    ).toBeTruthy();
    expect(screen.queryByText(t("channels.disconnectPhoneNote"))).toBeNull();
  });

  it("speaks of call forwarding when the business rents no number", async () => {
    const { t } = textsIn("en");
    renderNote(LINE);

    expect(await screen.findByText(t("channels.disconnectPhoneNote"))).toBeTruthy();
  });
});
