/**
 * TimeField and DateField in Hebrew (right to left, week from Sunday) and
 * German (week from Monday, day first): the clock stays 24-hour and reads
 * left to right in both, the calendar starts the week where the language
 * starts it, typed dates follow the language and, right to left, the arrow
 * keys move the way the eye reads the grid.
 */

import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import type { Locale } from "@/i18n/config";
import { renderInLocale, textsIn } from "@/test/render";

import { DateField } from "./DateField";
import { Field } from "./Field";
import { TimeField } from "./TimeField";

const TODAY = "2026-10-06";

function Day({ initial = "", onValue }: { initial?: string; onValue?: (value: string) => void }) {
  const [value, setValue] = useState(initial);
  return (
    <Field label="Day">
      {(control) => (
        <DateField
          {...control}
          value={value}
          today={TODAY}
          onChange={(next) => {
            setValue(next);
            onValue?.(next);
          }}
        />
      )}
    </Field>
  );
}

function Opens({ initial = "" }: { initial?: string }) {
  const [value, setValue] = useState(initial);
  return <Field label="Opens">{(control) => <TimeField {...control} value={value} onChange={setValue} />}</Field>;
}

function openCalendar(locale: Locale) {
  fireEvent.click(screen.getByRole("button", { name: textsIn(locale).t("formFields.date.open") }));
  return screen.getByRole("dialog", { name: textsIn(locale).t("formFields.date.calendar") });
}

describe.each<Locale>(["he", "de"])("TimeField in %s", (locale) => {
  it("keeps a 24-hour clock with no AM/PM, hours before minutes", () => {
    renderInLocale(<Opens initial="20:05" />, { locale });
    const names = textsIn(locale);
    const segments = screen.getAllByRole("spinbutton");
    expect(segments.map((segment) => segment.getAttribute("aria-label"))).toEqual([
      names.t("formFields.time.hours"),
      names.t("formFields.time.minutes"),
    ]);
    expect(segments.map((segment) => (segment as HTMLInputElement).value)).toEqual(["20", "05"]);
    expect(screen.getByRole("group", { name: "Opens" }).getAttribute("dir")).toBe("ltr");
  });
});

describe("DateField in Hebrew and German", () => {
  it.each<[Locale, string]>([
    ["he", "6 באוק׳ 2026"],
    ["de", "06.10.2026"],
  ])("shows the date in %s", (locale, text) => {
    renderInLocale(<Day initial={TODAY} />, { locale });
    expect(screen.getByRole("combobox", { name: "Day" })).toHaveProperty("value", text);
  });

  it.each<[Locale, string[]]>([
    ["he", ["יום א׳", "יום ב׳", "יום ג׳", "יום ד׳", "יום ה׳", "יום ו׳", "שבת"]],
    ["de", ["mo", "di", "mi", "do", "fr", "sa", "so"]],
  ])("starts the week where %s starts it", (locale, weekdays) => {
    renderInLocale(<Day initial={TODAY} />, { locale });
    const calendar = openCalendar(locale);
    const heads = within(calendar).getAllByRole("columnheader").map((cell) => cell.textContent?.toLowerCase().replace(/\.$/, ""));
    expect(heads).toEqual(weekdays.map((day) => day.toLowerCase()));
  });

  it.each<[Locale, string, string]>([
    ["he", "7 באוק׳ 2026", "2026-10-07"],
    ["he", "07.10.2026", "2026-10-07"],
    ["de", "7. Okt. 2026", "2026-10-07"],
    ["de", "07.10.2026", "2026-10-07"],
  ])("takes %s typed as %s", async (locale, typed, iso) => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    renderInLocale(<Day onValue={onValue} />, { locale });
    await user.type(screen.getByRole("combobox", { name: "Day" }), typed);
    expect(onValue).toHaveBeenLastCalledWith(iso);
  });

  it("moves to the previous day on ArrowRight when the page reads right to left", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    renderInLocale(
      <div dir="rtl" style={{ direction: "rtl" }}>
        <Day initial={TODAY} onValue={onValue} />
      </div>,
      { locale: "he" },
    );
    const calendar = openCalendar("he");
    expect(document.activeElement?.getAttribute("data-date")).toBe(TODAY);
    fireEvent.keyDown(within(calendar).getByRole("grid"), { key: "ArrowRight" });
    expect(document.activeElement?.getAttribute("data-date")).toBe("2026-10-05");
    fireEvent.keyDown(within(calendar).getByRole("grid"), { key: "ArrowLeft" });
    fireEvent.keyDown(within(calendar).getByRole("grid"), { key: "ArrowLeft" });
    await user.keyboard("{Enter}");
    expect(onValue).toHaveBeenLastCalledWith("2026-10-07");
  });
});
