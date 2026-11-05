import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderInLocale } from "@/test/render";

import { VariantField } from "./VariantField";

describe("VariantField", () => {
  it("edits the text without a preview filled with a made-up customer", () => {
    const { container } = renderInLocale(<VariantField language="it" value="Ciao {name}, a presto" onChange={vi.fn()} />);

    expect(screen.getByRole("textbox", { name: /^Text in / })).toBeTruthy();
    expect(container.querySelector("figure")).toBeNull();
    expect(container.textContent).not.toMatch(/Preview|Nino|Giulia/);
  });

  it("inserts a variable where the caret is", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderInLocale(<VariantField language="en" value="Hello !" onChange={onChange} />);
    const text = screen.getByRole<HTMLTextAreaElement>("textbox");
    text.setSelectionRange(6, 6);

    await user.click(screen.getByRole("button", { name: /^Insert Customer's name into the text in / }));
    expect(onChange).toHaveBeenCalledWith("Hello {name}!");
  });
});
