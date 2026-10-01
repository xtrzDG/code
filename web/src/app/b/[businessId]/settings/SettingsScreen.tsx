"use client";

import { IconSettings, IconShield } from "@/components/icons";
import { PageHeader } from "@/components/ui";
import { IconBell, IconList, IconUsers } from "@/components/workspace/icons";
import { TabPanel, Tabs, useHashTab, type TabItem } from "@/components/workspace/Tabs";
import { useI18n } from "@/i18n/client";

import { AuditTab } from "./_components/AuditTab";
import { GeneralTab } from "./_components/GeneralTab";
import { NotificationsTab } from "./_components/NotificationsTab";
import { PrivacyTab } from "./_components/PrivacyTab";
import { TeamTab } from "./_components/TeamTab";

const TABS = ["general", "team", "notifications", "privacy", "audit"] as const;
type SettingsTab = (typeof TABS)[number];

/** /settings: business settings, team, notification contacts, privacy and the audit log (tabs in the URL hash). */
export function SettingsScreen() {
  const { t } = useI18n();
  const [tab, setTab] = useHashTab(TABS, "general");

  const items: TabItem<SettingsTab>[] = [
    { id: "general", label: t("settings.tabs.general"), icon: IconSettings },
    { id: "team", label: t("settings.tabs.team"), icon: IconUsers },
    { id: "notifications", label: t("settings.tabs.notifications"), icon: IconBell },
    { id: "privacy", label: t("settings.tabs.privacy"), icon: IconShield },
    { id: "audit", label: t("settings.tabs.audit"), icon: IconList },
  ];

  return (
    <>
      <PageHeader title={t("nav.settings")} description={t("pages.settings.description")} />
      <Tabs group="settings" items={items} value={tab} onChange={setTab} label={t("settings.tabsLabel")} className="mb-6" />
      <TabPanel group="settings" id={tab}>
        {tab === "general" ? <GeneralTab /> : null}
        {tab === "team" ? <TeamTab /> : null}
        {tab === "notifications" ? <NotificationsTab /> : null}
        {tab === "privacy" ? <PrivacyTab /> : null}
        {tab === "audit" ? <AuditTab /> : null}
      </TabPanel>
    </>
  );
}
