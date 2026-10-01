import { sectionMetadata } from "@/components/business/SectionPlaceholder";

import { SettingsScreen } from "./SettingsScreen";

export const generateMetadata = sectionMetadata("settings");

export default function SettingsPage() {
  return <SettingsScreen />;
}
