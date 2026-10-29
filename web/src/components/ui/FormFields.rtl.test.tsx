/**
 * TimeField and DateField on a page laid out right to left: the layout stays
 * ready for such a language (`<html dir="rtl">`, config.ts LOCALE_DIRECTION)
 * although every cabinet language reads left to right today, so the fields
 * are rendered in Italian under `dir="rtl"`. The clock keeps reading left to
 * right, hours before minutes, and in the calendar the arrow keys move the
 * way the eye reads the grid.
 */

import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import type { Locale } from "@/i18n/config";
import { renderInLocale, textsIn } from "@/test/render";

import { DateField } from "./DateField";
import { Field } from "./Field";
import { TimeField } from "./TimeField";

const TODAY = "2026-10-06";
const LOCALE: Locale = "it";

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

/** The page as a right-to-left language lays it out. */
function RightToLeft({ children }: { children: ReactNode }) {
  return (
    <div dir="rtl" style={{ direction: "rtl" }}>
      {children}
    </div>
  );
}

function openCalendar() {
  fireEvent.click(screen.getByRole("button", { name: textsIn(LOCALE).t("formFields.date.open") }));
  return screen.getByRole("dialog", { name: textsIn(LOCALE).t("formFields.date.calendar") });
}

describe("TimeField on a right-to-left page", () => {
  it("keeps a 24-hour clock with no AM/PM, hours before minutes, reading left to right", () => {
    renderInLocale(
      <RightToLeft>
        <Opens initial="20:05" />
      </RightToLeft>,
      { locale: LOCALE },
    );
    const names = textsIn(LOCALE);
    const segments = screen.getAllByRole("spinbutton");
    expect(segments.map((segment) => segment.getAttribute("aria-label"))).toEqual([
      names.t("formFields.time.hours"),
      names.t("formFields.time.minutes"),
    ]);
    expect(segments.map((segment) => (segment as HTMLInputElement).value)).toEqual(["20", "05"]);
    expect(screen.getByRole("group", { name: "Opens" }).getAttribute("dir")).toBe("ltr");
  });
});

describe("DateField on a right-to-left page", () => {
  it("moves to the previous day on ArrowRight when the page reads right to left", async () => {
    const user = userEvent.setup();
    const onValue = vi.fn();
    renderInLocale(
      <RightToLeft>
        <Day initial={TODAY} onValue={onValue} />
      </RightToLeft>,
      { locale: LOCALE },
    );
    const calendar = openCalendar();
    expect(document.activeElement?.getAttribute("data-date")).toBe(TODAY);
    fireEvent.keyDown(within(calendar).getByRole("grid"), { key: "ArrowRight" });
    expect(document.activeElement?.getAttribute("data-date")).toBe("2026-10-05");
    fireEvent.keyDown(within(calendar).getByRole("grid"), { key: "ArrowLeft" });
    fireEvent.keyDown(within(calendar).getByRole("grid"), { key: "ArrowLeft" });
    await user.keyboard("{Enter}");
    expect(onValue).toHaveBeenLastCalledWith("2026-10-07");
  });
});
