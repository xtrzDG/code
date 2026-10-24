import { pageMetadata } from "@/components/business/pageMetadata";

import { MenuImportScreen } from "./MenuImportScreen";

export const generateMetadata = pageMetadata("assistant/knowledge", "knowledge.tabs.import");

/** Read a menu or price list from a photo, PDF, text file or link. */
export default function MenuImportPage() {
  return <MenuImportScreen />;
}
