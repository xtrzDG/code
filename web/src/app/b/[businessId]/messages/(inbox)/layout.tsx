import { ConversationsShell } from "./_components/ConversationsShell";

/** The feed stays mounted while conversations open next to it (see ConversationsShell). */
export default function ConversationsLayout({ children }: LayoutProps<"/b/[businessId]/messages">) {
  return <ConversationsShell>{children}</ConversationsShell>;
}
