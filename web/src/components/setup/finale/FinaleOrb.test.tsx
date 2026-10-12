import { render, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MotionPreferenceProvider } from "@/components/motion/MotionPreference";

import { FinaleOrb } from "./FinaleOrb";

const orb = (container: HTMLElement) => container.querySelector<HTMLElement>("[data-orb]");

describe("the finale's orb", () => {
  it("stays a drawing when the person asked for calm, and fetches no 3D", () => {
    const { container } = render(
      <MotionPreferenceProvider initialPreference="reduce">
        <FinaleOrb />
      </MotionPreferenceProvider>,
    );
    expect(orb(container)?.dataset.orb).toBe("static");
    expect(orb(container)?.dataset.orbReason).toBe("reduced-motion");
    expect(container.querySelector('[data-illustration="assistant-orb"]')).not.toBeNull();
    expect(container.querySelector("canvas")).toBeNull();
  });

  it("stays a drawing on a narrow screen, as the landing hero does (the same rules)", async () => {
    // The test window matches no media query: not the wide layout.
    const { container } = render(<FinaleOrb />);
    expect(orb(container)?.dataset.orb).toBe("static");
    await waitFor(() => expect(orb(container)?.dataset.orbReason).toBe("narrow-screen"));
    expect(container.querySelector("canvas")).toBeNull();
    expect(orb(container)?.getAttribute("aria-hidden")).toBe("true");
  });
});
