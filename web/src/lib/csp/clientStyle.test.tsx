import { act, render } from "@testing-library/react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NonceProvider } from "@/components/csp/NonceProvider";
import { NoncedStyle } from "@/components/csp/NoncedStyle";
import { BarFill } from "@/components/ui";

import { useMountedAfterHydration } from "./clientStyle";

function Entrance() {
  return <span data-testid="entrance" data-enters={String(useMountedAfterHydration())} />;
}

async function hydrate(element: React.ReactElement) {
  const container = document.createElement("div");
  container.innerHTML = renderToString(element);
  document.body.append(container);
  const recoverable = vi.fn();
  await act(async () => {
    hydrateRoot(container, element, { onRecoverableError: recoverable });
  });
  return { container, recoverable };
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("styles under the Content Security Policy", () => {
  it("leaves a bar's width out of the server's HTML and sets it once hydrated", async () => {
    const html = renderToString(<BarFill percent={40} className="h-full bg-accent-solid" />);
    expect(html).not.toContain("style=");
    expect(html).toContain("w-0");

    const { container, recoverable } = await hydrate(<BarFill percent={40} className="h-full bg-accent-solid" />);

    expect(recoverable).not.toHaveBeenCalled();
    expect((container.firstElementChild as HTMLElement).style.width).toBe("40%");
  });

  it("fills a bar drawn in the browser at once, within its track", () => {
    const { container } = render(<BarFill as="span" percent={140} />);

    expect((container.firstElementChild as HTMLElement).style.width).toBe("100%");
    expect(container.firstElementChild?.tagName).toBe("SPAN");
  });

  it("lets only components that came after hydration play an entrance", async () => {
    const { container } = await hydrate(<Entrance />);
    expect(container.querySelector("[data-testid=entrance]")?.getAttribute("data-enters")).toBe("false");

    const later = render(<Entrance />);
    expect(later.container.querySelector("[data-testid=entrance]")?.getAttribute("data-enters")).toBe("true");
  });

  it("gives a <style> the page's nonce", () => {
    const html = renderToString(
      <NonceProvider nonce="test-nonce-0000">
        <NoncedStyle css="main{color:red}" />
      </NonceProvider>,
    );

    expect(html).toBe('<style nonce="test-nonce-0000">main{color:red}</style>');
  });
});
