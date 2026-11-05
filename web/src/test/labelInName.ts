/**
 * WCAG 2.5.3, Label in Name: a control's name holds the words it shows,
 * in their order, so someone who says what they see (voice control) reaches
 * it. axe's `label-content-name-mismatch` compares words the way `nameWords`
 * cuts them (its `curateTokens`): parentheticals dropped, anything but
 * letters and digits a gap, case ignored.
 */

const PARENTHETICAL = /\([^()]*\)/g;
const NOT_A_LETTER_OR_DIGIT = /[^\p{L}\p{N}]+/gu;

function nameWords(text: string): string[] {
  let words = text.normalize("NFKD");
  let previous: string;
  do {
    previous = words;
    words = words.replace(PARENTHETICAL, "");
  } while (words !== previous);
  return words.replace(NOT_A_LETTER_OR_DIGIT, " ").toLowerCase().split(" ").filter(Boolean);
}

/** Whether `name` holds the words of `shown` one after another. */
export function holdsShownWords(name: string, shown: string): boolean {
  const needle = nameWords(shown);
  const haystack = nameWords(name);
  return haystack.some((_, start) => needle.every((word, offset) => haystack[start + offset] === word));
}
