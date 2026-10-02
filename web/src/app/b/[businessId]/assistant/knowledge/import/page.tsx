import { subPageMetadata } from "@/components/content/metadata";

import { MenuImportScreen } from "./MenuImportScreen";

export const generateMetadata = subPageMetadata("knowledge", "knowledge.tabs.import");

/** Read a menu or price list from a photo, PDF, text file or link. */
export default function MenuImportPage() {
  return <MenuImportScreen />;
}
