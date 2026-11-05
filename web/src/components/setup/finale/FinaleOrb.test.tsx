import { render, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MotionPreferenceProvider } from "@/components/motion/MotionPreference";

import { FinaleOrb } from "./FinaleOrb";

// The browser's waits pass at once; WebGL is whatever a test says.
const { hasWebGl } = vi.hoisted(() => ({ hasWebGl: vi.fn(() => false) }));
vi.mock("@/app/_landing/heroWaits", async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  afterNextPaint: (next: () => void) => {
    next();
    return () => undefined;
  },
  whenIdle: (next: () => void) => {
    next();
    return () => undefined;
  },
  hasWebGl,
}));

// The landing's orb (three.js) stood in for by a scene that has drawn its first frame.
vi.mock("@/app/_landing/scene/FinaleOrbScene", () => ({
  default: function FinaleOrbScene({ onReady }: { onReady: () => void }) {
    useEffect(onReady, [onReady]);
    return <div data-finale-scene />;
  },
}));

const orb = (container: HTMLElement) => container.querySelector<HTMLElement>("[data-orb]");

describe("the finale's orb", () => {
  afterEach(() => {
    hasWebGl.mockReset();
  });

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

  it("stays a drawing where there is no WebGL, on a narrow screen too", async () => {
    // The test window matches no media query (not the wide layout) and jsdom has no WebGL.
    hasWebGl.mockReturnValue(false);
    const { container } = render(<FinaleOrb />);
    expect(orb(container)?.dataset.orb).toBe("static");
    await waitFor(() => expect(orb(container)?.dataset.orbReason).toBe("no-webgl"));
    expect(container.querySelector("[data-finale-scene]")).toBeNull();
    expect(orb(container)?.getAttribute("aria-hidden")).toBe("true");
  });

  it("becomes the landing's 3D orb on a phone where WebGL exists", async () => {
    hasWebGl.mockReturnValue(true);
    const { container } = render(<FinaleOrb />);
    expect(orb(container)?.dataset.orb).toBe("static");
    await waitFor(() => expect(orb(container)?.dataset.orb).toBe("3d"));
    expect(container.querySelector("[data-finale-scene]")).not.toBeNull();
  });
});
