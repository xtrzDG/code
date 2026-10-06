/**
 * Words that belong to the business, its team or its customers (a name, a
 * message, a knowledge item, a note), shown as they were written, in
 * whatever language. `data-user-content` says they are not the interface's
 * own text: the e2e suite's check for untranslated interface text
 * (e2e/support/consoleClean.ts) leaves them out. Mark exactly the user's
 * words, never a translated label around them: an element that already
 * wraps nothing else takes the attribute itself (`<p data-user-content>`).
 */

import type { ReactNode } from "react";

import { splitUserValues } from "@/i18n/userValues";

/** A span of user content; `dir="auto"` by default, since it may be in any script. */
export function UserContent({
  children,
  className,
  dir = "auto",
}: {
  children: ReactNode;
  className?: string;
  dir?: "auto" | "ltr" | "rtl";
}) {
  return (
    <span data-user-content dir={dir} className={className}>
      {children}
    </span>
  );
}

/**
 * A translated sentence that names user content: `text` is the translation
 * with the user placeholders left in it (`t("inbox.assign.handledBy")`, no value
 * for `{name}`), and each of `values` is shown in its own `UserContent`, so
 * the sentence itself is still checked: `<UserSentence text={t(key)} values={{ name }} />`.
 */
export function UserSentence({ text, values }: { text: string; values: Readonly<Record<string, string>> }) {
  return (
    <>
      {splitUserValues(text, values).map((part, index) =>
        part.kind === "text" ? part.text : <UserContent key={`${part.name}-${index}`}>{part.value}</UserContent>,
      )}
    </>
  );
}
