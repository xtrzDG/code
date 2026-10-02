import type { ComponentPropsWithRef, ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * A data table that scrolls sideways on narrow screens.
 *
 *     <Table caption="Bookings">
 *       <THead><Tr><Th>Name</Th><Th align="right">Guests</Th></Tr></THead>
 *       <TBody>{rows.map((row) => <Tr key={row.id}><Td>…</Td></Tr>)}</TBody>
 *     </Table>
 */
export function Table({
  caption,
  captionHidden = true,
  className,
  children,
  ...props
}: ComponentPropsWithRef<"table"> & { caption?: ReactNode; captionHidden?: boolean }) {
  return (
    <div className="w-full overflow-x-auto">
      <table className={cn("w-full border-collapse text-left text-sm", className)} {...props}>
        {caption ? (
          <caption className={cn(captionHidden ? "sr-only" : "px-4 py-3 text-left text-sm text-ink-muted")}>
            {caption}
          </caption>
        ) : null}
        {children}
      </table>
    </div>
  );
}

export function THead({ className, ...props }: ComponentPropsWithRef<"thead">) {
  return <thead className={cn("border-b border-line text-xs text-ink-muted", className)} {...props} />;
}

export function TBody({ className, ...props }: ComponentPropsWithRef<"tbody">) {
  return <tbody className={cn("divide-y divide-line", className)} {...props} />;
}

export function Tr({ className, ...props }: ComponentPropsWithRef<"tr">) {
  return <tr className={cn("transition-colors hover:bg-surface-muted/50", className)} {...props} />;
}

type Align = "left" | "right" | "center";
const ALIGN: Record<Align, string> = { left: "text-left", right: "text-right", center: "text-center" };

export function Th({
  align = "left",
  className,
  scope = "col",
  ...props
}: ComponentPropsWithRef<"th"> & { align?: Align }) {
  return <th scope={scope} className={cn("px-4 py-2.5 font-medium whitespace-nowrap", ALIGN[align], className)} {...props} />;
}

export function Td({ align = "left", className, ...props }: ComponentPropsWithRef<"td"> & { align?: Align }) {
  return <td className={cn("px-4 py-3 align-top text-ink", ALIGN[align], className)} {...props} />;
}
