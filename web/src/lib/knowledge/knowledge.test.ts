import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/errors";

import {
  emptyKnowledgeForm,
  isEmptyPatch,
  knowledgeCreateBody,
  knowledgeFormFromItem,
  knowledgePatchBody,
  validateKnowledgeForm,
  type KnowledgeForm,
} from "./form";
import {
  countByKind,
  filterKnowledgeItems,
  groupByKind,
  kindHasDuration,
  kindHasPrice,
  orderKinds,
  sortByTitle,
} from "./kinds";
import {
  base64FromDataUrl,
  checkMenuFile,
  confidenceLevel,
  formatFileSize,
  initialImportSelection,
  MENU_UPLOAD_MAX_BYTES,
  menuLinkProblem,
  menuMediaType,
  type ImportedMenuItem,
} from "./menuImport";

const item = (id: string, kind: ImportedMenuItem["item"]["kind"], isActive = true) => ({ id, kind, is_active: isActive });

describe("kinds", () => {
  it("puts the niche's kinds first, then the others without repeats", () => {
    const order = orderKinds(["menu_item", "package", "faq", "policy", "faq"]);
    expect(order.slice(0, 4)).toEqual(["menu_item", "package", "faq", "policy"]);
    expect(order).toHaveLength(8);
    expect(new Set(order).size).toBe(8);
    expect(orderKinds(undefined)[0]).toBe("menu_item");
  });

  it("knows which kinds have prices and durations", () => {
    expect(kindHasPrice("menu_item")).toBe(true);
    expect(kindHasPrice("faq")).toBe(false);
    expect(kindHasPrice("policy")).toBe(false);
    expect(kindHasDuration("service")).toBe(true);
    expect(kindHasDuration("menu_item")).toBe(false);
  });

  it("groups items by kind in the given order and skips empty kinds", () => {
    const items = [item("a", "faq"), item("b", "menu_item"), item("c", "faq"), item("d", "product")];
    const groups = groupByKind(items, ["menu_item", "faq"]);
    expect(groups.map((group) => group.kind)).toEqual(["menu_item", "faq", "product"]);
    expect(groups[1]?.items.map((entry) => entry.id)).toEqual(["a", "c"]);
    expect(countByKind(items)).toEqual({ faq: 2, menu_item: 1, product: 1 });
  });

  it("sorts by title in the UI language", () => {
    const items = [{ title: "Хинкали" }, { title: "apple" }, { title: "Banana" }, { title: "Аджика" }];
    expect(sortByTitle(items, "en").map((item) => item.title)).toEqual(["apple", "Banana", "Аджика", "Хинкали"]);
    // Russian collation puts Cyrillic first.
    expect(sortByTitle(items, "ru").map((item) => item.title)).toEqual(["Аджика", "Хинкали", "apple", "Banana"]);
  });

  it("filters by kind and by whether the assistant uses the item", () => {
    const items = [item("a", "faq"), item("b", "menu_item", false), item("c", "menu_item")];
    expect(filterKnowledgeItems(items, { kind: "all", status: "all" })).toHaveLength(3);
    expect(filterKnowledgeItems(items, { kind: "menu_item", status: "all" }).map((entry) => entry.id)).toEqual(["b", "c"]);
    expect(filterKnowledgeItems(items, { kind: "all", status: "inactive" }).map((entry) => entry.id)).toEqual(["b"]);
    expect(filterKnowledgeItems(items, { kind: "menu_item", status: "active" }).map((entry) => entry.id)).toEqual(["c"]);
  });
});

describe("the item form", () => {
  const form = (patch: Partial<KnowledgeForm>): KnowledgeForm => ({ ...emptyKnowledgeForm("menu_item"), ...patch });

  it("shows minor units as major units of the currency", () => {
    const values = knowledgeFormFromItem(
      { kind: "service", title: "Haircut", body: null, price_minor: 1850, duration_minutes: 45, languages: ["ka"], is_active: false },
      "GEL",
    );
    expect(values).toEqual({
      kind: "service",
      title: "Haircut",
      body: "",
      price: "18.5",
      duration: "45",
      languages: ["ka"],
      isActive: false,
    });
    expect(knowledgeFormFromItem({ kind: "menu_item", title: "Ramen", body: null, price_minor: 1200, duration_minutes: null }, "JPY").price).toBe("1200");
  });

  it("requires a title, an answer for questions and sensible numbers", () => {
    expect(validateKnowledgeForm(form({}), "GEL")).toEqual({ title: "validation.required" });
    expect(validateKnowledgeForm(form({ kind: "faq", title: "Parking?" }), "GEL")).toEqual({ body: "validation.required" });
    expect(validateKnowledgeForm(form({ title: "x", price: "abc" }), "GEL").price).toBe("validation.number");
    expect(validateKnowledgeForm(form({ title: "x", price: "-5" }), "GEL").price).toBe("validation.number");
    expect(validateKnowledgeForm(form({ title: "x", duration: "1.5" }), "GEL").duration).toBe("validation.wholeNumber");
    expect(validateKnowledgeForm(form({ title: "x", duration: "0" }), "GEL").duration).toBe("validation.positive");
    expect(validateKnowledgeForm(form({ title: "x".repeat(301) }), "GEL").title).toBe("validation.tooLong");
    expect(validateKnowledgeForm(form({ title: "x", price: "18,50", duration: "60" }), "GEL")).toEqual({});
  });

  it("refuses more decimals than the currency has", () => {
    expect(validateKnowledgeForm(form({ title: "x", price: "18.5555" }), "GEL").price).toBe("knowledge.form.priceTooPrecise");
    expect(validateKnowledgeForm(form({ title: "x", price: "0.555" }), "GEL").price).toBe("knowledge.form.priceTooPrecise");
    expect(validateKnowledgeForm(form({ title: "x", price: "1500.5" }), "JPY").price).toBe("knowledge.form.priceTooPrecise");
    expect(validateKnowledgeForm(form({ title: "x", price: "1500" }), "JPY")).toEqual({});
    expect(validateKnowledgeForm(form({ title: "x", price: "1.200,50" }), "EUR")).toEqual({});
    expect(validateKnowledgeForm(form({ title: "x", price: "1.255" }), "KWD")).toEqual({});
  });

  it("refuses a lone separator before three digits instead of storing a price 1000 times too low", () => {
    expect(validateKnowledgeForm(form({ title: "x", price: "25.000" }), "IDR").price).toBe("knowledge.form.priceAmbiguous");
    expect(validateKnowledgeForm(form({ title: "x", price: "1,200" }), "USD").price).toBe("knowledge.form.priceAmbiguous");
    expect(validateKnowledgeForm(form({ title: "x", price: "18.555" }), "GEL").price).toBe("knowledge.form.priceAmbiguous");
    expect(validateKnowledgeForm(form({ title: "x", price: "10,000" }), "JPY")).toEqual({});
    expect(knowledgeCreateBody(form({ title: "x", price: "10,000" }), "JPY").price_minor).toBe(10000);
  });

  it("ignores the price of questions and rules", () => {
    expect(validateKnowledgeForm(form({ kind: "policy", title: "Dress code", price: "abc" }), "GEL")).toEqual({});
    expect(knowledgeCreateBody(form({ kind: "policy", title: "Dress code", price: "10" }), "GEL").price_minor).toBeNull();
  });

  it("builds the create body in minor units", () => {
    expect(knowledgeCreateBody(form({ title: " Khachapuri ", body: " Cheese ", price: "18,5", languages: ["ka"] }), "GEL")).toEqual({
      kind: "menu_item",
      title: "Khachapuri",
      body: "Cheese",
      price_minor: 1850,
      duration_minutes: null,
      languages: ["ka"],
      is_active: true,
    });
  });

  it("sends only the changed fields, with null to clear", () => {
    const initial = form({ title: "Khachapuri", body: "Cheese", price: "18.5", duration: "", languages: ["ka", "en"] });
    expect(isEmptyPatch(knowledgePatchBody({ ...initial, languages: ["en", "ka"] }, initial, "GEL"))).toBe(true);
    expect(knowledgePatchBody({ ...initial, price: "18,50" }, initial, "GEL")).toEqual({});
    expect(knowledgePatchBody({ ...initial, price: "", body: " " }, initial, "GEL")).toEqual({ price_minor: null, body: null });
    expect(knowledgePatchBody({ ...initial, title: "Imeruli", isActive: false }, initial, "GEL")).toEqual({
      title: "Imeruli",
      is_active: false,
    });
    expect(knowledgePatchBody({ ...initial, kind: "faq" }, initial, "GEL")).toEqual({ kind: "faq", price_minor: null });
    expect(knowledgePatchBody({ ...initial, duration: "30", languages: [] }, initial, "GEL")).toEqual({
      duration_minutes: 30,
      languages: [],
    });
  });
});

describe("menu import", () => {
  const draft = (id: string, confidence: number): ImportedMenuItem => ({
    confidence,
    is_currency_mismatch: false,
    item: { id, kind: "menu_item", title: id },
  });

  it("rates the reader's confidence", () => {
    expect(confidenceLevel(0.95)).toBe("high");
    expect(confidenceLevel(0.8)).toBe("high");
    expect(confidenceLevel(0.5)).toBe("medium");
    expect(confidenceLevel(0.49)).toBe("low");
  });

  it("preselects the drafts it was fairly sure of", () => {
    expect([...initialImportSelection([draft("a", 0.9), draft("b", 0.3), draft("c", 0.6)])]).toEqual(["a", "c"]);
  });

  it("finds the media type from the browser or the extension", () => {
    expect(menuMediaType("menu.jpg", "image/jpeg")).toBe("image/jpeg");
    expect(menuMediaType("menu.JPG", "")).toBe("image/jpeg");
    expect(menuMediaType("menu.csv", "application/vnd.ms-excel")).toBe("text/csv");
    expect(menuMediaType("menu.txt", "text/plain;charset=utf-8")).toBe("text/plain");
    expect(menuMediaType("photo.heic", "image/heic")).toBeNull();
    expect(menuMediaType("menu", "")).toBeNull();
  });

  it("checks type and size before reading the file", () => {
    expect(checkMenuFile({ name: "menu.pdf", type: "application/pdf", size: 2048 })).toEqual({ ok: true, mediaType: "application/pdf" });
    expect(checkMenuFile({ name: "menu.docx", type: "application/msword", size: 2048 })).toEqual({
      ok: false,
      error: "knowledge.import.errors.fileType",
    });
    expect(checkMenuFile({ name: "menu.png", type: "image/png", size: 0 })).toEqual({ ok: false, error: "knowledge.import.errors.fileEmpty" });
    expect(checkMenuFile({ name: "menu.png", type: "image/png", size: MENU_UPLOAD_MAX_BYTES + 1 })).toEqual({
      ok: false,
      error: "knowledge.import.errors.fileTooLarge",
    });
  });

  it("strips the data URL prefix and formats sizes", () => {
    expect(base64FromDataUrl("data:image/png;base64,QUJD")).toBe("QUJD");
    expect(base64FromDataUrl("QUJD")).toBe("QUJD");
    expect(formatFileSize(512, "en")).toBe("512 B");
    expect(formatFileSize(1536, "en")).toBe("1.5 KB");
    expect(formatFileSize(3 * 1024 * 1024, "ru")).toBe("3 MB");
  });
});

describe("menu link problems", () => {
  const refused = (status: number, code: string, details: string[] = []) =>
    new ApiError({ status, code: "validation_failed", reasons: [{ code, message: "", details }] });

  it("reads the reason code of a link the API could not read", () => {
    expect(menuLinkProblem(refused(422, "menu_link_invalid", ["not_public"]))).toEqual({ code: "menu_link_invalid", status: null });
    expect(menuLinkProblem(refused(422, "menu_link_unreachable", ["timeout"]))).toEqual({ code: "menu_link_unreachable", status: null });
    expect(menuLinkProblem(refused(422, "menu_link_unreachable", ["http_status:404"]))).toEqual({
      code: "menu_link_unreachable",
      status: 404,
    });
    expect(menuLinkProblem(refused(422, "menu_link_unreadable", ["media_type:application/zip"]))).toEqual({
      code: "menu_link_unreadable",
      status: null,
    });
  });

  it("leaves other failures to the generic message", () => {
    expect(menuLinkProblem(new ApiError({ status: 502, code: "external_service_error" }))).toBeNull();
    expect(menuLinkProblem(new ApiError({ status: 422, code: "validation_failed" }))).toBeNull();
    expect(menuLinkProblem(refused(422, "something_else"))).toBeNull();
    expect(menuLinkProblem(new Error("network"))).toBeNull();
  });
});
