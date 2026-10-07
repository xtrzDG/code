import { InboxShell } from "./_components/list/InboxShell";

/** The list stays mounted while conversations open next to it (see InboxShell). */
export default function InboxLayout({ children }: LayoutProps<"/b/[businessId]/inbox">) {
  return <InboxShell>{children}</InboxShell>;
}
