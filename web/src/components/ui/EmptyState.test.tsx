import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { InboxCalmIllustration } from "@/components/illustrations";

import { EmptyState } from "./EmptyState";

describe("an empty state", () => {
  it("shows a spot illustration instead of the icon tile, hidden from screen readers", () => {
    const { container } = render(
      <EmptyState icon={<span data-testid="icon" />} illustration={<InboxCalmIllustration />} title="All caught up" description="Nothing waits." />,
    );
    expect(container.querySelector('[data-illustration="inbox-calm"]')).not.toBeNull();
    expect(container.querySelector('[data-illustration="inbox-calm"]')?.parentElement?.getAttribute("aria-hidden")).toBe("true");
    expect(screen.queryByTestId("icon")).toBeNull();
    expect(screen.getByRole("heading", { name: "All caught up" })).toBeTruthy();
    expect(screen.getByText("Nothing waits.")).toBeTruthy();
  });

  it("keeps the icon tile where there is no illustration", () => {
    const { container } = render(<EmptyState icon={<span data-testid="icon" />} title="No leads" />);
    expect(screen.getByTestId("icon")).toBeTruthy();
    expect(container.querySelector("[data-illustration]")).toBeNull();
  });
});
