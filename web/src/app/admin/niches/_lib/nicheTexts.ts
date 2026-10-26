/**
 * Pure helpers of the niche template editor (/admin/niches): the wording a
 * form starts from, the checks the API makes too (one line, no HTML, the
 * field's length, the code text's placeholders), the draft's body, what the
 * preview shows and how each field is named.
 */

import type { RequestBody, Schema } from "@/api/types";
import type { MessageKey, MessageValues } from "@/i18n/translate";

export type NicheTextEditor = Schema<"NicheTextEditorView">;
export type NicheTextField = Schema<"NicheTextFieldView">;
export type NicheTextQuestion = Schema<"NicheTextQuestionView">;
type NicheTextSection = Schema<"NicheTextSection">;
export type NicheTextRelease = Schema<"NicheTextReleaseView">;
export type NicheTextStatus = Schema<"NicheTextStatusView">;
export type DraftBody = RequestBody<"/v1/admin/niche-templates/{niche_key}/draft", "put">;

/** The admin's wording by field key ("" keeps the code's text). */
export type FormValues = Readonly<Record<string, string>>;

const SECTION_ORDER: readonly NicheTextSection[] = ["niche", "question", "rules", "starters"];

export type TextProblem =
  | { kind: "html" }
  | { kind: "lineBreak" }
  | { kind: "tooLong"; max: number }
  | { kind: "placeholders"; names: string };

const HTML_TAG = /<\s*[A-Za-z/!?]/;
const PLACEHOLDER = /\{([a-z_]+)\}/g;

/** The wording the form starts from: the waiting draft's, else the published one. */
export function startingValues(editor: NicheTextEditor): FormValues {
  return Object.fromEntries(
    editor.fields.map((field) => [field.field_key, (editor.status.has_draft ? field.draft_text : field.published_text) ?? ""]),
  );
}

export function isDirty(values: FormValues, start: FormValues): boolean {
  return Object.keys(start).some((key) => (values[key] ?? "").trim() !== (start[key] ?? "").trim());
}

function placeholdersOf(text: string): string[] {
  return [...new Set([...text.matchAll(PLACEHOLDER)].map((match) => match[1] ?? ""))].sort();
}

/** The code's text owners read in this language today. */
function codeText(field: NicheTextField): string {
  return field.code_text ?? field.english_text;
}

/** Why the wording cannot be saved (null: it can; empty keeps the code's text). */
export function textProblem(field: NicheTextField, value: string): TextProblem | null {
  const text = value.trim();
  if (text === "") {
    return null;
  }
  if (/[\r\n]/.test(text)) {
    return { kind: "lineBreak" };
  }
  if (HTML_TAG.test(text)) {
    return { kind: "html" };
  }
  if (text.length > field.max_length) {
    return { kind: "tooLong", max: field.max_length };
  }
  const expected = placeholdersOf(codeText(field));
  if (placeholdersOf(text).join() !== expected.join()) {
    return { kind: "placeholders", names: expected.map((name) => `{${name}}`).join(", ") || "—" };
  }
  return null;
}

/** The message of a problem, for `t`. */
export function problemMessage(problem: TextProblem): [MessageKey, MessageValues] {
  switch (problem.kind) {
    case "html":
      return ["adminNiches.editor.errors.html", {}];
    case "lineBreak":
      return ["adminNiches.editor.errors.lineBreak", {}];
    case "tooLong":
      return ["adminNiches.editor.errors.tooLong", { max: problem.max }];
    case "placeholders":
      return ["adminNiches.editor.errors.placeholders", { names: problem.names }];
  }
}

export function hasProblems(editor: NicheTextEditor, values: FormValues): boolean {
  return editor.fields.some((field) => textProblem(field, values[field.field_key] ?? "") !== null);
}

/** The PUT …/draft body of the form's language: every field with its own wording. */
export function draftBody(editor: NicheTextEditor, values: FormValues): DraftBody {
  return {
    language: editor.language,
    texts: editor.fields
      .map((field) => ({ field_key: field.field_key, text: (values[field.field_key] ?? "").trim() }))
      .filter((text) => text.text !== ""),
  };
}

/** What an owner reads for the field with the form's wording. */
export function shownText(field: NicheTextField | undefined, values: FormValues): string {
  if (!field) {
    return "";
  }
  return (values[field.field_key] ?? "").trim() || codeText(field);
}

/** The fields of one part of the form: the niche, one question, the rules, the starters. */
export interface FieldGroup {
  section: NicheTextSection;
  questionKey: string | null;
  fields: NicheTextField[];
}

export function fieldGroups(editor: NicheTextEditor): FieldGroup[] {
  const groups: FieldGroup[] = [];
  for (const section of SECTION_ORDER) {
    for (const field of editor.fields.filter((item) => item.section === section)) {
      const questionKey = field.question_key ?? null;
      const last = groups.at(-1);
      if (last && last.section === section && last.questionKey === questionKey) {
        last.fields.push(field);
      } else {
        groups.push({ section, questionKey, fields: [field] });
      }
    }
  }
  return groups;
}

function words(key: string): string {
  return key.replaceAll("_", " ");
}

/** Which text of the niche a field is ("Hint", "Choice “separate hall”"). */
export function fieldCaption(fieldKey: string): [MessageKey, MessageValues] {
  const parts = fieldKey.split(".");
  const [first = "", second = "", third = "", fourth = ""] = parts;
  const fixed: Record<string, MessageKey> = {
    name: "adminNiches.editor.fields.name",
    description: "adminNiches.editor.fields.description",
    resource_noun: "adminNiches.editor.fields.resourceNoun",
    "starters.tone": "adminNiches.editor.fields.tone",
    "starters.cancellation_policy": "adminNiches.editor.fields.cancellationPolicy",
    "starters.resource_name": "adminNiches.editor.fields.resourceName",
  };
  const known = fixed[fieldKey];
  if (known) {
    return [known, {}];
  }
  if (first === "questions" && third === "label") {
    return ["adminNiches.editor.fields.label", {}];
  }
  if (first === "questions" && third === "hint") {
    return ["adminNiches.editor.fields.hint", {}];
  }
  if (first === "questions" && third === "choices") {
    return ["adminNiches.editor.fields.choice", { choice: words(fourth) }];
  }
  if (first === "handoff_rules" || first === "forbidden_rules") {
    const key = first === "handoff_rules" ? "handoffRule" : "forbiddenRule";
    return [`adminNiches.editor.fields.${key}`, { position: second }];
  }
  if (first === "starters" && second === "faq") {
    const key = fourth === "answer" ? "faqAnswer" : "faqQuestion";
    return [`adminNiches.editor.fields.${key}`, { entry: words(third) }];
  }
  if (first === "starters" && second === "offers") {
    return ["adminNiches.editor.fields.offerTitle", { entry: words(third) }];
  }
  return ["adminNiches.editor.fields.unknown", { key: fieldKey }];
}
