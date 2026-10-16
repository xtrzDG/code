import { SectionFrame } from "@/components/shell/SectionFrame";

/** Overview: the dashboard and (owners) the reports, under one heading with tabs. */
export default function OverviewLayout({ children }: LayoutProps<"/b/[businessId]/overview">) {
  return <SectionFrame section="overview">{children}</SectionFrame>;
}
