import { SectionLoading } from "@/components/business/SectionLoading";

import { ChannelsSkeleton } from "./_components/ChannelsSkeleton";

export default function ChannelsLoading() {
  return (
    <SectionLoading section="channels" label="common.loading">
      <ChannelsSkeleton />
    </SectionLoading>
  );
}
