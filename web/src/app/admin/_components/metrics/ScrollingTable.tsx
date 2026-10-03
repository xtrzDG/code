import type { ReactNode } from "react";

/**
 * A table of the Metrics page that scrolls sideways on a phone. The
 * scrolling area takes keyboard focus (arrow keys scroll it), so the
 * columns past the edge are reachable without a pointer; the kit's THead,
 * TBody, Tr, Th and Td go inside.
 */
export function ScrollingTable({ caption, children }: { caption: string; children: ReactNode }) {
  return (
    <div role="group" aria-label={caption} tabIndex={0} className="w-full overflow-x-auto">
      <table className="w-full border-collapse text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}
