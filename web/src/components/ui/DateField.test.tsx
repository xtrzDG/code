import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import type { Locale } from "@/i18n/config";
import { renderInLocale, textsIn } from "@/test/render";

import { DateField } from "./DateField";
import { DateTimeField } from "./DateTimeField";
import { Field } from "./Field";

const TODAY = "2026-10-06";

function Day({
  initial = "",
  onValue,
  min,
  max,
  clearable,
}: {
  initial?: string;
  onValue?: (value: string) => void;
  min?: string;
  max?: string;
  clearable?: boolean;
}) {
  const [value, setValue] = useState(initial);
  return (
    <Field label="Day">
      {(control) => (
        <DateField
          {...control}
          value={value}
          today={TODAY}
          min={min}
          max={max}
          clearable={clearable}
          onChange={(next) => {
            setValue(next);
            onValue?.(next);
          }}
        />
      )}
    </Field>
  );
}

function openCalendar(locale: Locale) {
  fireEvent.click(screen.getByRole("button", { name: textsIn(locale).t("formFields.date.open") }));
  return screen.getByRole("dialog", { name: textsIn(locale).t("formFields.date.calendar") });
}

describe("DateField", () => {
  it.each<[Locale, string]>([
    ["ru", "6 окт. 2026 г."],
    ["ka", "6 ოქტ. 2026"],
    ["en", "Oct 6, 2026"],
  ])("shows the date in %s, not mm/dd/yyyy", (locale, text) => {
    renderInLocale(<Day initial={TODAY} />, { locale });
    expect(screen.getByRole("combobox", { name: "Day" })).toHaveProperty("value", text);
  });

  it.each<[Locale, string[]]>([
    ["ru", ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]],
    ["en", ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]],
  ])("starts the week where %s starts it", (locale, weekdays) => {
    renderInLocale(<Day initial={TODAY} />, { locale });
    const calendar = openCalendar(locale);
    const heads = within(calendar).getAllByRole("columnheader").map((cell) => cell.textContent?.toLowerCase());
    expect(heads).toEqual(weekdays.map((day) => day.toLowerCase()));
  });

  it("titles the month in the cabinet's language and marks today and the chosen day", () => {
    renderInLocale(<Day initial="2026-10-20" />, { locale: "ka" });
    const calendar = openCalendar("ka");
    expect(within(calendar).getByText("ოქტომბერი, 2026")).toBeTruthy();
    const today = within(calendar).getByRole("button", { current: "date" });
    expect(today.textContent).toBe("6");
    expect(within(calendar).getByRole("gridcell", { selected: true }).textContent).toBe("20");
  });

  it("picks a day with the keyboard and stores ISO", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    renderInLocale(<Day initial={TODAY} onValue={onValue} />, { locale: "ru" });
    const input = screen.getByRole("combobox", { name: "Day" });
    await user.click(input);
    await user.keyboard("{ArrowDown}");
    expect(document.activeElement?.getAttribute("data-date")).toBe(TODAY);
    await user.keyboard("{ArrowRight}{ArrowDown}{Enter}");
    expect(onValue).toHaveBeenLastCalledWith("2026-10-14");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(input);
    expect(input).toHaveProperty("value", "14 окт. 2026 г.");
  });

  it("moves by months and closes on Escape without a change", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    renderInLocale(<Day initial={TODAY} onValue={onValue} />, { locale: "en" });
    const calendar = openCalendar("en");
    await user.keyboard("{PageDown}");
    expect(within(calendar).getByText("November 2026")).toBeTruthy();
    await user.click(within(calendar).getByRole("button", { name: "Previous month" }));
    await user.click(within(calendar).getByRole("button", { name: "Previous month" }));
    expect(within(calendar).getByText("September 2026")).toBeTruthy();
    fireEvent.keyDown(within(calendar).getByRole("grid"), { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(onValue).not.toHaveBeenCalled();
  });

  it("does not pick a day outside the bounds", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    renderInLocale(<Day min={TODAY} max="2026-10-31" onValue={onValue} />, { locale: "en" });
    const calendar = openCalendar("en");
    const past = within(calendar).getByRole("button", { name: /October 5, 2026/ });
    expect(past.getAttribute("aria-disabled")).toBe("true");
    await user.click(past);
    expect(onValue).not.toHaveBeenCalled();
    expect((within(calendar).getByRole("button", { name: "Previous month" }) as HTMLButtonElement).disabled).toBe(true);
    await user.click(within(calendar).getByRole("button", { name: "Today" }));
    expect(onValue).toHaveBeenLastCalledWith(TODAY);
  });

  it("clears a filter's date", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    renderInLocale(<Day initial={TODAY} clearable onValue={onValue} />, { locale: "ru" });
    const calendar = openCalendar("ru");
    await user.click(within(calendar).getByRole("button", { name: "Очистить" }));
    expect(onValue).toHaveBeenLastCalledWith("");
  });

  it("takes a typed date once it is whole, and goes back on nonsense", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    renderInLocale(<Day initial={TODAY} onValue={onValue} />, { locale: "ru" });
    const input = screen.getByRole("combobox", { name: "Day" });
    await user.clear(input);
    expect(onValue).toHaveBeenLastCalledWith("");
    await user.type(input, "07.10.20");
    expect(onValue).toHaveBeenCalledTimes(1);
    await user.type(input, "26");
    expect(onValue).toHaveBeenLastCalledWith("2026-10-07");
    await user.tab();
    expect(input).toHaveProperty("value", "7 окт. 2026 г.");
    await user.clear(input);
    await user.type(input, "завтра");
    await user.tab();
    expect(input).toHaveProperty("value", "");
  });

  it("opens the month instead of the keyboard on a touch", () => {
    renderInLocale(<Day initial={TODAY} />, { locale: "en" });
    fireEvent.pointerDown(screen.getByRole("combobox", { name: "Day" }), { pointerType: "touch" });
    expect(screen.getByRole("dialog", { name: "Calendar" })).toBeTruthy();
  });
});

describe("DateTimeField", () => {
  function Starts({ onValue }: { onValue: (value: string) => void }) {
    const [value, setValue] = useState("2026-10-06T09:30");
    return (
      <Field label="Starts">
        {(control) => (
          <DateTimeField
            {...control}
            value={value}
            onChange={(next) => {
              setValue(next);
              onValue(next);
            }}
          />
        )}
      </Field>
    );
  }

  it("keeps the date and the time under one label, and says when one is missing", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    renderInLocale(<Starts onValue={onValue} />, { locale: "ru" });
    expect(screen.getByRole("combobox", { name: "Starts" })).toHaveProperty("value", "6 окт. 2026 г.");
    const minutes = screen.getByRole("spinbutton", { name: "Starts Минуты" });
    await user.click(minutes);
    await user.keyboard("{ArrowUp}");
    expect(onValue).toHaveBeenLastCalledWith("2026-10-06T09:45");
    await user.keyboard("{Backspace}");
    expect(onValue).toHaveBeenLastCalledWith("2026-10-06T");
    await user.clear(screen.getByRole("combobox", { name: "Starts" }));
    expect(onValue).toHaveBeenLastCalledWith("");
  });
});
