import { render } from "@testing-library/react";
import { MotionConfigContext } from "motion/react";
import { useContext } from "react";
import { describe, expect, it } from "vitest";

import { NonceProvider } from "@/components/csp/NonceProvider";

import { MotionProvider } from "./MotionProvider";

function NonceOfMotion() {
  return <output>{useContext(MotionConfigContext).nonce ?? "none"}</output>;
}

describe("MotionProvider", () => {
  it("hands the page's nonce to motion, whose popLayout writes a <style> element", () => {
    const { container } = render(
      <NonceProvider nonce="test-nonce-0000">
        <MotionProvider>
          <NonceOfMotion />
        </MotionProvider>
      </NonceProvider>,
    );

    expect(container.querySelector("output")?.textContent).toBe("test-nonce-0000");
  });
});
