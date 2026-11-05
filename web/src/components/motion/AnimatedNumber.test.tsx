import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AnimatedNumber } from "./AnimatedNumber";

/** Each character is 10 px wide, as tabular digits are (jsdom lays nothing out). */
const CHARACTER_PX = 10;

const format = (value: number) => String(value);
const numberIn = (container: HTMLElement) => container.querySelector("span") as HTMLSpanElement;

describe("AnimatedNumber", () => {
  let frames: FrameRequestCallback[] = [];

  beforeEach(() => {
    frames = [];
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => frames.push(callback));
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => undefined);
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      return new DOMRect(0, 0, (this.textContent ?? "").length * CHARACTER_PX, 20);
    });
    // A box is laid out unless it or an ancestor is hidden (display: none).
    vi.spyOn(HTMLElement.prototype, "getClientRects").mockImplementation(function (this: HTMLElement) {
      return (this.closest("[hidden]") ? [] : [this.getBoundingClientRect()]) as unknown as DOMRectList;
    });
    // Every number is on screen at once.
    vi.stubGlobal(
      "IntersectionObserver",
      class {
        constructor(private readonly callback: IntersectionObserverCallback) {}
        observe(target: Element) {
          this.callback([{ isIntersecting: true, target } as IntersectionObserverEntry], this as unknown as IntersectionObserver);
        }
        disconnect() {}
      },
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    document.documentElement.removeAttribute("data-motion");
  });

  const runFrame = (now: number) => {
    const pending = frames;
    frames = [];
    act(() => pending.forEach((callback) => callback(now)));
  };

  it("counts up inside the final number's width, so nothing beside it moves", () => {
    const view = render(<AnimatedNumber value={4} format={format} countIn={false} />);
    view.rerender(<AnimatedNumber value={16} format={format} countIn={false} />);

    const number = numberIn(view.container);
    expect(number.textContent).toBe("4");
    expect(number.style.width).toBe("20px");
    // The text's start stays where the final number's will be: a start that moves is a layout shift.
    expect(number.style.textAlign).toBe("start");

    runFrame(0);
    runFrame(450);
    expect(Number(number.textContent)).toBeGreaterThan(4);
    expect(number.style.width).toBe("20px");

    runFrame(2000);
    expect(number.textContent).toBe("16");
    // Done: the number sizes itself again (the same width).
    expect(number.style.width).toBe("");
    expect(frames).toHaveLength(0);
  });

  it("changes at once when the count would start wider than it ends", () => {
    const view = render(<AnimatedNumber value={16} format={format} countIn={false} />);
    view.rerender(<AnimatedNumber value={4} format={format} countIn={false} />);

    const number = numberIn(view.container);
    expect(number.textContent).toBe("4");
    expect(number.style.width).toBe("");
    expect(frames).toHaveLength(0);
  });

  it("counts in from zero the first time, within the final width", () => {
    const view = render(<AnimatedNumber value={1920} format={format} />);
    const number = numberIn(view.container);
    expect(number.textContent).toBe("0");
    expect(number.style.width).toBe("40px");
    runFrame(0);
    runFrame(2000);
    expect(number.textContent).toBe("1920");
    expect(number.style.width).toBe("");
  });

  it("counts in React's own text node, which then shows what React renders later", () => {
    const view = render(<AnimatedNumber value={4} format={format} countIn={false} />);
    const text = numberIn(view.container).firstChild;
    view.rerender(<AnimatedNumber value={16} format={format} countIn={false} />);
    runFrame(0);
    runFrame(2000);
    expect(numberIn(view.container).firstChild).toBe(text);
    view.rerender(<AnimatedNumber value={16} format={(value) => `${value} items`} countIn={false} />);
    expect(numberIn(view.container).textContent).toBe("16 items");
  });

  it("shows a value that changed while the number was hidden at once, never a count in a 0 px box", () => {
    const shown = (value: number, hidden: boolean) => (
      <div hidden={hidden}>
        <AnimatedNumber value={value} format={format} countIn={false} />
      </div>
    );
    const view = render(shown(3, true));
    view.rerender(shown(128, true));

    const number = numberIn(view.container);
    expect(number.textContent).toBe("128");
    expect(number.style.width).toBe("");
    expect(frames).toHaveLength(0);

    view.rerender(shown(128, false));
    expect(number.textContent).toBe("128");
    expect(number.style.width).toBe("");
    expect(frames).toHaveLength(0);
  });

  it("keeps still with the cabinet's own Reduce motion", () => {
    document.documentElement.setAttribute("data-motion", "reduce");
    const view = render(<AnimatedNumber value={4} format={format} countIn={false} />);
    view.rerender(<AnimatedNumber value={16} format={format} countIn={false} />);
    expect(numberIn(view.container).textContent).toBe("16");
    expect(frames).toHaveLength(0);
  });
});
