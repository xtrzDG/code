import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderInLocale } from "@/test/render";

import { BusinessStatusBadge } from "./BusinessStatusBadge";

describe("BusinessStatusBadge", () => {
  it.each([
    ["en", "Setting up"],
    ["it", "In configurazione"],
  ] as const)("names a business that is not live yet as being set up, not tested (%s)", (locale, label) => {
    renderInLocale(<BusinessStatusBadge status="testing" />, { locale });

    expect(screen.getByText(label)).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/Testing|In prova/);
  });
});
