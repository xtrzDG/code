import { describe, expect, it } from "vitest";

import { findPhysicalClasses, logicalClass, toLogicalClasses } from "./logicalClasses";

describe("the logical twin of a class", () => {
  it("turns margins, paddings and insets to the start and end of the text", () => {
    expect(logicalClass("ml-2")).toBe("ms-2");
    expect(logicalClass("mr-auto")).toBe("me-auto");
    expect(logicalClass("pl-2.5")).toBe("ps-2.5");
    expect(logicalClass("pr-[3px]")).toBe("pe-[3px]");
    expect(logicalClass("left-0")).toBe("start-0");
    expect(logicalClass("right-1/2")).toBe("end-1/2");
    expect(logicalClass("left-full")).toBe("start-full");
    expect(logicalClass("right-(--gap)")).toBe("end-(--gap)");
    expect(logicalClass("scroll-pl-4")).toBe("scroll-ps-4");
    expect(logicalClass("scroll-mr-px")).toBe("scroll-me-px");
  });

  it("keeps variants, the negative sign and the important mark", () => {
    expect(logicalClass("md:hover:-ml-2")).toBe("md:hover:-ms-2");
    expect(logicalClass("max-[359px]:pl-2.5")).toBe("max-[359px]:ps-2.5");
    expect(logicalClass("!pr-4")).toBe("!pe-4");
    expect(logicalClass("pr-4!")).toBe("pe-4!");
    expect(logicalClass("focus:left-3")).toBe("focus:start-3");
    expect(logicalClass("[&>li]:pl-5")).toBe("[&>li]:ps-5");
  });

  it("turns borders, corners, text alignment and floats", () => {
    expect(logicalClass("border-l")).toBe("border-s");
    expect(logicalClass("border-r-2")).toBe("border-e-2");
    expect(logicalClass("border-l-warning")).toBe("border-s-warning");
    expect(logicalClass("lg:border-l")).toBe("lg:border-s");
    expect(logicalClass("rounded-l")).toBe("rounded-s");
    expect(logicalClass("rounded-r-lg")).toBe("rounded-e-lg");
    expect(logicalClass("rounded-tl-md")).toBe("rounded-ss-md");
    expect(logicalClass("rounded-tr-none")).toBe("rounded-se-none");
    expect(logicalClass("rounded-bl-md")).toBe("rounded-es-md");
    expect(logicalClass("rounded-br-[6px]")).toBe("rounded-ee-[6px]");
    expect(logicalClass("text-left")).toBe("text-start");
    expect(logicalClass("sm:text-right")).toBe("sm:text-end");
    expect(logicalClass("float-left")).toBe("float-start");
    expect(logicalClass("clear-right")).toBe("clear-end");
  });

  it("leaves classes that name no side, or name it under rtl: or ltr:", () => {
    for (const token of ["ms-2", "px-4", "inset-x-0", "rounded-lg", "border-line", "text-start", "space-x-2", "translate-x-2"]) {
      expect(logicalClass(token), token).toBeNull();
    }
    expect(logicalClass("rtl:left-2")).toBeNull();
    expect(logicalClass("md:ltr:pl-3")).toBeNull();
  });

  it("does not read words or style keys as classes", () => {
    for (const token of ["left", "right", "left-to-right", "right-most", "left:", "border-left", "constructor", "-text-left", "-border-l", "-rounded-l"]) {
      expect(logicalClass(token), token).toBeNull();
    }
    expect(logicalClass("rounded-l-huge")).toBeNull();
    expect(logicalClass("pl-wide")).toBeNull();
  });
});

describe("a source file", () => {
  const source = [
    'const a = cn("flex pl-3", active && "mr-2");',
    '<span className="absolute top-1/2 left-1/2 -translate-x-1/2" />',
    '<p className={`text-left ${x}`}>left to right</p>',
    "const style = { left: 0 };",
  ].join("\n");

  it("lists its physical classes with their lines", () => {
    expect(findPhysicalClasses(source)).toEqual([
      { line: 1, found: "pl-3", logical: "ps-3" },
      { line: 1, found: "mr-2", logical: "me-2" },
      { line: 3, found: "text-left", logical: "text-start" },
    ]);
  });

  it("is rewritten in place, keeping the centring idiom and everything else", () => {
    expect(toLogicalClasses(source)).toBe(
      [
        'const a = cn("flex ps-3", active && "me-2");',
        '<span className="absolute top-1/2 left-1/2 -translate-x-1/2" />',
        '<p className={`text-start ${x}`}>left to right</p>',
        "const style = { left: 0 };",
      ].join("\n"),
    );
    expect(toLogicalClasses("plain text")).toBe("plain text");
  });

  it("rewrites several classes on one line from the end, so columns stay right", () => {
    expect(toLogicalClasses('"pl-1 pr-10 ml-auto"')).toBe('"ps-1 pe-10 ms-auto"');
  });
});
