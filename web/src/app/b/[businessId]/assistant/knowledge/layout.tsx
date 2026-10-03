import { KnowledgeFrame } from "./_components/KnowledgeFrame";

/** Every Knowledge sub-page shares the heading and the tabs. */
export default function KnowledgeLayout({ children }: LayoutProps<"/b/[businessId]/assistant/knowledge">) {
  return <KnowledgeFrame>{children}</KnowledgeFrame>;
}
