import type { ReactNode } from "react";

/** The tone of a folded row's summary that wants a look (systemFolds.tsx, clientFolds.tsx); null reads as usual. */
export type FoldTone = "danger" | "warning" | null;

/** A folded row's summary, in the danger or warning colour when it wants a look. */
export function foldNote(text: string, tone: FoldTone): ReactNode {
  return tone ? <span className={tone === "danger" ? "text-danger" : "text-warning"}>{text}</span> : text;
}
