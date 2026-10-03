import { SectionFrame } from "@/components/shell/SectionFrame";

/** Every settings page shares the heading and the tabs (business, team, notifications, plan, privacy, audit). */
export default function SettingsLayout({ children }: LayoutProps<"/b/[businessId]/settings">) {
  return <SectionFrame section="settings">{children}</SectionFrame>;
}
