/**
 * A translated sentence that names someone's own words ("Handled by
 * {name}", "Booked for {customer}"), cut into the interface's text and the
 * user values, so each value can be shown in its own `data-user-content`
 * element (`UserSentence` in the UI kit) while the sentence around it stays
 * the interface's: the e2e suite's check for untranslated interface text
 * (e2e/support/consoleClean.ts) reads the sentence and skips the values.
 *
 * The template is the translation with the user placeholders left in it
 * (`t(key)` keeps a placeholder it has no value for); other placeholders
 * may already be filled. Like `interpolate`, a value that ends with a full
 * stop takes the place of the template's full stop right after it.
 */

export type SentencePart = { kind: "text"; text: string } | { kind: "value"; name: string; value: string };

/**
 * A translated sentence with its user placeholders left in (`text`) and the
 * user values they stand for: `UserSentence` shows it, `interpolate(text,
 * values)` says it as one string.
 */
export interface SentenceWithUserValues {
  text: string;
  values: Readonly<Record<string, string>>;
}

/** A sentence of the interface's own words only. */
export function interfaceSentence(text: string): SentenceWithUserValues {
  return { text, values: {} };
}

/** Someone's own words alone (an address, a model's summary), as a sentence of one user value. */
export function userWords(words: string): SentenceWithUserValues {
  return { text: "{words}", values: { words } };
}

/**
 * Several sentences said as one ("“Лобио”, “Пхали”"): each one's user
 * placeholders are numbered apart (`{name}` -> `{name_2}`), so the same
 * placeholder of two sentences keeps its own words.
 */
export function joinSentences(sentences: readonly SentenceWithUserValues[], separator: string): SentenceWithUserValues {
  const values: Record<string, string> = {};
  const texts = sentences.map((sentence, index) =>
    sentence.text.replace(/\{(\w+)\}/g, (placeholder, name: string) => {
      const value = Object.hasOwn(sentence.values, name) ? sentence.values[name] : undefined;
      if (value === undefined) {
        return placeholder;
      }
      const numbered = `${name}_${index + 1}`;
      values[numbered] = value;
      return `{${numbered}}`;
    }),
  );
  return { text: texts.join(separator), values };
}

const PLACEHOLDER = /\{(\w+)\}(\.?)/g;

/** "Handled by {name}." with `{ name: "Тамар" }` -> [text "Handled by ", value "Тамар", text "."]. */
export function splitUserValues(template: string, values: Readonly<Record<string, string>>): SentencePart[] {
  const parts: SentencePart[] = [];
  let text = "";
  let last = 0;
  for (const match of template.matchAll(PLACEHOLDER)) {
    const [placeholder, name = "", stop = ""] = match;
    const value = Object.hasOwn(values, name) ? values[name] : undefined;
    if (value === undefined) {
      continue;
    }
    text += template.slice(last, match.index);
    if (text) {
      parts.push({ kind: "text", text });
    }
    parts.push({ kind: "value", name, value });
    text = value.endsWith(".") ? "" : stop;
    last = match.index + placeholder.length;
  }
  text += template.slice(last);
  if (text) {
    parts.push({ kind: "text", text });
  }
  return parts;
}
