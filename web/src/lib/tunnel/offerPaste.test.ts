import { describe, expect, it } from "vitest";

import { MAX_PASTED_LINES, parsePastedOffer } from "./offerPaste";

describe("an offer pasted from a spreadsheet", () => {
  it("is a single value when there is one line without tabs", () => {
    expect(parsePastedOffer("Khachapuri")).toBeNull();
    expect(parsePastedOffer("Khachapuri\n")).toBeNull();
  });

  it("reads name, price and duration from tab-separated lines", () => {
    expect(parsePastedOffer("Haircut\t35 €\t45 min\r\nColouring\t1 200,50\t1:30\nBeard trim\t\t\n")).toEqual([
      { title: "Haircut", price: "35", duration: "45" },
      { title: "Colouring", price: "1 200,50", duration: "90" },
      { title: "Beard trim", price: "", duration: "" },
    ]);
    expect(parsePastedOffer("Khinkali\t1,20 ₾")).toEqual([{ title: "Khinkali", price: "1,20", duration: "" }]);
  });

  it("leaves out a heading line and lines without a name", () => {
    expect(parsePastedOffer("Name\tPrice\tMinutes\nLobio\t12\n\n\t5\nMtsvadi\t18")).toEqual([
      { title: "Lobio", price: "12", duration: "" },
      { title: "Mtsvadi", price: "18", duration: "" },
    ]);
  });

  it("takes a plain list as names", () => {
    expect(parsePastedOffer("Lobio\nMtsvadi")).toEqual([
      { title: "Lobio", price: "", duration: "" },
      { title: "Mtsvadi", price: "", duration: "" },
    ]);
  });

  it("keeps a heading-looking first line when it is the only one", () => {
    expect(parsePastedOffer("Wine\tby the glass")).toEqual([{ title: "Wine", price: "", duration: "" }]);
  });

  it("adds at most a menu's worth of lines and cuts long names", () => {
    const many = Array.from({ length: MAX_PASTED_LINES + 5 }, (_, index) => `Dish ${index}\t${index}`).join("\n");
    expect(parsePastedOffer(many)).toHaveLength(MAX_PASTED_LINES);
    expect(parsePastedOffer(`${"x".repeat(250)}\t1`)?.[0]?.title).toHaveLength(200);
  });
});
