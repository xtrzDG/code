import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import type { Locale } from "@/i18n/config";
import { renderInLocale, textsIn } from "@/test/render";

import { Field } from "./Field";
import { TimeField } from "./TimeField";

function Opens({ initial = "", onValue, step }: { initial?: string; onValue?: (value: string) => void; step?: number }) {
  const [value, setValue] = useState(initial);
  return (
    <Field label="Opens">
      {(control) => (
        <TimeField
          {...control}
          value={value}
          step={step}
          onChange={(next) => {
            setValue(next);
            onValue?.(next);
          }}
        />
      )}
    </Field>
  );
}

const segment = (name: RegExp) => screen.getByRole("spinbutton", { name });

function renderOpens(locale: Locale, props: Parameters<typeof Opens>[0] = {}) {
  const view = renderInLocale(<Opens {...props} />, { locale });
  const names = textsIn(locale);
  return {
    view,
    hours: segment(new RegExp(names.t("formFields.time.hours"))),
    minutes: segment(new RegExp(names.t("formFields.time.minutes"))),
  };
}

describe("TimeField", () => {
  it.each<Locale>(["ru", "ka"])("shows 08:00 with no AM/PM in %s", (locale) => {
    const { hours, minutes } = renderOpens(locale, { initial: "08:00" });
    expect(hours).toHaveProperty("value", "08");
    expect(minutes).toHaveProperty("value", "00");
    expect(screen.queryAllByRole("spinbutton")).toHaveLength(2);
    expect(hours.getAttribute("aria-valuetext")).toBe("08:00");
    expect(document.body.textContent).not.toMatch(/AM|PM/);
  });

  it("shows the English clock with AM and PM", () => {
    renderOpens("en", { initial: "20:30" });
    const period = segment(/AM or PM/);
    expect(period).toHaveProperty("value", "PM");
    expect(segment(/Hours/)).toHaveProperty("value", "08");
    expect(segment(/Hours/).getAttribute("aria-valuetext")).toMatch(/^8:30\sPM$/);
  });

  it("is named by its label and focuses the hours from it", async () => {
    const user = userEvent.setup();
    renderOpens("ru");
    expect(screen.getByRole("group", { name: "Opens" })).toBeTruthy();
    await user.click(screen.getByText("Opens"));
    expect(document.activeElement).toBe(segment(/Opens Часы/));
  });

  it("takes 0830 typed in one go", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    const { hours, minutes } = renderOpens("ru", { onValue });
    await user.click(hours);
    await user.keyboard("0830");
    expect(hours).toHaveProperty("value", "08");
    expect(minutes).toHaveProperty("value", "30");
    expect(onValue).toHaveBeenLastCalledWith("08:30");
    expect(document.activeElement).toBe(minutes);
  });

  it("reads 2030 as 8:30 PM on an English clock", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    const { hours } = renderOpens("en", { onValue });
    await user.click(hours);
    await user.keyboard("2030");
    expect(onValue).toHaveBeenLastCalledWith("20:30");
    expect(segment(/AM or PM/)).toHaveProperty("value", "PM");
    await user.keyboard("a");
    expect(onValue).toHaveBeenLastCalledWith("08:30");
  });

  it("steps the minutes by 15 or 30 with the arrows", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    const { minutes } = renderOpens("ru", { initial: "08:10", onValue });
    await user.click(minutes);
    await user.keyboard("{ArrowUp}");
    expect(onValue).toHaveBeenLastCalledWith("08:15");
    await user.keyboard("{ArrowDown}");
    expect(onValue).toHaveBeenLastCalledWith("08:00");
    await user.keyboard("{ArrowDown}");
    expect(onValue).toHaveBeenLastCalledWith("07:45");
  });

  it("steps by half an hour when asked", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    const { minutes } = renderOpens("ru", { initial: "09:30", onValue, step: 30 });
    await user.click(minutes);
    await user.keyboard("{ArrowUp}");
    expect(onValue).toHaveBeenLastCalledWith("10:00");
  });

  it("starts an empty field at 09:00 and steps hours by one", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    const { hours } = renderOpens("ka", { onValue });
    await user.click(hours);
    await user.keyboard("{ArrowUp}");
    expect(onValue).toHaveBeenLastCalledWith("09:00");
    await user.keyboard("{ArrowUp}");
    expect(onValue).toHaveBeenLastCalledWith("10:00");
  });

  it("empties a segment with Backspace and goes back from an empty one", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    const { hours, minutes } = renderOpens("ru", { initial: "08:30", onValue });
    await user.click(minutes);
    await user.keyboard("{Backspace}");
    expect(onValue).toHaveBeenLastCalledWith("");
    expect(minutes).toHaveProperty("value", "");
    await user.keyboard("{Backspace}");
    expect(document.activeElement).toBe(hours);
    await user.keyboard("{ArrowRight}");
    expect(document.activeElement).toBe(minutes);
  });

  it("takes a pasted time and text a phone keyboard put in", () => {
    const onValue = vi.fn();
    const { hours } = renderOpens("ru", { onValue });
    fireEvent.paste(hours, { clipboardData: { getData: () => "9:45" } });
    expect(onValue).toHaveBeenLastCalledWith("09:45");
    fireEvent.change(hours, { target: { value: "17:20" } });
    expect(onValue).toHaveBeenLastCalledWith("17:20");
  });

  it("takes a new value from outside", () => {
    function Outside() {
      const [value, setValue] = useState("08:00");
      return (
        <>
          <TimeField aria-label="Closes" value={value} onChange={setValue} />
          <button type="button" onClick={() => setValue("22:15")}>
            later
          </button>
        </>
      );
    }
    renderInLocale(<Outside />, { locale: "ru" });
    const group = screen.getByRole("group", { name: "Closes" });
    fireEvent.click(screen.getByText("later"));
    expect(within(group).getAllByRole("spinbutton").map((input) => (input as HTMLInputElement).value)).toEqual(["22", "15"]);
    expect(within(group).getAllByRole("spinbutton")[0]?.getAttribute("aria-label")).toBe("Часы");
  });
});
