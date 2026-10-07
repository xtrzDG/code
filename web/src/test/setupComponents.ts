/**
 * Setup of the component tests (vitest project "components", jsdom).
 *
 * jsdom renders the DOM but has no layout and no top layer, so the few
 * browser features the UI kit relies on are stood in for here, each as
 * the HTML standard describes it (see modalDialog.ts); a test that needs
 * geometry gives it explicitly (layout.ts).
 */

import { cleanup } from "@testing-library/react";
import { afterEach, beforeAll, vi } from "vitest";

import { loadToastList } from "@/components/ui/toastList";

import { installModalDialog, resetModalDialogs } from "./modalDialog";

installModalDialog();

// jsdom has no layout to animate: `m.*` elements get no animation code
// (as without a <MotionProvider>) and render at once as plain elements.
vi.mock("@/components/motion/motionFeatures", () => ({ default: {} }));

// The browser fetches the toast list with the first toast; tests have it at once.
beforeAll(async () => {
  await loadToastList();
});

// jsdom has no scrolling: a no-op a test can spy on.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() {};
}

// Motion and the theme read media queries; nothing matches (no reduced motion, light theme).
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }) as MediaQueryList;
}

afterEach(() => {
  cleanup();
  resetModalDialogs();
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});
