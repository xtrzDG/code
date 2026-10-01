import { sectionMetadata } from "@/components/business/SectionPlaceholder";

import { ChannelsScreen } from "./ChannelsScreen";

export const generateMetadata = sectionMetadata("channels");

export default function ChannelsPage() {
  return <ChannelsScreen />;
}
