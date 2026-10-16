/**
 * Layout problems long texts cause: a page that scrolls sideways, and a
 * button, tab or link whose text does not fit (clipped, or pushed out of
 * the screen). Controls inside a box that scrolls sideways on purpose (a
 * wide table, a row of tabs) may sit outside the screen. In the
 * pseudo-locale every dictionary text is in brackets, so a cut text counts
 * only when it holds one: an e-mail address or a business name may be
 * shortened with "…" on purpose, and so may an element marked
 * `data-clip="content"` (a preview of a customer's message).
 */

import type { BrowserContext, Page } from "@playwright/test";

import { WEB_URL } from "./env";

/**
 * The pseudo-locale (src/i18n/pseudo.ts): `en-XA` left to right, or its
 * twin `ar-XB` on pages laid out right to left as for Hebrew. The cabinet
 * serves them when started with PSEUDO_LOCALE=true.
 */
export async function usePseudoLocale(
  context: BrowserContext,
  direction: "ltr" | "rtl" = "ltr",
): Promise<void> {
  const value = direction === "rtl" ? "ar-XB" : "en-XA";
  await context.addCookies([
    { name: "aw_locale", value, url: WEB_URL, sameSite: "Lax" },
  ]);
}

/** Every overflow on the page, described for the failure message; empty when it fits. */
export function findOverflow(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const problems: string[] = [];
    const width = document.documentElement.clientWidth;
    if (document.documentElement.scrollWidth > width + 1) {
      problems.push(
        `the page scrolls sideways: ${document.documentElement.scrollWidth} px wide on a ${width} px screen`,
      );
    }

    const scrollsSideways = (element: Element): boolean => {
      for (let node = element.parentElement; node; node = node.parentElement) {
        const overflowX = getComputedStyle(node).overflowX;
        if (
          (overflowX === "auto" || overflowX === "scroll") &&
          node.scrollWidth > node.clientWidth + 1
        ) {
          return true;
        }
      }
      return false;
    };
    const describe = (element: HTMLElement): string =>
      `${element.tagName.toLowerCase()}${element.getAttribute("role") ? `[role=${element.getAttribute("role")}]` : ""} “${(
        element.innerText ||
        element.getAttribute("aria-label") ||
        ""
      )
        .replace(/\s+/g, " ")
        .slice(0, 60)}”`;

    const textReachesPast = (control: HTMLElement, box: DOMRect): boolean => {
      const walker = document.createTreeWalker(control, NodeFilter.SHOW_TEXT);
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        if (!node.textContent?.trim()) {
          continue;
        }
        const range = document.createRange();
        range.selectNodeContents(node);
        for (const line of range.getClientRects()) {
          if (
            line.width > 0 &&
            (line.right > box.right + 1 ||
              line.left < box.left - 1 ||
              line.bottom > box.bottom + 1)
          ) {
            return true;
          }
        }
      }
      return false;
    };
    const isText = (element: HTMLElement): boolean =>
      (element.innerText || "").includes("[");

    const controls = document.querySelectorAll<HTMLElement>(
      'button, [role="tab"], [role="button"], a',
    );
    for (const control of controls) {
      const box = control.getBoundingClientRect();
      const style = getComputedStyle(control);
      // Visually hidden ("Skip to content" until focused) and hidden controls do not count.
      if (
        box.width <= 1 ||
        box.height <= 1 ||
        style.visibility === "hidden" ||
        control.closest("[aria-hidden='true'], [inert]")
      ) {
        continue;
      }
      // Clipped: a text of the control reaches past its edge while the control hides overflow.
      const hidesOverflow =
        style.overflowX !== "visible" || style.overflowY !== "visible";
      if (hidesOverflow && isText(control) && textReachesPast(control, box)) {
        problems.push(`${describe(control)} is cut at its edge`);
      }
      // A text cut short inside the control: with an ellipsis, or after its last allowed line.
      for (const part of control.querySelectorAll<HTMLElement>("*")) {
        const partStyle = getComputedStyle(part);
        const isEllipsis =
          partStyle.textOverflow === "ellipsis" &&
          part.scrollWidth > part.clientWidth + 1;
        const isClamped =
          partStyle.webkitLineClamp !== "none" &&
          part.scrollHeight > part.clientHeight + 1;
        if (
          (isEllipsis || isClamped) &&
          isText(part) &&
          !part.closest("[data-clip='content']")
        ) {
          problems.push(
            `${describe(control)} has its text cut (“${(part.innerText || "").slice(0, 40)}”)`,
          );
          break;
        }
      }
      if (
        (box.right > width + 1 || box.left < -1) &&
        !scrollsSideways(control)
      ) {
        problems.push(
          `${describe(control)} sticks out of the screen (${Math.round(box.left)}–${Math.round(box.right)} px)`,
        );
      }
    }
    return problems;
  });
}
