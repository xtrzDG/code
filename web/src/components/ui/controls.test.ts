import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Input, Textarea } from "./controls";

describe("free text controls", () => {
  it("let typed text set its own direction", () => {
    expect(renderToStaticMarkup(createElement(Input, { defaultValue: "مطعم" }))).toContain('dir="auto"');
    expect(renderToStaticMarkup(createElement(Input, { type: "search" }))).toContain('dir="auto"');
    expect(renderToStaticMarkup(createElement(Textarea, { defaultValue: "שלום" }))).toContain('dir="auto"');
  });

  it("leave numbers, phones and addresses to the page direction", () => {
    for (const type of ["tel", "email", "number", "url", "password"]) {
      expect(renderToStaticMarkup(createElement(Input, { type }))).not.toContain("dir=");
    }
  });

  it("keep a direction the caller sets", () => {
    expect(renderToStaticMarkup(createElement(Input, { dir: "ltr" }))).toContain('dir="ltr"');
    expect(renderToStaticMarkup(createElement(Textarea, { dir: "rtl" }))).toContain('dir="rtl"');
  });
});
