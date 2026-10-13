import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MotionPreferenceProvider } from "./MotionPreference";
import { morphName, SharedMorph } from "./SharedMorph";

/*
 * React's <ViewTransition>, reduced to what it was asked: the name both ends
 * of a morph share, and how they animate. jsdom lays nothing out, so React
 * never starts a transition there; the morph itself is checked in a browser
 * (e2e/motion-budget.spec.ts counts the view transitions a row's tap starts).
 */
vi.mock("react", async (importOriginal) => {
  const react = await importOriginal<Record<string, unknown>>();
  return {
    ...react,
    ViewTransition: ({ name, share, default: fallback, children }: { name: string; share: string; default: string; children: ReactNode }) => (
      <div data-view-transition={name} data-share={share} data-default={fallback}>
        {children}
      </div>
    ),
  };
});

function setViewTransitions(isSupported: boolean) {
  if (isSupported) {
    Object.defineProperty(document, "startViewTransition", { value: () => undefined, configurable: true, writable: true });
  } else {
    Reflect.deleteProperty(document, "startViewTransition");
  }
}

/** The view-transition names on the page, with how each one animates. */
function named(container: HTMLElement) {
  return [...container.querySelectorAll<HTMLElement>("[data-view-transition]")].map((node) => ({ ...node.dataset }));
}

const ROW_ID = "c_01H8";

/** The inbox row's customer and the open conversation's header, as InboxRowItem and ConversationTopBar name them. */
function RowAndHeader({ isOpen }: { isOpen: boolean }) {
  return (
    <>
      <SharedMorph name={morphName("conversation-name", ROW_ID)} active={!isOpen}>
        <span>Nino</span>
      </SharedMorph>
      {isOpen ? (
        <SharedMorph name={morphName("conversation-name", ROW_ID)}>
          <h1>Nino</h1>
        </SharedMorph>
      ) : null}
    </>
  );
}

describe("the morph from an inbox row to the conversation header", () => {
  afterEach(() => {
    setViewTransitions(false);
  });

  it("pairs the row and the header under one name, morphing between them and nothing else", () => {
    setViewTransitions(true);
    const view = render(<RowAndHeader isOpen={false} />);
    const expected = { viewTransition: "aw-conversation-name-c_01H8", share: "morph", default: "none" };
    expect(named(view.container)).toEqual([expected]);

    // Open: the row gives up the name and the header alone holds it, so the pair is unambiguous.
    view.rerender(<RowAndHeader isOpen />);
    expect(named(view.container)).toEqual([expected]);
    expect(view.container.querySelector("[data-view-transition] h1")).not.toBeNull();
  });

  it("names nothing where the browser cannot morph, or with reduced motion", () => {
    const plain = render(<RowAndHeader isOpen={false} />);
    expect(named(plain.container)).toEqual([]);

    setViewTransitions(true);
    const calm = render(
      <MotionPreferenceProvider initialPreference="reduce">
        <RowAndHeader isOpen />
      </MotionPreferenceProvider>,
    );
    expect(named(calm.container)).toEqual([]);
  });
});
