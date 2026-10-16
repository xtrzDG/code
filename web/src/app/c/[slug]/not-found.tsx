import { headers } from "next/headers";

import { hostedChatTexts } from "@/lib/hostedChat/texts";

import { HostedChatNotice, HostedChatShell } from "./_components/HostedChatShell";
import { visitorLanguage } from "./_lib/hostedChatRequest";

/** No business has this chat address: said in the visitor's language, without the cabinet. */
export default async function HostedChatNotFound() {
  const page = visitorLanguage((await headers()).get("accept-language"));
  return (
    <HostedChatShell page={page}>
      <HostedChatNotice lead={hostedChatTexts(page.language).notFound} />
    </HostedChatShell>
  );
}
