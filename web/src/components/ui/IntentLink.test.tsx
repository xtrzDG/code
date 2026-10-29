import { fireEvent, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";

import { IntentLink } from "./IntentLink";

// Next's link, reduced to what it was asked: whether to prefetch.
vi.mock("next/link", () => ({
  default: ({ prefetch, href, children, ...props }: ComponentProps<"a"> & { prefetch?: boolean | null; href: string }) => (
    <a href={href} data-prefetch={String(prefetch)} {...props}>
      {children}
    </a>
  ),
}));

describe("a link that prefetches on intent", () => {
  it("fetches nothing ahead while it is only on screen", () => {
    render(<IntentLink href="/b/business_1/settings">Settings</IntentLink>);
    expect(screen.getByRole("link", { name: "Settings" }).dataset.prefetch).toBe("false");
  });

  it("hands prefetching back to Next.js once a pointer or a finger comes to it", () => {
    const onPointerEnter = vi.fn();
    render(
      <IntentLink href="/b/business_1/settings" onPointerEnter={onPointerEnter}>
        Settings
      </IntentLink>,
    );
    const link = screen.getByRole("link", { name: "Settings" });
    fireEvent.pointerEnter(link);
    expect(link.dataset.prefetch).toBe("null");
    expect(onPointerEnter).toHaveBeenCalledTimes(1);
  });

  it("and once the keyboard's focus does", () => {
    const onFocus = vi.fn();
    render(
      <IntentLink href="/help" onFocus={onFocus}>
        Help
      </IntentLink>,
    );
    const link = screen.getByRole("link", { name: "Help" });
    fireEvent.focus(link);
    expect(link.dataset.prefetch).toBe("null");
    expect(onFocus).toHaveBeenCalledTimes(1);
  });

  it("carries every link of the phone's More sheet, which shows them all at once", () => {
    const shell = path.resolve(__dirname, "..");
    for (const file of ["shell/MoreSheet.tsx", "shell/AccountPanel.tsx", "help/HelpSupportSection.tsx"]) {
      const source = readFileSync(path.join(shell, file), "utf8");
      expect(source, file).not.toContain('from "next/link"');
      expect(source, file).toContain("<IntentLink");
    }
  });
});
