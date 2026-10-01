import { AssistantFrame } from "./_components/AssistantFrame";

/** Every Assistant sub-page shares the heading, the version history and the tabs. */
export default function AssistantLayout({ children }: LayoutProps<"/b/[businessId]/assistant">) {
  return <AssistantFrame>{children}</AssistantFrame>;
}
