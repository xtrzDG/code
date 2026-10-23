/**
 * "Continue with Facebook" on the Channels page. Meta never answers in the
 * suite: the API's sign-in routes, Facebook's SDK (connect.facebook.net)
 * and its signup window (a frame of www.facebook.com that posts the
 * WA_EMBEDDED_SIGNUP message) are served by the test. What runs for real is
 * the page's policy: the SDK is admitted by the Channels page's Content
 * Security Policy (any violation fails the console-clean gate), its frame
 * too, and the page keeps its handle on Facebook's windows.
 */

import type { Page } from "@playwright/test";

import { expectStrictPolicy, policyViolations, watchPolicyViolations } from "./support/csp";
import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";

const STATE = "s".repeat(43);
const SDK = `
window.FB = {
  init: function (options) { window.__fbInit = options; },
  login: function (callback, options) {
    window.__fbLogin = options;
    window.addEventListener("message", function answer(event) {
      if (event.origin !== "https://www.facebook.com") return;
      window.removeEventListener("message", answer);
      setTimeout(function () { callback({ authResponse: { code: "AQB-e2e-code-0000" } }); }, 0);
    });
    var frame = document.createElement("iframe");
    frame.title = "Facebook";
    frame.src = "https://www.facebook.com/e2e-signup?purpose=" + (options.config_id ? "whatsapp" : "pages");
    document.body.appendChild(frame);
  },
};
if (window.fbAsyncInit) window.fbAsyncInit();
`;
const SIGNUP_WINDOW = `<!doctype html><script>
parent.postMessage(JSON.stringify({ type: "WA_EMBEDDED_SIGNUP", event: "FINISH",
  data: { waba_id: "102290129340398", phone_number_id: "106540352242923" } }), "*");
</script>`;

function channelView(businessId: string, channel: string, accountId: string) {
  return {
    id: "channel_5f0c6b1e-2a3d-4c5b-9e8f-7a6b5c4d3e2f",
    business_id: businessId,
    channel,
    status: "connected",
    account_id: accountId,
    has_credential: true,
    updated_at: Date.now() * 1000,
  };
}

/** Meta's side of the sign-in, served by the test; returns what the cabinet sent. */
async function serveMeta(page: Page, businessId: string) {
  const sent: { complete: unknown[]; pages: unknown[]; picked: unknown[]; starts: number } = {
    complete: [],
    pages: [],
    picked: [],
    starts: 0,
  };
  const base = `**/api/backend/v1/businesses/${businessId}/channels`;
  await page.route("https://connect.facebook.net/**", (route) =>
    route.fulfill({ contentType: "application/javascript", body: SDK, headers: { "access-control-allow-origin": "*" } }),
  );
  await page.route("https://www.facebook.com/**", (route) => route.fulfill({ contentType: "text/html", body: SIGNUP_WINDOW }));
  await page.route(`${base}/meta/sign-in`, (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: { whatsapp: true, pages: true, app_id: "1234567890", graph_api_version: "v23.0" } });
    }
    sent.starts += 1;
    const { purpose } = route.request().postDataJSON() as { purpose: string };
    return route.fulfill({
      status: 201,
      json: {
        purpose,
        state: STATE,
        app_id: "1234567890",
        graph_api_version: "v23.0",
        configuration_id: purpose === "whatsapp" ? "987654321" : null,
        permissions: purpose === "pages" ? ["pages_show_list", "pages_messaging"] : [],
        expires_at: (Date.now() + 15 * 60_000) * 1000,
      },
    });
  });
  await page.route(`${base}/whatsapp/embedded-signup`, (route) => {
    sent.complete.push(route.request().postDataJSON());
    return route.fulfill({ json: channelView(businessId, "whatsapp", "106540352242923") });
  });
  await page.route(`${base}/meta/pages`, (route) => {
    sent.pages.push(route.request().postDataJSON());
    return route.fulfill({
      json: {
        pages: [{ page_id: "4410001", name: "Salon Morgenrot", username: "salon.morgenrot", has_instagram: false }],
        expires_at: 0,
      },
    });
  });
  await page.route(`${base}/messenger/page`, (route) => {
    sent.picked.push(route.request().postDataJSON());
    return route.fulfill({ json: channelView(businessId, "messenger", "4410001") });
  });
  return sent;
}

const cardOf = (page: Page, channel: string) => page.getByRole("region", { name: channel, exact: true });

test("WhatsApp connects with Facebook's signup window on the Channels page", async ({ page, owner }) => {
  const sent = await serveMeta(page, owner.businessId);
  await watchPolicyViolations(page);
  const response = await page.goto(`/b/${owner.businessId}/assistant/channels`);
  const headers = response?.headers() ?? {};
  // Facebook's window reports back to this page; others still cannot reach it.
  expect(headers["cross-origin-opener-policy"]).toBe("same-origin-allow-popups");
  // The strict policy (nonce'd styles, Trusted Types) with Facebook's hosts only.
  expectStrictPolicy(headers["content-security-policy"] ?? "", "the Channels page");
  expect(headers["content-security-policy"]).toContain("https://connect.facebook.net");

  const whatsapp = en.channels.kinds.whatsapp;
  await cardOf(page, whatsapp).getByRole("button", { name: `${en.channels.connect} — ${whatsapp}` }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: en.metaConnect.continue }).click();
  // The click is still the owner's: Facebook's window opens without a second one.
  await expect(page.getByText(en.channels.connectedToast.replace("{channel}", whatsapp))).toBeVisible();
  await expect(dialog).toBeHidden();

  expect(sent.starts).toBe(1);
  expect(sent.complete).toEqual([
    { state: STATE, code: "AQB-e2e-code-0000", whatsapp_business_account_id: "102290129340398", phone_number_id: "106540352242923" },
  ]);
  expect(await page.evaluate(() => (window as unknown as { __fbLogin: { config_id: string } }).__fbLogin.config_id)).toBe("987654321");
  await expect(cardOf(page, whatsapp).getByText(en.channels.state.connected)).toBeVisible();
  // The SDK came in through the `facebook-sdk` Trusted Types policy; nothing was refused.
  expect(await page.locator("script[src^='https://connect.facebook.net/']").getAttribute("src")).toBe(
    "https://connect.facebook.net/en_US/sdk.js",
  );
  expect(await policyViolations(page), "Facebook's sign-in broke the policy").toEqual([]);
});

test("Messenger picks a Facebook page; the manual fields wait under a click", async ({ page, owner }) => {
  const sent = await serveMeta(page, owner.businessId);
  await watchPolicyViolations(page);
  await page.goto(`/b/${owner.businessId}/assistant/channels`);

  const messenger = en.channels.kinds.messenger;
  await cardOf(page, messenger).getByRole("button", { name: `${en.channels.connect} — ${messenger}` }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByLabel(en.channels.fields.pageAccessToken)).toBeHidden();
  await dialog.getByRole("button", { name: en.channelSetup.meta.manual }).click();
  await expect(dialog.getByLabel(en.channels.fields.pageAccessToken)).toBeVisible();

  await dialog.getByRole("button", { name: en.metaConnect.continue }).click();
  await expect(dialog.getByRole("radio", { name: /Salon Morgenrot/ })).toBeChecked();
  await dialog.getByRole("button", { name: en.metaConnect.pages.connect }).click();

  await expect(dialog).toBeHidden();
  expect(sent.pages).toEqual([{ state: STATE, code: "AQB-e2e-code-0000" }]);
  expect(sent.picked).toEqual([{ state: STATE, page_id: "4410001" }]);
  expect(await policyViolations(page), "the page picker broke the policy").toEqual([]);
});

test("reached from another page, the dialog loads the page once and opens again", async ({ page, owner }) => {
  await serveMeta(page, owner.businessId);
  const sdkLoads: string[] = [];
  page.on("request", (request) => {
    if (request.url().startsWith("https://connect.facebook.net/")) {
      sdkLoads.push(page.url());
    }
  });
  const response = await page.goto(`/b/${owner.businessId}/overview`);
  // Elsewhere the cabinet keeps its strict policy.
  expect(response?.headers()["content-security-policy"]).not.toContain("facebook");
  expect(response?.headers()["cross-origin-opener-policy"]).toBe("same-origin");

  const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });
  await navigation.getByRole("link", { name: en.navigation.sections.assistant, exact: true }).click();
  await navigation.getByRole("link", { name: en.navigation.pages.assistantChannels, exact: true }).click();
  const whatsapp = en.channels.kinds.whatsapp;
  await cardOf(page, whatsapp).getByRole("button", { name: `${en.channels.connect} — ${whatsapp}` }).click();
  await page.getByRole("dialog").getByRole("button", { name: en.metaConnect.continue }).click();

  // A full load of the Channels page, the dialog open again, the marker gone.
  await expect(page.getByRole("dialog").getByRole("button", { name: en.metaConnect.continue })).toBeEnabled();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/assistant/channels$`));
  expect(sdkLoads.every((url) => url.includes("/assistant/channels"))).toBe(true);
});
