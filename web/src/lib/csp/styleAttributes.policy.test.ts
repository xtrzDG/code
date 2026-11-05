/**
 * The Content Security Policy refuses every style attribute in the
 * server's HTML (style-src has a nonce and no 'unsafe-inline'). So a
 * component may pass `style` only where the server never renders it:
 *
 *  - a server component never does (it has no browser to set it in);
 *  - a client component waits for hydration (src/lib/csp/clientStyle.ts:
 *    useClientStyle, useHydrated, useMountedAfterHydration, or BarFill);
 *  - or it is drawn only in the browser, for the reason listed below.
 *
 * Static values belong in classes; data-driven first-paint rules in a
 * nonce'd <style> (NoncedStyle). The e2e suite checks the pages for
 * violations too (e2e/security.spec.ts).
 */

import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const SOURCE_DIRECTORY = path.resolve(__dirname, "../..");

/** Client components drawn only in the browser, never in the server's HTML. */
const BROWSER_ONLY: Record<string, string> = {
  "app/_landing/scene/FinaleOrbScene.tsx": "loaded with next/dynamic and ssr: false",
  "app/_landing/scene/HeroScene.tsx": "loaded with next/dynamic and ssr: false",
  "app/b/[businessId]/inbox/_components/list/InboxShell.tsx": "the width comes from browser storage, null on the server",
  "components/bookings/calendar/day/BookingBlock.tsx": "drawn from the booking grid, fetched in the browser",
  "components/bookings/calendar/day/DayColumn.tsx": "drawn from the booking grid, fetched in the browser",
  "components/bookings/calendar/day/DayView.tsx": "drawn from the booking grid, fetched in the browser",
  "components/bookings/calendar/nights/NightsRow.tsx": "drawn from the booking grid, fetched in the browser",
  "components/bookings/calendar/nights/NightsView.tsx": "drawn from the booking grid, fetched in the browser",
  "components/bookings/calendar/week/HeatCell.tsx": "drawn from the booking grid, fetched in the browser",
  "components/ui/Popover.tsx": "placed in an effect after it is measured; unplaced it has no style",
  "components/ui/ToastList.tsx": "toasts exist only in the browser",
};

const STYLE_PROP = /\sstyle=\{/;
const HYDRATION_GATE = /from "@\/lib\/csp\/clientStyle"/;

function componentFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return componentFiles(full);
    }
    return entry.name.endsWith(".tsx") && !entry.name.includes(".test.") ? [full] : [];
  });
}

function isClientComponent(source: string): boolean {
  return /^\s*(?:\/\/[^\n]*\n|\/\*[\s\S]*?\*\/\s*)*["']use client["'];/.test(source);
}

describe("style attributes", () => {
  const files = componentFiles(SOURCE_DIRECTORY).map((file) => ({
    name: path.relative(SOURCE_DIRECTORY, file).split(path.sep).join("/"),
    source: readFileSync(file, "utf8"),
  }));
  const styled = files.filter((file) => STYLE_PROP.test(file.source));

  it("never come from a server component", () => {
    expect(styled.filter((file) => !isClientComponent(file.source)).map((file) => file.name)).toEqual([]);
  });

  it("wait for hydration, unless the component is drawn only in the browser", () => {
    const ungated = styled.filter((file) => !HYDRATION_GATE.test(file.source) && !(file.name in BROWSER_ONLY));
    expect(ungated.map((file) => file.name)).toEqual([]);
  });

  it("lists only components that still pass a style", () => {
    const stale = Object.keys(BROWSER_ONLY).filter((name) => !styled.some((file) => file.name === name));
    expect(stale).toEqual([]);
  });
});
