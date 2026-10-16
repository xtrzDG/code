import { describe, expect, it } from "vitest";

import {
  buildStaffTemplatesBody,
  isSameTemplates,
  newTemplateRow,
  nextTemplateLanguage,
  savedStaffTemplates,
  staffTemplatesKey,
  templateLanguageCode,
} from "./staffTemplates";

const template = (language_code: string, name = "staff_reply") => ({ language_code, name });

describe("WhatsApp templates for late staff replies", () => {
  it("writes languages the way WhatsApp does", () => {
    expect(templateLanguageCode("pt-br")).toBe("pt_BR");
    expect(templateLanguageCode(" KA ")).toBe("ka");
    expect(templateLanguageCode("en_us")).toBe("en_US");
  });

  it("saves one template per language, dropping empty rows", () => {
    const rows = [newTemplateRow("ka", "staff_reply"), newTemplateRow("", ""), newTemplateRow("pt-br", " staff_pt ")];

    expect(buildStaffTemplatesBody(rows)).toEqual({
      ok: true,
      body: { templates: [template("ka"), template("pt_BR", "staff_pt")] },
    });
    expect(buildStaffTemplatesBody([])).toEqual({ ok: true, body: { templates: [] } });
  });

  it("names what to fix in each row", () => {
    const missing = newTemplateRow("ru", "");
    const wrong = newTemplateRow("georgian", "Staff Reply");
    const twice = newTemplateRow("ka", "other");
    const first = newTemplateRow("ka", "staff_reply");

    const result = buildStaffTemplatesBody([first, missing, wrong, twice]);

    expect(result).toEqual({
      ok: false,
      errors: {
        [missing.key]: { name: "required" },
        [wrong.key]: { language: "language", name: "name" },
        [twice.key]: { language: "duplicate" },
      },
    });
  });

  it("flags a repeated language even when its first row has another mistake", () => {
    const first = newTemplateRow("de", "Staff Reply");
    const again = newTemplateRow("de", "staff_reply_pt");

    expect(buildStaffTemplatesBody([first, again])).toEqual({
      ok: false,
      errors: { [first.key]: { name: "name" }, [again.key]: { language: "duplicate" } },
    });
  });

  it("reads a channel saved by the previous release with its single template", () => {
    expect(savedStaffTemplates({ staff_reply_template: template("ru") })).toEqual([template("ru")]);
    expect(savedStaffTemplates({ staff_reply_templates: [template("ka"), template("he")], staff_reply_template: template("ka") })).toEqual(
      [template("ka"), template("he")],
    );
    expect(savedStaffTemplates({})).toEqual([]);
    expect(staffTemplatesKey({ staff_reply_templates: [template("ka"), template("he", "staff_he")] })).toBe(
      "ka:staff_reply,he:staff_he",
    );
  });

  it("offers the next business language without a template on a new row", () => {
    expect(nextTemplateLanguage(["ka", "ru", "en"], "ka", [newTemplateRow("ka", "a")])).toBe("ru");
    expect(nextTemplateLanguage(["pt-BR"], "pt-BR", [])).toBe("pt_BR");
    expect(nextTemplateLanguage(["ka"], "ka", [newTemplateRow("ka", "a")])).toBe("");
  });

  it("knows when the rows say what is saved", () => {
    const saved = [template("ka"), template("ru")];
    expect(isSameTemplates([newTemplateRow("ru", "staff_reply"), newTemplateRow("ka", "staff_reply")], saved)).toBe(true);
    expect(isSameTemplates([newTemplateRow("ka", "staff_reply")], saved)).toBe(false);
    expect(isSameTemplates([newTemplateRow("ka", "Bad Name")], saved)).toBe(false);
  });
});
