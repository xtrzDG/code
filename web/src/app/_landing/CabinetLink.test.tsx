import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { buttonClasses } from "@/components/ui";

import { CabinetButtonLink } from "./CabinetLink";

describe("a button link into the cabinet", () => {
  it("is a plain anchor that looks like a button", () => {
    render(
      <CabinetButtonLink href="/create" size="lg" fullWidth trailingIcon={<svg data-testid="arrow" />}>
        Create an AI assistant
      </CabinetButtonLink>,
    );
    const link = screen.getByRole("link", { name: "Create an AI assistant" });
    expect(link.getAttribute("href")).toBe("/create");
    expect(link.className).toBe(buttonClasses({ size: "lg", fullWidth: true }));
    expect(link.lastElementChild).toBe(screen.getByTestId("arrow"));
  });
});
