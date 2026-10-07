/**
 * A link shown in a narrow place keeps its end: "localh…/c/kofeynya-zerno"
 * rather than "localhost:3401/c/kof…". The text splits before its last path
 * segment; the head gives way first (an ellipsis at its end), the tail (the
 * page's own name, which tells links apart) only when even that does not fit.
 */

export function splitForMiddleEllipsis(text: string): { head: string; tail: string } {
  const cut = text.lastIndexOf("/");
  if (cut <= 0 || cut === text.length - 1) {
    return { head: text, tail: "" };
  }
  return { head: text.slice(0, cut), tail: text.slice(cut) };
}
