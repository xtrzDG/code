import { SectionFrame } from "@/components/shell/SectionFrame";

/** Messages: all conversations, the ones that need a person and requests, as tabs. */
export default function MessagesLayout({ children }: LayoutProps<"/b/[businessId]/messages">) {
  return <SectionFrame section="messages">{children}</SectionFrame>;
}
