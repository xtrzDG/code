/**
 * The conversation card's call recordings: fetched only when played, played
 * and sought from memory, a missing one explained, a failed one retried, and
 * an expired session sent to sign-in. The card itself is served by the test
 * (see support/conversation-card.ts); everything else runs against the real API.
 */

import type { Route } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { waitForNetworkQuiet } from "./support/network";
import { en } from "./support/messages";
import { CONVERSATION_ID, cardWithCalls, datedLabel, openCard, openDetails, playerLabel, serveCard, silentWav } from "./support/conversation-card";

test("a call recording loads only when played, seeks, and a missing one says so", async ({ page, owner, consoleErrors }) => {
  consoleErrors.allow(/Failed to load resource: the server responded with a status of 404/);
  await serveCard(page, owner.businessId, cardWithCalls(owner.businessId, ["call_kept", "call_purged"]));
  const played: string[] = [];
  await page.route("**/calls/*/recording", (route: Route) => {
    const url = route.request().url();
    played.push(url);
    // Served the way the API answers a request without Range: whole, 200.
    return url.includes("/calls/call_kept/")
      ? route.fulfill({ status: 200, contentType: "audio/wav", body: silentWav(10) })
      : route.fulfill({ status: 404, json: { error: "not_found", message: "This call has no recording." } });
  });

  await openCard(page, owner.businessId);
  await openDetails(page);
  const playButtons = page.getByRole("button", { name: datedLabel(en.conversations.calls.playLabel) });
  await expect(playButtons).toHaveCount(2);
  await waitForNetworkQuiet(page);
  // Opening the card fetches no audio (and so writes no audit entry).
  expect(played).toEqual([]);
  await expect(page.getByLabel(playerLabel())).toHaveCount(0);

  await playButtons.nth(0).click();
  const player = page.getByLabel(playerLabel());
  await expect(player).toHaveCount(1);
  // The pressed button is gone; focus is on the player that replaced it.
  await expect(player).toBeFocused();
  expect(await player.evaluate((audio: HTMLAudioElement) => audio.src.startsWith("blob:"))).toBe(true);
  await expect.poll(() => player.evaluate((audio: HTMLAudioElement) => audio.readyState)).toBeGreaterThan(0);
  // Played from memory: the whole recording is seekable without ranges.
  expect(await player.evaluate((audio: HTMLAudioElement) => audio.seekable.end(0))).toBeGreaterThan(9);
  const position = await player.evaluate(
    (audio: HTMLAudioElement) =>
      new Promise<number>((resolve) => {
        audio.addEventListener("seeked", () => resolve(audio.currentTime), { once: true });
        audio.currentTime = 6;
      }),
  );
  expect(position).toBeGreaterThanOrEqual(5.9);
  expect(played).toHaveLength(1);
  await expect(page.getByText(en.conversations.calls.playError)).toBeHidden();

  await page.getByRole("button", { name: datedLabel(en.conversations.calls.playLabel) }).click();
  await expect(page.getByText(en.conversations.calls.playMissing)).toBeVisible();
  // A deleted recording cannot come back: nothing to try again.
  await expect(page.getByRole("button", { name: en.conversations.calls.playRetry })).toHaveCount(0);
  expect(played).toHaveLength(2);
});

test("a recording the service could not give can be tried again from the keyboard", async ({ page, owner, consoleErrors }) => {
  consoleErrors.allow(/Failed to load resource: the server responded with a status of 502/);
  await serveCard(page, owner.businessId, cardWithCalls(owner.businessId, ["call_flaky"]));
  let answers = 0;
  await page.route("**/calls/*/recording", (route: Route) => {
    answers += 1;
    return answers <= 2
      ? route.fulfill({ status: 502, json: { error: "external_service_error", message: "ElevenLabs is down." } })
      : route.fulfill({ status: 200, contentType: "audio/wav", body: silentWav() });
  });

  await openCard(page, owner.businessId);
  await openDetails(page);
  await page.getByRole("button", { name: datedLabel(en.conversations.calls.playLabel) }).click();
  const failure = page.getByRole("alert").filter({ hasText: en.conversations.calls.playError });
  await expect(failure).toBeVisible();
  const retry = failure.getByRole("button", { name: en.conversations.calls.playRetry });

  // A retry that fails again keeps the alert and the focus on its button.
  await retry.press("Enter");
  await expect.poll(() => answers).toBe(2);
  // The second answer is counted when it is served, before the page has read
  // it: the button stays busy (and ignores Enter) until then.
  await expect(retry).not.toHaveAttribute("aria-busy", "true");
  await expect(retry).toBeFocused();
  await expect(failure).toBeVisible();

  await retry.press("Enter");
  const player = page.getByLabel(playerLabel());
  await expect(player).toHaveCount(1);
  await expect(player).toBeFocused();
  await expect(failure).toBeHidden();
});

test("an expired session sends the player to sign-in", async ({ page, owner, consoleErrors }) => {
  consoleErrors.allow(/status of 401/);
  await serveCard(page, owner.businessId, cardWithCalls(owner.businessId, ["call_late"]));
  await page.route("**/calls/*/recording", (route: Route) =>
    route.fulfill({ status: 401, json: { error: "authentication_required", message: "Sign in again." } }),
  );

  await openCard(page, owner.businessId);
  await openDetails(page);
  await page.getByRole("button", { name: datedLabel(en.conversations.calls.playLabel) }).click();

  await expect(page).toHaveURL(/\/login\?.*reason=expired/);
  const next = new URL(page.url()).searchParams.get("next");
  expect(next).toBe(`/b/${owner.businessId}/inbox/${CONVERSATION_ID}`);
});
