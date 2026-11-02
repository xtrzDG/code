import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CustomerPageLinks } from "./CustomerPageLinks";

describe("the links at the foot of a customer's page", () => {
  it("lead to the business's privacy notice and the accessibility statement, in the page's language", () => {
    render(<CustomerPageLinks language="it" privacyHref="/c/cafe-roma/privacy" />);

    const privacy = screen.getByRole("link", { name: "Informativa privacy" });
    const statement = screen.getByRole("link", { name: "Accessibilità" });
    expect(privacy.getAttribute("href")).toBe("/c/cafe-roma/privacy");
    expect(privacy.getAttribute("target")).toBeNull();
    expect(statement.getAttribute("href")).toBe("/it/accessibility");
    expect(screen.getByRole("list").getAttribute("lang")).toBe("it");
  });

  it("open a business's own notice elsewhere in a new tab, and name the statement in English where the site has no language", () => {
    render(<CustomerPageLinks language="ka" privacyHref="https://cafe.example/privacy" />);

    const privacy = screen.getByRole("link", { name: "კონფიდენციალურობა" });
    expect(privacy.getAttribute("target")).toBe("_blank");
    expect(privacy.getAttribute("rel")).toBe("noopener noreferrer");
    const statement = screen.getByRole("link", { name: "ხელმისაწვდომობა" });
    expect(statement.getAttribute("href")).toBe("/en/accessibility");
    expect(statement.getAttribute("hreflang")).toBe("en");
  });

  it("show only the statement when there is no notice to link", () => {
    render(<CustomerPageLinks language="en" privacyHref={null} />);

    expect(screen.getAllByRole("link").map((link) => link.textContent)).toEqual(["Accessibility"]);
  });
});
