/**
 * A Hebrew conversation end to end, in a cabinet that reads Italian: a
 * visitor writes in Hebrew in the website chat and asks for a manager, the
 * conversation waits in the inbox and opens with each text in its own
 * direction (the customer's Hebrew bubble at the start of the left-to-right
 * page, the team's at its end), and the team's Hebrew reply reaches the
 * visitor's chat.
 */

import { uniqueSuffix } from "./support/api";
import { signInAsDemoOwner, visitorTranscript } from "./support/demo";
import { API_URL, WEB_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { waitingConversationOf } from "./support/inbox";
import { it } from "./support/messages";

test("a Hebrew conversation reads right to left from the visitor's question to the team's reply", async ({
  page,
  context,
  request,
}) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(context, owner.token);
  await context.addCookies([{ name: "aw_locale", value: "it", url: WEB_URL }]);

  const visitor = {
    name: `נועה לוי ${uniqueSuffix()}`,
    sessionKey: `e2e_${uniqueSuffix()}_hebrew`,
  };
  const question = "אפשר לדבר עם מנהל, בבקשה?";
  const widget = `${API_URL}/v1/widget/${owner.businessId}/messages`;
  const sent = await request.post(widget, {
    data: {
      session_key: visitor.sessionKey,
      text: question,
      contact_name: visitor.name,
    },
  });
  expect(sent.status(), await sent.text()).toBe(202);
  await expect
    .poll(
      async () => {
        const poll = await request.get(widget, {
          headers: { "X-Widget-Session-Key": visitor.sessionKey },
        });
        return (
          poll.ok() &&
          ((await poll.json()) as { is_handed_off: boolean }).is_handed_off
        );
      },
      {
        message: "the Hebrew request for a manager hands the chat to a person",
        timeout: 15_000,
      },
    )
    .toBe(true);
  const conversationId = await waitingConversationOf(
    request,
    owner.token,
    owner.businessId,
    visitor.name,
  );

  await page.goto(`/b/${owner.businessId}/inbox/${conversationId}`);
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await expect(page.locator("html")).toHaveAttribute("lang", "it");
  await expect(
    page.getByRole("heading", { level: 2, name: visitor.name }),
  ).toBeVisible();

  const transcript = page.getByRole("region", {
    name: it.conversations.transcript,
  });
  const message = transcript.getByText(question).first();
  await expect(message).toBeVisible();
  expect(
    await message.evaluate((element) => getComputedStyle(element).direction),
  ).toBe("rtl");
  const middle = await transcript.evaluate((element) => {
    const box = element.getBoundingClientRect();
    return box.left + box.width / 2;
  });
  const centre = async (locator: typeof message) => {
    const box = await locator.boundingBox();
    return box ? box.x + box.width / 2 : 0;
  };
  // The customer's bubble stands at the start of the page (its left); the Hebrew line inside it starts on its right.
  expect(await centre(message)).toBeLessThan(middle);

  const reply = `שלום נועה, אני המנהל במשמרת. ${uniqueSuffix()}`;
  await page
    .getByRole("textbox", { name: it.conversations.reply.label })
    .fill(reply);
  await page
    .getByRole("button", { name: it.inboxCard.composer.sendLabel, exact: true })
    .click();
  const answer = transcript.getByText(reply);
  await expect(answer).toBeVisible();
  // The team's bubble stands on the other side.
  expect(await centre(answer)).toBeGreaterThan(middle);
  await expect
    .poll(() => visitorTranscript(request, owner.businessId, visitor))
    .toContain(reply);
});
