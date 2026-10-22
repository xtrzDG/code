import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { CountryListItem, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { answerGet, failure, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business } from "../../../../settings/_lib/settingsFixtures";
import type { PhoneLineView, PhoneNumberOffers, RentedPhoneNumber } from "../../_lib/phoneLine";
import { PhoneNumberPanel } from "./PhoneNumberPanel";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));

const LINE_PATH = "/v1/businesses/{business_id}/phone-line";
const OFFERS_PATH = "/v1/businesses/{business_id}/phone-line/offers";
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const EMPTY_LINE: PhoneLineView = {
  business_id: business.id,
  are_numbers_self_serve: true,
  self_serve_countries: ["US"],
  default_country_code: "US",
};
const PRICE = { money: { amount_minor: 500, currency_code: "GEL" }, text: "5.00 ₾", is_estimated: false };
const AUSTIN: PhoneNumberOffers = {
  country_code: "US",
  number_type: "local",
  availability: "self_serve",
  monthly_price: PRICE,
  offers: [{ phone_number: "+15125550142", display_number: "+1 512-555-0142", locality: "Austin", region: "TX" }],
};
const RENTED: RentedPhoneNumber = {
  phone_number: "+15125550142",
  display_number: "+1 512-555-0142",
  country_code: "US",
  number_type: "local",
  locality: "Austin",
  monthly_price: PRICE,
  status: "active",
  is_attached: true,
  rented_at: 1,
};
const COUNTRIES = {
  display_language: "en",
  countries: [
    { country_code: "GE", display_name: "Georgia", english_name: "Georgia", calling_code: 995, onboarding_status: "supported" },
    { country_code: "US", display_name: "United States", english_name: "United States", calling_code: 1, onboarding_status: "supported" },
  ] as CountryListItem[],
};

function answer(line: PhoneLineView, offers: PhoneNumberOffers = AUSTIN) {
  answerGet((path) => {
    if (path === LINE_PATH) return ok(line);
    if (path === OFFERS_PATH) return ok(offers);
    if (path === "/v1/catalog/countries") return ok(COUNTRIES);
    return pending();
  });
}

function renderPanel(canManage = true, onChanged = vi.fn()) {
  renderInLocale(
    <BusinessProvider business={business} me={me}>
      <PhoneNumberPanel canManage={canManage} onChanged={onChanged} />
    </BusinessProvider>,
  );
  return onChanged;
}

describe("the phone card's number from us", () => {
  const { t } = textsIn("en");

  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.GET).mockReset();
    vi.mocked(api.POST).mockReset();
    vi.mocked(api.DELETE).mockReset();
  });

  it("finds numbers, shows the monthly price and takes one after confirming", async () => {
    answer(EMPTY_LINE);
    vi.mocked(api.POST).mockImplementation((() => ok(RENTED)) as never);
    const onChanged = renderPanel();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: t("phoneNumbers.panel.getNumber") }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(t("phoneNumbers.dialog.city"), { exact: false }), "Austin");
    await user.click(within(dialog).getByRole("button", { name: t("phoneNumbers.dialog.search") }));

    expect(await within(dialog).findByText("+1 512-555-0142")).toBeTruthy();
    expect(within(dialog).getByText(/a month for any of them/)).toBeTruthy();
    const offersCall = (vi.mocked(api.GET).mock.calls as unknown[][]).find(([path]) => path === OFFERS_PATH);
    const query = offersCall?.[1] as { params: { query: Record<string, string> } };
    expect(query.params.query).toMatchObject({ country: "US", number_type: "local", city: "Austin" });

    await user.click(within(dialog).getByRole("button", { name: t("phoneNumbers.offers.takeLabel", { number: "+1 512-555-0142" }) }));
    await user.click(within(dialog).getByRole("button", { name: t("phoneNumbers.confirm.take") }));

    const [path, init] = vi.mocked(api.POST).mock.calls[0]! as [string, { body: unknown }];
    expect(path).toBe("/v1/businesses/{business_id}/phone-line/number");
    expect(init.body).toEqual({
      phone_number: "+15125550142",
      number_type: "local",
      monthly_price: { amount_minor: 500, currency_code: "GEL" },
      locality: "Austin",
    });
    expect(onChanged).toHaveBeenCalledOnce();
  });

  it("asks our team where the country wants the business's documents", async () => {
    answer({ ...EMPTY_LINE, default_country_code: "GE" }, { country_code: "GE", number_type: "local", availability: "requires_documents" });
    vi.mocked(api.POST).mockImplementation((() =>
      ok({ country_code: "GE", number_type: "local", status: "open", requested_at: 1 })) as never);
    renderPanel();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: t("phoneNumbers.panel.getNumber") }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: t("phoneNumbers.dialog.search") }));
    expect(await within(dialog).findByText(t("phoneNumbers.request.requires_documents"))).toBeTruthy();
    await user.click(within(dialog).getByRole("button", { name: t("phoneNumbers.request.ask") }));

    const [path, init] = vi.mocked(api.POST).mock.calls[0]! as [string, { body: unknown }];
    expect(path).toBe("/v1/businesses/{business_id}/phone-line/request");
    expect(init.body).toEqual({ country_code: "GE", number_type: "local" });
  });

  it("words a number someone else has just taken", async () => {
    answer(EMPTY_LINE);
    vi.mocked(api.POST).mockImplementation((() =>
      failure(409, {
        error: "conflict",
        message: "This number is no longer available.",
        reasons: [{ code: "number_taken", message: "Search again.", details: [] }],
      })) as never);
    renderPanel();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: t("phoneNumbers.panel.getNumber") }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: t("phoneNumbers.dialog.search") }));
    await user.click(await within(dialog).findByRole("button", { name: t("phoneNumbers.offers.takeLabel", { number: "+1 512-555-0142" }) }));
    await user.click(within(dialog).getByRole("button", { name: t("phoneNumbers.confirm.take") }));

    expect(await within(dialog).findByText(t("phoneNumbers.refusals.numberTaken"))).toBeTruthy();
  });

  it("shows the rented number, its price and that it answers", async () => {
    answer({ ...EMPTY_LINE, rented_number: RENTED });
    renderPanel();

    expect(await screen.findByText("+1 512-555-0142")).toBeTruthy();
    expect(screen.getByText(t("phoneNumbers.panel.answering"))).toBeTruthy();
    expect(screen.getByText(/a month/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("phoneNumbers.panel.getNumber") })).toBeNull();
  });

  it("shows an open request and cancels it", async () => {
    answer({
      ...EMPTY_LINE,
      open_request: { country_code: "GE", number_type: "local", city: "Batumi", status: "open", requested_at: 1 },
    });
    vi.mocked(api.DELETE).mockImplementation((() => ok(undefined)) as never);
    renderPanel();
    const user = userEvent.setup();

    expect(await screen.findByText(/near Batumi/)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: t("phoneNumbers.panel.cancelRequest") }));

    expect(vi.mocked(api.DELETE).mock.calls[0]?.[0]).toBe("/v1/businesses/{business_id}/phone-line/request");
  });

  it("tells staff only an owner takes a number", async () => {
    answer(EMPTY_LINE);
    renderPanel(false);

    expect(await screen.findByText(t("phoneNumbers.panel.ownerOnly"))).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("phoneNumbers.panel.getNumber") })).toBeNull();
  });
});
