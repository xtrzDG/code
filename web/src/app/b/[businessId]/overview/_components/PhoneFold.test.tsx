import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import type { BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale } from "@/test/render";

import { PhoneFold, PhoneFolds } from "./PhoneFold";

const business = { id: "business_1", viewer_role: "owner", status: "live" } as unknown as BusinessView;
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const REMEMBERED = "aw.pref.overview-open:user_owner";

function Folds() {
  return (
    <BusinessProvider business={business} me={me}>
      <PhoneFolds>
        <PhoneFold name="languages" title="Languages" summary="Russian: 35 %">
          <p>Russian 15</p>
        </PhoneFold>
        <PhoneFold name="channels" title="Channels">
          <p>Website chat 16</p>
        </PhoneFold>
      </PhoneFolds>
    </BusinessProvider>
  );
}

function row(name: RegExp) {
  return screen.getByRole("button", { name });
}

describe("PhoneFold", () => {
  afterEach(() => window.localStorage.clear());

  it("folds each block into a row with its summary; a tap opens it and the open ones are remembered", async () => {
    const user = userEvent.setup();
    const view = renderInLocale(<Folds />);
    const languages = row(/^Languages/);
    expect(languages.textContent).toContain("Russian: 35 %");
    expect(languages.getAttribute("aria-expanded")).toBe("false");
    const content = document.getElementById(languages.getAttribute("aria-controls")!)!;
    expect(content.textContent).toBe("Russian 15");
    expect(content.className).toContain("max-lg:hidden");

    await user.click(languages);
    expect(languages.getAttribute("aria-expanded")).toBe("true");
    expect(content.className).not.toContain("max-lg:hidden");
    expect(row(/^Channels/).getAttribute("aria-expanded")).toBe("false");
    expect(window.localStorage.getItem(REMEMBERED)).toBe("languages");

    // Another visit: the row the person opened is open again.
    view.unmount();
    renderInLocale(<Folds />);
    expect(row(/^Languages/).getAttribute("aria-expanded")).toBe("true");

    await user.click(row(/^Languages/));
    expect(row(/^Languages/).getAttribute("aria-expanded")).toBe("false");
    expect(window.localStorage.getItem(REMEMBERED)).toBeNull();
  });

  it("ignores a remembered value it does not understand", () => {
    window.localStorage.setItem(REMEMBERED, "<script>,channels");
    renderInLocale(<Folds />);
    expect(row(/^Languages/).getAttribute("aria-expanded")).toBe("false");
    expect(row(/^Channels/).getAttribute("aria-expanded")).toBe("true");
  });
});
