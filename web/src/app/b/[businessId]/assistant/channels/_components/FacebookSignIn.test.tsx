import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { failure, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business } from "../../../settings/_lib/settingsFixtures";
import type { FacebookLoginResponse, FacebookSdk } from "../_lib/facebookSdk";
import type { MetaChannel } from "../_lib/metaSignIn";
import { FacebookSignIn } from "./FacebookSignIn";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));

const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const STATE = "s".repeat(43);
const CHANNEL = { channel: "whatsapp", status: "connected", account_id: "106540352242923" };
const t = textsIn("en").t;

let login: ReturnType<typeof vi.fn<(callback: (response: FacebookLoginResponse) => void, options: object) => void>>;

function startView(purpose: "whatsapp" | "pages") {
  return {
    purpose,
    state: STATE,
    app_id: "1234567890",
    graph_api_version: "v23.0",
    configuration_id: purpose === "whatsapp" ? "987654321" : null,
    permissions: purpose === "pages" ? ["pages_show_list"] : [],
    expires_at: 0,
  };
}

function show(kind: MetaChannel, onConnected = vi.fn()) {
  renderInLocale(
    <BusinessProvider business={business} me={me}>
      <FacebookSignIn kind={kind} onConnected={onConnected} />
    </BusinessProvider>,
  );
  return onConnected;
}

/** Facebook's window answering: the signup window's message first, then the login callback. */
function facebookAnswers(code: string | null, message?: { origin: string; data: unknown }) {
  const callback = login.mock.calls.at(-1)?.[0];
  act(() => {
    if (message) {
      window.dispatchEvent(new MessageEvent("message", message));
    }
    callback?.(code ? { authResponse: { code } } : { status: "unknown" });
  });
}

beforeEach(() => {
  queryCache.clear();
  login = vi.fn();
  const sdk: FacebookSdk = { init: vi.fn(), login };
  window.FB = sdk;
  vi.mocked(api.POST).mockReset();
  vi.mocked(api.PUT).mockReset();
});

afterEach(() => {
  delete window.FB;
});

describe("Continue with Facebook", () => {
  it("connects WhatsApp with the code and the ids its signup window reported", async () => {
    vi.mocked(api.POST).mockImplementation(((path: string) =>
      path.endsWith("/meta/sign-in") ? ok(startView("whatsapp")) : ok(CHANNEL)) as never);
    const onConnected = show("whatsapp");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: t("metaConnect.continue") }));
    await user.click(await screen.findByRole("button", { name: t("metaConnect.openWindow") }));
    expect(login.mock.calls[0]?.[1]).toMatchObject({ config_id: "987654321", response_type: "code" });
    facebookAnswers("AQB-test-code-0000", {
      origin: "https://www.facebook.com",
      data: JSON.stringify({ type: "WA_EMBEDDED_SIGNUP", event: "FINISH", data: { waba_id: "1022", phone_number_id: "1065" } }),
    });

    await waitFor(() => expect(onConnected).toHaveBeenCalledWith(CHANNEL));
    expect(vi.mocked(api.POST).mock.calls[1]?.[1]).toMatchObject({
      body: { state: STATE, code: "AQB-test-code-0000", whatsapp_business_account_id: "1022", phone_number_id: "1065" },
    });
  });

  it("never takes ids from another site's message", async () => {
    vi.mocked(api.POST).mockImplementation(((path: string) =>
      path.endsWith("/meta/sign-in") ? ok(startView("whatsapp")) : ok(CHANNEL)) as never);
    const onConnected = show("whatsapp");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: t("metaConnect.continue") }));
    await user.click(await screen.findByRole("button", { name: t("metaConnect.openWindow") }));
    facebookAnswers("AQB-test-code-0000", {
      origin: "https://evilfacebook.com",
      data: JSON.stringify({ type: "WA_EMBEDDED_SIGNUP", event: "FINISH", data: { waba_id: "666", phone_number_id: "666" } }),
    });

    await waitFor(() => expect(onConnected).toHaveBeenCalled());
    expect(vi.mocked(api.POST).mock.calls[1]?.[1]).toMatchObject({ body: { state: STATE, code: "AQB-test-code-0000" } });
    expect(JSON.stringify(vi.mocked(api.POST).mock.calls[1]?.[1])).not.toContain("666");
  });

  it("says so when the window closed early, and opens it again", async () => {
    vi.mocked(api.POST).mockImplementation((() => ok(startView("whatsapp"))) as never);
    show("whatsapp");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: t("metaConnect.continue") }));
    await user.click(await screen.findByRole("button", { name: t("metaConnect.openWindow") }));
    facebookAnswers(null);

    expect(await screen.findByText(t("metaConnect.notices.cancelled"))).toBeTruthy();
    await user.click(screen.getByRole("button", { name: t("metaConnect.openWindow") }));
    expect(login).toHaveBeenCalledTimes(2);
    // The same sign-in: no second start, no code sent.
    expect(api.POST).toHaveBeenCalledTimes(1);
  });

  it("names Meta's refusal in the owner's words", async () => {
    vi.mocked(api.POST).mockImplementation(((path: string) =>
      path.endsWith("/meta/sign-in")
        ? ok(startView("whatsapp"))
        : failure(409, {
            error: "conflict",
            message: "PIN",
            reasons: [{ code: "whatsapp_pin_mismatch", message: "PIN", details: [] }],
          })) as never);
    show("whatsapp");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: t("metaConnect.continue") }));
    await user.click(await screen.findByRole("button", { name: t("metaConnect.openWindow") }));
    facebookAnswers("AQB-test-code-0000");

    expect(await screen.findByText(t("metaConnect.refusals.whatsapp_pin_mismatch"))).toBeTruthy();
  });

  it("lets Instagram pick only a page with an Instagram account", async () => {
    const pages = [
      { page_id: "4410001", name: "Cafe Ezo", has_instagram: false },
      { page_id: "4410002", name: "Cafe Ezo Batumi", has_instagram: true, instagram_username: "cafe.ezo" },
    ];
    vi.mocked(api.POST).mockImplementation(((path: string) =>
      path.endsWith("/meta/sign-in") ? ok(startView("pages")) : ok({ pages, expires_at: 0 })) as never);
    vi.mocked(api.PUT).mockImplementation((() => ok({ ...CHANNEL, channel: "instagram" })) as never);
    const onConnected = show("instagram");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: t("metaConnect.continue") }));
    await user.click(await screen.findByRole("button", { name: t("metaConnect.openWindow") }));
    expect(login.mock.calls[0]?.[1]).toMatchObject({ scope: "pages_show_list" });
    facebookAnswers("AQD-test-code-0000");

    const [withoutInstagram, withInstagram] = (await screen.findAllByRole("radio")) as HTMLInputElement[];
    expect(withoutInstagram?.disabled).toBe(true);
    expect(withInstagram?.checked).toBe(true);
    expect(screen.getByText(t("metaConnect.pages.noInstagram"))).toBeTruthy();
    expect(screen.getByText(t("metaConnect.pages.instagram", { username: "cafe.ezo" }))).toBeTruthy();
    await user.click(screen.getByRole("button", { name: t("metaConnect.pages.connect") }));

    await waitFor(() => expect(onConnected).toHaveBeenCalled());
    expect(vi.mocked(api.PUT).mock.calls[0]?.[1]).toMatchObject({
      params: { path: { business_id: business.id, channel: "instagram" } },
      body: { state: STATE, page_id: "4410002" },
    });
  });
});
