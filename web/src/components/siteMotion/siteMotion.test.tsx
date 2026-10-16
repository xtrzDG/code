import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MagneticButton, Parallax, Reveal, Stagger, StaggerItem, TiltCard, TiltLayer } from ".";

/** A stand-in IntersectionObserver whose observed elements a test "scrolls into view". */
class FakeObserver {
  static all: FakeObserver[] = [];
  readonly observed = new Set<Element>();
  constructor(
    readonly callback: IntersectionObserverCallback,
    readonly options: IntersectionObserverInit,
  ) {
    FakeObserver.all.push(this);
  }
  observe(element: Element) {
    this.observed.add(element);
  }
  unobserve(element: Element) {
    this.observed.delete(element);
  }
  disconnect() {
    this.observed.clear();
  }
}

/** Reports `element` on screen (or not) to whichever observer watches it. */
function scrollTo(element: Element, isIntersecting = true) {
  for (const observer of FakeObserver.all.filter((candidate) => candidate.observed.has(element))) {
    act(() => observer.callback([{ target: element, isIntersecting } as unknown as IntersectionObserverEntry], {} as IntersectionObserver));
  }
}

function box(element: Element, rect: Partial<DOMRect>) {
  vi.spyOn(element, "getBoundingClientRect").mockReturnValue({ left: 0, top: 0, width: 0, height: 0, ...rect } as DOMRect);
}

// The observers live as long as the page (one per share of visibility), so the list is kept across tests.
beforeEach(() => {
  vi.stubGlobal("IntersectionObserver", FakeObserver);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Reveal", () => {
  it("stays hidden until enough of it is seen, then stays revealed", () => {
    render(
      <Reveal as="section" depth={1} delay={0.2} amount={0.4} aria-label="Plans">
        Plans
      </Reveal>,
    );
    const element = screen.getByRole("region", { name: "Plans" });
    expect(element.hasAttribute("data-reveal")).toBe(true);
    expect(element.style.getPropertyValue("--reveal-depth")).toBe("1");
    expect(element.style.getPropertyValue("--reveal-delay")).toBe("0.2s");
    expect(FakeObserver.all.find((observer) => observer.observed.has(element))?.options).toEqual({ threshold: 0.4 });

    scrollTo(element, false);
    expect(element.hasAttribute("data-revealed")).toBe(false);
    scrollTo(element);
    expect(element.hasAttribute("data-revealed")).toBe(true);
    // Seen once is enough: it is no longer watched.
    expect(FakeObserver.all.some((observer) => observer.observed.has(element))).toBe(false);
  });

  it("writes no style of its own with the defaults, and one observer serves every reveal of a share", () => {
    render(
      <>
        <Reveal>One</Reveal>
        <Reveal>Two</Reveal>
      </>,
    );
    expect(screen.getByText("One").getAttribute("style")).toBeNull();
    const watching = FakeObserver.all.filter((observer) => observer.observed.size > 0);
    expect(watching).toHaveLength(1);
    expect(watching[0]?.observed.size).toBe(2);
  });

  it("stops waiting when it leaves the page before being seen", () => {
    const { unmount } = render(<Reveal>Gone</Reveal>);
    const element = screen.getByText("Gone");
    unmount();
    expect(FakeObserver.all.some((observer) => observer.observed.has(element))).toBe(false);
  });

  it("shows at once where the browser cannot tell what is on screen", () => {
    vi.stubGlobal("IntersectionObserver", undefined);
    render(<Reveal>Plain</Reveal>);
    expect(screen.getByText("Plain").hasAttribute("data-revealed")).toBe(true);
  });
});

describe("Stagger", () => {
  it("numbers its own items once seen and leaves an inner group's items to it", () => {
    render(
      <Stagger as="ul" delay={0.15} step={0.45} aria-label="Steps">
        <StaggerItem as="li">First</StaggerItem>
        <StaggerItem as="li" depth={1}>
          Second
          <Stagger aria-label="Inner">
            <StaggerItem>Inner item</StaggerItem>
          </Stagger>
        </StaggerItem>
      </Stagger>,
    );
    const group = screen.getByRole("list", { name: "Steps" });
    expect(group.style.getPropertyValue("--stagger-delay")).toBe("0.15s");
    expect(group.style.getPropertyValue("--stagger-step")).toBe("0.45s");
    const [first, second] = screen.getAllByRole("listitem");
    expect(second?.style.getPropertyValue("--reveal-depth")).toBe("1");
    expect(first?.hasAttribute("data-reveal-item")).toBe(true);

    scrollTo(group);
    expect(group.hasAttribute("data-revealed")).toBe(true);
    expect(first?.style.getPropertyValue("--reveal-index")).toBe("0");
    expect(second?.style.getPropertyValue("--reveal-index")).toBe("1");
    expect(screen.getByText("Inner item").style.getPropertyValue("--reveal-index")).toBe("");
  });
});

describe("TiltCard", () => {
  it("turns towards the mouse with a glare where it points, and settles when it leaves", () => {
    render(
      <TiltCard as="figure" maxDegrees={10}>
        <TiltLayer depth={24}>Card</TiltLayer>
      </TiltCard>,
    );
    const card = screen.getByRole("figure");
    expect(screen.getByText("Card").style.transform).toBe("translateZ(24px)");
    box(card, { width: 200, height: 100 });

    fireEvent.pointerMove(card, { pointerType: "mouse", clientX: 200, clientY: 0 });
    expect(card.style.getPropertyValue("--tilt-x")).toBe("10deg");
    expect(card.style.getPropertyValue("--tilt-y")).toBe("10deg");
    expect(card.style.getPropertyValue("--glare-x")).toBe("100%");
    expect(card.hasAttribute("data-tilting")).toBe(true);
    expect(card.querySelector(".tilt-glare")).not.toBeNull();

    fireEvent.pointerLeave(card);
    expect(card.style.getPropertyValue("--tilt-x")).toBe("");
    expect(card.hasAttribute("data-tilting")).toBe(false);
  });

  it("stays flat under a finger or a pen, and can go without the glare", () => {
    render(<TiltCard glare={false}>Card</TiltCard>);
    const card = screen.getByText("Card");
    box(card, { width: 200, height: 100 });
    fireEvent.pointerMove(card, { pointerType: "touch", clientX: 200, clientY: 0 });
    expect(card.style.getPropertyValue("--tilt-x")).toBe("");
    expect(card.querySelector(".tilt-glare")).toBeNull();
  });
});

describe("MagneticButton", () => {
  it("leans towards the mouse, at most a few pixels, and springs back", () => {
    render(
      <MagneticButton strength={0.5} maxOffset={6}>
        <button type="button">Start</button>
      </MagneticButton>,
    );
    const wrapper = screen.getByRole("button", { name: "Start" }).parentElement as HTMLElement;
    box(wrapper, { width: 100, height: 40 });

    fireEvent.pointerMove(wrapper, { pointerType: "mouse", clientX: 58, clientY: 100 });
    expect(wrapper.style.getPropertyValue("--magnet-x")).toBe("4px");
    expect(wrapper.style.getPropertyValue("--magnet-y")).toBe("6px");
    fireEvent.pointerMove(wrapper, { pointerType: "pen", clientX: 0, clientY: 0 });
    expect(wrapper.style.getPropertyValue("--magnet-x")).toBe("4px");

    fireEvent.pointerLeave(wrapper);
    expect(wrapper.style.getPropertyValue("--magnet-x")).toBe("");
  });
});

describe("Parallax", () => {
  it("is a decorative layer that drifts by its speed's share of the way", () => {
    const { container } = render(<Parallax speed={-0.6} className="glow" />);
    const layer = container.firstElementChild as HTMLElement;
    expect(layer.getAttribute("aria-hidden")).toBe("true");
    expect(layer.className).toBe("parallax-layer glow");
    expect(layer.style.getPropertyValue("--parallax-shift")).toBe("-72px");
  });
});
