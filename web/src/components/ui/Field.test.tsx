import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { renderInLocale } from "@/test/render";

import { Checkbox, Input } from "./controls";
import { Field, Fieldset } from "./Field";

function NameField({ error, hint, required }: { error?: string; hint?: string; required?: boolean }) {
  const [value, setValue] = useState("");
  return (
    <Field label="Business name" hint={hint} error={error} required={required} optionalLabel={required ? undefined : "optional"}>
      {(control) => <Input {...control} value={value} onChange={(event) => setValue(event.target.value)} />}
    </Field>
  );
}

function describedBy(element: HTMLElement): string[] {
  return (element.getAttribute("aria-describedby") ?? "")
    .split(" ")
    .filter(Boolean)
    .map((id) => document.getElementById(id)?.textContent ?? `missing #${id}`);
}

describe("Field", () => {
  it("labels its control, so a click on the label focuses it and typing reaches it", async () => {
    const user = userEvent.setup();
    renderInLocale(<NameField />);

    await user.click(screen.getByText("Business name"));
    await user.keyboard("Café Tbilisi");

    const input = screen.getByRole("textbox", { name: /Business name/ });
    expect(document.activeElement).toBe(input);
    expect(input).toHaveProperty("value", "Café Tbilisi");
  });

  it("marks a required field for people and for assistive technology", () => {
    renderInLocale(<NameField required />);

    const input = screen.getByRole("textbox", { name: /Business name/ });
    expect(input).toHaveProperty("required", true);
    // The asterisk is decoration: the name stays "Business name".
    expect(screen.getByText("*").getAttribute("aria-hidden")).toBe("true");
    expect(screen.queryByText("(optional)")).toBeNull();
  });

  it("says when a field is optional", () => {
    renderInLocale(<NameField />);

    expect(screen.getByText("(optional)")).toBeTruthy();
    expect(screen.getByRole("textbox", { name: /Business name/ })).toHaveProperty("required", false);
  });

  it("announces its error before its hint and marks the control invalid", () => {
    renderInLocale(<NameField hint="Shown to customers" error="Enter a name" />);

    const input = screen.getByRole("textbox", { name: /Business name/ });
    expect(input.getAttribute("aria-invalid")).toBe("true");
    expect(describedBy(input)).toEqual(["Enter a name", "Shown to customers"]);
  });

  it("is valid again once the error is gone, keeping its hint", () => {
    const view = renderInLocale(<NameField hint="Shown to customers" error="Enter a name" />);

    view.rerender(<NameField hint="Shown to customers" />);

    const input = screen.getByRole("textbox", { name: /Business name/ });
    expect(input.hasAttribute("aria-invalid")).toBe(false);
    expect(describedBy(input)).toEqual(["Shown to customers"]);
    expect(screen.queryByText("Enter a name")).toBeNull();
  });

  it("gives every field its own ids", () => {
    renderInLocale(
      <>
        <NameField error="First" />
        <NameField error="Second" />
      </>,
    );

    const [first, second] = screen.getAllByRole("textbox");
    expect(first?.id).not.toBe(second?.id);
    expect(describedBy(first!)).toEqual(["First"]);
    expect(describedBy(second!)).toEqual(["Second"]);
  });
});

describe("Fieldset", () => {
  it("names a group by its legend and describes it by its error and hint", () => {
    renderInLocale(
      <Fieldset legend="Channels" hint="Where customers write" error="Choose at least one">
        <Checkbox label="Telegram" />
        <Checkbox label="WhatsApp" />
      </Fieldset>,
    );

    const group = screen.getByRole("group", { name: "Channels" });
    expect(describedBy(group)).toEqual(["Choose at least one", "Where customers write"]);
    expect(screen.getAllByRole("checkbox")).toHaveLength(2);
  });
});
