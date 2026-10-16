import { pageMetadata } from "@/components/business/pageMetadata";

import { GeneralTab } from "./_components/GeneralTab";
import { LegacyTabRedirect } from "./_components/LegacyTabRedirect";

export const generateMetadata = pageMetadata("settings");

/** Settings → Business: details, languages and time, recordings, the assistant's state. */
export default function SettingsPage() {
  return (
    <>
      <LegacyTabRedirect />
      <GeneralTab />
    </>
  );
}
