import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { renderInLocale } from "@/test/render";

import { Badge } from "./Badge";
import { Card } from "./Card";
import { PhoneFold, PhoneFolds } from "./PhoneFold";

function Nothing() {
  return null;
}

function Page({ userId = "user_admin" }: { userId?: string }) {
  return (
    <PhoneFolds preference="admin-system-open" userId={userId}>
      <PhoneFold name="circuits" title="Provider circuits" summary={<Badge tone="danger">1 not closed</Badge>}>
        <Card aria-label="Provider circuits" title="Provider circuits" description="The circuit breakers">
          <p>Twilio open</p>
        </Card>
      </PhoneFold>
      <PhoneFold name="database" title="Database" summary="1.2 GB">
        <p>Largest tables</p>
      </PhoneFold>
      <PhoneFold name="reconciliation" title="Payment reconciliation">
        <Nothing />
      </PhoneFold>
    </PhoneFolds>
  );
}

const row = (name: RegExp) => screen.getByRole("button", { name });
const bodyOf = (button: HTMLElement) => document.getElementById(button.getAttribute("aria-controls")!)!;

describe("PhoneFold", () => {
  afterEach(() => window.localStorage.clear());

  it("folds a card into a row that names it and says its summary, and opens it from the keyboard", async () => {
    const user = userEvent.setup();
    renderInLocale(<Page />);
    const circuits = row(/^Provider circuits/);
    expect(circuits.textContent).toContain("1 not closed");
    expect(circuits.getAttribute("aria-expanded")).toBe("false");
    const body = bodyOf(circuits);
    expect(body.className).toContain("max-lg:hidden");
    // The card's own title is said by the row on a phone; its region keeps its name.
    expect(body.className).toContain("max-lg:[&_[data-card-title]]:sr-only");
    expect(screen.getByRole("region", { name: "Provider circuits" }).textContent).toContain("Twilio open");

    circuits.focus();
    await user.keyboard("{Enter}");
    expect(circuits.getAttribute("aria-expanded")).toBe("true");
    expect(body.className).not.toContain("max-lg:hidden");
    await user.keyboard(" ");
    expect(circuits.getAttribute("aria-expanded")).toBe("false");
  });

  it("remembers the open rows per preference and per person", async () => {
    const user = userEvent.setup();
    const view = renderInLocale(<Page />);
    await user.click(row(/^Database/));
    await user.click(row(/^Provider circuits/));
    expect(window.localStorage.getItem("aw.pref.admin-system-open:user_admin")).toBe("circuits,database");

    view.unmount();
    const again = renderInLocale(<Page />);
    expect(row(/^Database/).getAttribute("aria-expanded")).toBe("true");

    // Another admin on the same browser starts with every row folded.
    again.unmount();
    renderInLocale(<Page userId="user_other" />);
    expect(row(/^Database/).getAttribute("aria-expanded")).toBe("false");
  });

  it("leaves no row behind for a block that renders nothing", () => {
    renderInLocale(<Page />);
    const reconciliation = row(/^Payment reconciliation/);
    expect(bodyOf(reconciliation).childElementCount).toBe(0);
    // The wrapper hides itself when its block is empty (CSS :has, phones and large screens alike).
    expect(reconciliation.parentElement!.className).toContain("has-[>[data-fold-body]:empty]:hidden");
    // A row without a summary says only its name.
    expect(reconciliation.textContent).toBe("Payment reconciliation");
  });
});
