/**
 * The website chat's warm look in both themes and three languages (English,
 * Georgian, right-to-left Hebrew), on a host site with a fake widget API
 * (support/widget-site.ts): paper #faf7f2 or ink #1a1816 by the visitor's
 * system or the script tag's data-theme, the business colour only on the
 * header, the launcher and the send button, and text on it at WCAG AA.
 */

import type { Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { FakeWidgetApi, SITE, chat, loadWidgetSource, serveSite } from "./support/widget-site";

test.beforeAll(async () => {
  await loadWidgetSource();
});

const LANGUAGES = [
  { tag: "en", direction: "ltr", native_name: "English" },
  { tag: "ka", direction: "ltr", native_name: "ქართული" },
  { tag: "he", direction: "rtl", native_name: "עברית" },
];
const PAPER = "rgb(250, 247, 242)";
const INK = "rgb(26, 24, 22)";

/** Computed colours of the widget's parts (inside its shadow root). */
async function widgetColours(page: Page) {
  return page.evaluate(() => {
    const root = document.querySelector("[data-assistant-workshop-chat]")?.shadowRoot;
    const style = (selector: string) => {
      const element = root?.querySelector(selector);
      return element ? getComputedStyle(element) : null;
    };
    return {
      panel: style(".aw-panel")?.backgroundColor,
      header: style(".aw-header")?.backgroundColor,
      headerText: style(".aw-header")?.color,
      send: style(".aw-send")?.backgroundColor,
      launcher: style(".aw-launcher")?.backgroundColor,
      direction: root?.querySelector(".aw")?.getAttribute("dir"),
    };
  });
}

async function openWidget(page: Page, attributes: Record<string, string>) {
  const api = new FakeWidgetApi();
  api.configExtras = { languages: LANGUAGES, default_language: "en" };
  await serveSite(page.context(), api, { dataOpen: true, attributes });
  await page.goto(`${SITE}/`);
  await expect(chat(page)).toBeVisible();
}

for (const scheme of ["light", "dark"] as const) {
  test.describe(`a ${scheme} system`, () => {
    test.use({ colorScheme: scheme });

    test(`the widget follows it, and data-theme wins over it`, async ({ page }) => {
      await openWidget(page, {});
      expect((await widgetColours(page)).panel).toBe(scheme === "dark" ? INK : PAPER);

      const other = scheme === "dark" ? "light" : "dark";
      await openWidget(page, { "data-theme": other });
      expect((await widgetColours(page)).panel).toBe(other === "dark" ? INK : PAPER);
    });
  });
}

test("a light business colour keeps ink text on the header, launcher and send button", async ({ page }) => {
  await openWidget(page, { "data-color": "#f59e0b" });

  const colours = await widgetColours(page);
  expect(colours.header).toBe("rgb(245, 158, 11)");
  expect(colours.launcher).toBe(colours.header);
  expect(colours.send).toBe(colours.header);
  expect(colours.headerText).toBe(INK);
  // The panel itself stays paper: the business colour is an accent only.
  expect(colours.panel).toBe(PAPER);
});

test("a mid-tone business colour is darkened until white text reads on it", async ({ page }) => {
  await openWidget(page, { "data-color": "#808080" });

  const colours = await widgetColours(page);
  expect(colours.headerText).toBe("rgb(255, 255, 255)");
  expect(colours.header).not.toBe("rgb(128, 128, 128)");
});

for (const { language, placeholder, direction } of [
  { language: "en", placeholder: "Type a message…", direction: "ltr" },
  { language: "ka", placeholder: "დაწერეთ შეტყობინება…", direction: "ltr" },
  { language: "he", placeholder: "כתבו הודעה…", direction: "rtl" },
]) {
  test(`the widget speaks ${language} in the warm palette`, async ({ page }) => {
    await openWidget(page, { "data-language": language });

    await expect(page.getByRole("textbox")).toHaveAttribute("placeholder", placeholder);
    const colours = await widgetColours(page);
    expect(colours.direction).toBe(direction);
    expect(colours.panel).toBe(PAPER);
  });
}
