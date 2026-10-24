import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DeviceSignals } from "@/lib/heroDevice";

import { HeroVisual } from "./HeroVisual";

/** The browser's moments and signals, released by hand (./heroWaits is mocked). */
const control = vi.hoisted(() => ({
  signals: {} as DeviceSignals,
  webGl: true,
  pending: [] as { name: string; next: () => void }[],
  cancelled: [] as string[],
  scene: null as { onReady: () => void; onFallback: () => void } | null,
}));

vi.mock("./heroWaits", () => {
  const manual = (name: string) => (next: () => void) => {
    control.pending.push({ name, next });
    return () => control.cancelled.push(name);
  };
  return {
    REDUCED_MOTION_QUERY: "(prefers-reduced-motion: reduce)",
    WIDE_LAYOUT_QUERY: "(min-width: 64rem)",
    readDeviceSignals: () => control.signals,
    hasWebGl: () => control.webGl,
    afterNextPaint: manual("paint"),
    afterPageLoad: manual("load"),
    whenIdle: manual("idle"),
    whenOnScreen: () => manual("on-screen"),
  };
});

vi.mock("./scene/HeroScene", () => ({
  default: function FakeScene(props: { onReady: () => void; onFallback: () => void; className?: string }) {
    control.scene = { onReady: props.onReady, onFallback: props.onFallback };
    return <div data-testid="scene" className={props.className} />;
  },
}));

const WIDE_DESKTOP: DeviceSignals = { prefersReducedMotion: false, isWideLayout: true, isCoarsePointer: false, cores: 8, memoryGb: 8 };

/** Media queries the test can flip; HeroVisual listens to them. */
const media = new Map<string, { matches: boolean; listeners: Set<() => void> }>();

function flipMedia(query: string, matches: boolean) {
  const entry = media.get(query);
  if (!entry) {
    throw new Error(`nobody listens to ${query}`);
  }
  entry.matches = matches;
  act(() => entry.listeners.forEach((listener) => listener()));
}

function release(name: string) {
  const index = control.pending.findIndex((wait) => wait.name === name);
  if (index < 0) {
    throw new Error(`no pending wait "${name}" (pending: ${control.pending.map((wait) => wait.name).join(", ")})`);
  }
  const [wait] = control.pending.splice(index, 1);
  act(() => wait?.next());
}

function renderVisual() {
  render(<HeroVisual label="The assistant answering every channel" />);
  return screen.getByRole("img", { name: "The assistant answering every channel" });
}

describe("the hero's picture", () => {
  beforeEach(() => {
    control.signals = WIDE_DESKTOP;
    control.webGl = true;
    control.pending = [];
    control.cancelled = [];
    control.scene = null;
    media.clear();
    vi.spyOn(window, "matchMedia").mockImplementation((query: string) => {
      const entry = media.get(query) ?? { matches: query.includes("min-width"), listeners: new Set<() => void>() };
      media.set(query, entry);
      return {
        get matches() {
          return entry.matches;
        },
        media: query,
        onchange: null,
        addEventListener: (_type: string, listener: () => void) => entry.listeners.add(listener),
        removeEventListener: (_type: string, listener: () => void) => entry.listeners.delete(listener),
        addListener: () => undefined,
        removeListener: () => undefined,
        dispatchEvent: () => false,
      } as unknown as MediaQueryList;
    });
  });

  it("is the poster from the first render, and stays the poster on a phone", () => {
    control.signals = { ...WIDE_DESKTOP, isWideLayout: false, isCoarsePointer: true };
    const hero = renderVisual();
    expect(hero.getAttribute("data-scene")).toBe("static");
    expect(hero.querySelector(".hero-still")).not.toBeNull();
    expect(hero.hasAttribute("data-scene-reason")).toBe(false);

    release("paint");
    expect(hero.getAttribute("data-scene-reason")).toBe("narrow-screen");
    // Nothing else is waited for: the 3D chunk is never asked for.
    expect(control.pending).toEqual([]);
    expect(screen.queryByTestId("scene")).toBeNull();
  });

  it("fetches the scene only after the load event, idle time and the hero on screen, and shows it after its first frame", async () => {
    const hero = renderVisual();
    for (const moment of ["paint", "load", "idle"]) {
      release(moment);
      expect(screen.queryByTestId("scene")).toBeNull();
    }
    release("on-screen");

    const scene = await screen.findByTestId("scene");
    // Loaded but not drawn yet: the poster stays in front, the scene is transparent.
    expect(hero.getAttribute("data-scene")).toBe("static");
    expect(scene.classList.contains("opacity-0")).toBe(true);

    act(() => control.scene?.onReady());
    expect(hero.getAttribute("data-scene")).toBe("3d");
    expect(scene.classList.contains("opacity-100")).toBe(true);
    expect(hero.querySelector(".hero-still")?.className).toMatch(/\binvisible\b.*\bopacity-0\b|\bopacity-0\b.*\binvisible\b/);
  });

  it("keeps the poster where WebGL is missing", () => {
    control.webGl = false;
    const hero = renderVisual();
    ["paint", "load", "idle", "on-screen"].forEach(release);
    expect(hero.getAttribute("data-scene-reason")).toBe("no-webgl");
    expect(screen.queryByTestId("scene")).toBeNull();
  });

  it("goes back to the poster when the visitor turns reduced motion on", async () => {
    const hero = renderVisual();
    ["paint", "load", "idle", "on-screen"].forEach(release);
    await screen.findByTestId("scene");
    act(() => control.scene?.onReady());

    const leaving = control.scene;
    flipMedia("(prefers-reduced-motion: reduce)", true);
    expect(hero.getAttribute("data-scene")).toBe("static");
    expect(hero.getAttribute("data-scene-reason")).toBe("reduced-motion");
    expect(screen.queryByTestId("scene")).toBeNull();
    // The scene loses its WebGL context as it goes: that is no reason of its own.
    act(() => leaving?.onFallback());
    expect(hero.getAttribute("data-scene-reason")).toBe("reduced-motion");
  });

  it("stops waiting when the window narrows to the phone layout", () => {
    const hero = renderVisual();
    release("paint");
    flipMedia("(min-width: 64rem)", false);
    expect(hero.getAttribute("data-scene-reason")).toBe("narrow-screen");
    expect(control.cancelled).toContain("load");
  });

  it("hands back to the poster when the scene gives up", async () => {
    const hero = renderVisual();
    ["paint", "load", "idle", "on-screen"].forEach(release);
    await screen.findByTestId("scene");
    act(() => control.scene?.onFallback());
    expect(hero.getAttribute("data-scene-reason")).toBe("gave-up");
    expect(screen.queryByTestId("scene")).toBeNull();
  });

  it("cancels what it waits for when it leaves the page", () => {
    const { unmount } = render(<HeroVisual label="Hero" />);
    release("paint");
    unmount();
    expect(control.cancelled).toContain("load");
  });
});
