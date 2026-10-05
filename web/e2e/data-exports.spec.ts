/**
 * Exports of the business's data: the owner downloads a table as CSV from
 * Settings → Privacy, Bookings and the Inbox (UTF-8 with a byte order
 * mark, headings in the cabinet's language, named by the table and the
 * day), and prepares the full export, which the worker builds into a ZIP
 * downloaded through one-time links (three downloads at most). Staff get
 * no export buttons.
 */

import { readFile } from "node:fs/promises";

import type { Download, Page } from "@playwright/test";

import { inviteStaff, signInByEmail, uniqueEmail } from "./support/api";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

const texts = en.dataExports;
const BOM = "﻿";

async function downloadBy(page: Page, click: () => Promise<void>): Promise<Download> {
  const [download] = await Promise.all([page.waitForEvent("download"), click()]);
  return download;
}

async function textOf(download: Download): Promise<string> {
  return readFile(await download.path(), "utf8");
}

test("the owner downloads tables as CSV and the full export as a ZIP", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/settings/privacy`);
  await expect(page.getByRole("heading", { name: texts.full.title })).toBeVisible();
  await expect(page.getByText(texts.full.empty)).toBeVisible();

  const bookings = await downloadBy(page, () =>
    page.getByRole("button", { name: texts.csv.tableLabel.replace("{table}", texts.csv.tables.bookings) }).click(),
  );
  expect(bookings.suggestedFilename()).toMatch(/^bookings-\d{4}-\d{2}-\d{2}\.csv$/);
  expect(await textOf(bookings)).toMatch(new RegExp(`^${BOM}Booking ID,`));

  const audit = await downloadBy(page, () =>
    page.getByRole("button", { name: texts.csv.tableLabel.replace("{table}", texts.csv.tables.audit_log) }).click(),
  );
  // The bookings export above is itself in the log.
  expect(await textOf(audit)).toContain("export,booking,csv");

  await page.getByRole("button", { name: texts.full.start }).click();
  await expect(page.getByText(texts.full.started)).toBeVisible();
  const button = page.getByRole("button", { name: /^Download the export asked / });
  await expect(button).toBeVisible({ timeout: 60_000 });
  const row = page.getByRole("listitem").filter({ has: button });
  await expect(row.getByText(texts.full.status.ready, { exact: true })).toBeVisible();
  await expect(row.getByText(/3 of 3 downloads left/)).toBeVisible();
  const archive = await downloadBy(page, () => button.click());
  expect(archive.suggestedFilename()).toMatch(/^business-export-\d{4}-\d{2}-\d{2}\.zip$/);
  const bytes = await readFile(await archive.path());
  expect(bytes.subarray(0, 2).toString("latin1")).toBe("PK");
  await expect(row.getByText(/2 of 3 downloads left/)).toBeVisible();
});

test("Bookings and the Inbox export what their filters show; staff see no export", async ({ browser, page, owner, request }) => {
  await page.goto(`/b/${owner.businessId}/bookings?range=past&status=cancelled`);
  const filtered = page.waitForRequest(/\/exports\/bookings\?.*status=cancelled.*order=latest_first/);
  const bookings = await downloadBy(page, () => page.getByRole("button", { name: texts.csv.button }).click());
  await filtered;
  expect(bookings.suggestedFilename()).toMatch(/^bookings-\d{4}-\d{2}-\d{2}\.csv$/);
  const rows = (await textOf(bookings)).trim().split("\r\n");
  expect(rows).toHaveLength(1);
  await expect(page.getByText(texts.csv.saved)).toBeVisible();

  await page.goto(`/b/${owner.businessId}/inbox?view=all`);
  const conversations = await downloadBy(page, () => page.getByRole("button", { name: texts.csv.inboxLabel }).click());
  expect(conversations.suggestedFilename()).toMatch(/^conversations-\d{4}-\d{2}-\d{2}\.csv$/);
  expect(await textOf(conversations)).toMatch(new RegExp(`^${BOM}Conversation ID,`));

  const staffEmail = uniqueEmail();
  await inviteStaff(request, owner.token, owner.businessId, staffEmail);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInByEmail(request, staffEmail));
  const staffPage = await context.newPage();
  await staffPage.goto(`/b/${owner.businessId}/bookings`);
  await expect(staffPage.getByRole("heading", { level: 1, name: en.nav.bookings })).toBeVisible();
  await expect(staffPage.getByRole("button", { name: texts.csv.button })).toHaveCount(0);
  await staffPage.goto(`/b/${owner.businessId}/inbox`);
  await expect(staffPage.getByRole("heading", { level: 1, name: en.inbox.title })).toBeVisible();
  await expect(staffPage.getByRole("button", { name: texts.csv.inboxLabel })).toHaveCount(0);
  await context.close();
});
