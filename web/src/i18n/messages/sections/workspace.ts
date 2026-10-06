/**
 * Texts of the cabinet sections: Channels, billing, settings (Calls, Quick replies, Reviews and Integrations among them), resources' calendars and the platform admin.
 *
 * Top-level keys are namespaces (one per section, e.g. `bookings`). They are
 * spread into en.ts, ru.ts, ka.ts, he.ts and de.ts, so they must not clash
 * with the namespaces of the other dictionaries. The other languages are
 * type-checked against `en`.
 *
 * Each namespace (a large one in a few parts) lives in its own file per
 * language under `./workspace/`; this file composes them.
 */

import type { Translation } from "../../translate";
import { adminEn } from "./workspace/admin.en";
import { adminIncidentEn } from "./workspace/adminIncident.en";
import { adminIncidentKa } from "./workspace/adminIncident.ka";
import { adminIncidentRu } from "./workspace/adminIncident.ru";
import { adminKa } from "./workspace/admin.ka";
import { adminActionsEn } from "./workspace/adminActions.en";
import { adminActionsKa } from "./workspace/adminActions.ka";
import { adminActionsRu } from "./workspace/adminActions.ru";
import { adminStoryEn } from "./workspace/adminStory.en";
import { adminStoryKa } from "./workspace/adminStory.ka";
import { adminStoryRu } from "./workspace/adminStory.ru";
import { adminChurnEn } from "./workspace/adminChurn.en";
import { adminChurnKa } from "./workspace/adminChurn.ka";
import { adminChurnRu } from "./workspace/adminChurn.ru";
import { adminMetricsEn } from "./workspace/adminMetrics.en";
import { adminMetricsKa } from "./workspace/adminMetrics.ka";
import { adminMetricsRu } from "./workspace/adminMetrics.ru";
import { adminRu } from "./workspace/admin.ru";
import { adminReplyGuardEn } from "./workspace/adminReplyGuard.en";
import { adminReplyGuardKa } from "./workspace/adminReplyGuard.ka";
import { adminReplyGuardRu } from "./workspace/adminReplyGuard.ru";
import { adminReplySpeedEn } from "./workspace/adminReplySpeed.en";
import { adminReplySpeedKa } from "./workspace/adminReplySpeed.ka";
import { adminReplySpeedRu } from "./workspace/adminReplySpeed.ru";
import { adminSecurityEn } from "./workspace/adminSecurity.en";
import { adminSpendEn } from "./workspace/adminSpend.en";
import { adminSpendKa } from "./workspace/adminSpend.ka";
import { adminSpendRu } from "./workspace/adminSpend.ru";
import { adminSecurityKa } from "./workspace/adminSecurity.ka";
import { adminSecurityRu } from "./workspace/adminSecurity.ru";
import { adminSystemEn } from "./workspace/adminSystem.en";
import { adminSystemKa } from "./workspace/adminSystem.ka";
import { adminSystemRu } from "./workspace/adminSystem.ru";
import { dataTasksEn } from "./workspace/dataTasks.en";
import { dataTasksKa } from "./workspace/dataTasks.ka";
import { dataTasksRu } from "./workspace/dataTasks.ru";
import { adminTeamEn } from "./workspace/adminTeam.en";
import { adminTeamKa } from "./workspace/adminTeam.ka";
import { adminTeamRu } from "./workspace/adminTeam.ru";
import { billingEn } from "./workspace/billing.en";
import { billingKa } from "./workspace/billing.ka";
import { billingRu } from "./workspace/billing.ru";
import { billingLifecycleEn } from "./workspace/billingLifecycle.en";
import { billingLifecycleKa } from "./workspace/billingLifecycle.ka";
import { billingLifecycleRu } from "./workspace/billingLifecycle.ru";
import { calendarSyncEn } from "./workspace/calendarSync.en";
import { calendarSyncKa } from "./workspace/calendarSync.ka";
import { calendarSyncRu } from "./workspace/calendarSync.ru";
import { callSettingsEn } from "./workspace/callSettings.en";
import { callSettingsKa } from "./workspace/callSettings.ka";
import { callSettingsRu } from "./workspace/callSettings.ru";
import { channelSetupEn } from "./workspace/channelSetup.en";
import { channelSetupKa } from "./workspace/channelSetup.ka";
import { channelSetupRu } from "./workspace/channelSetup.ru";
import { channelPagesEn } from "./workspace/channelPages.en";
import { channelPagesKa } from "./workspace/channelPages.ka";
import { channelPagesRu } from "./workspace/channelPages.ru";
import { channelsEn } from "./workspace/channels.en";
import { channelsKa } from "./workspace/channels.ka";
import { channelsRu } from "./workspace/channels.ru";
import { customerMemoryEn } from "./workspace/customerMemory.en";
import { customerMemoryKa } from "./workspace/customerMemory.ka";
import { customerMemoryRu } from "./workspace/customerMemory.ru";
import { dataExportsEn } from "./workspace/dataExports.en";
import { dataExportsKa } from "./workspace/dataExports.ka";
import { dataExportsRu } from "./workspace/dataExports.ru";
import { formFieldsEn } from "./workspace/formFields.en";
import { formFieldsKa } from "./workspace/formFields.ka";
import { formFieldsRu } from "./workspace/formFields.ru";
import { workspaceCommonEn } from "./workspace/common.en";
import { workspaceCommonKa } from "./workspace/common.ka";
import { workspaceCommonRu } from "./workspace/common.ru";
import { loginOptionsEn } from "./workspace/loginOptions.en";
import { loginOptionsKa } from "./workspace/loginOptions.ka";
import { loginOptionsRu } from "./workspace/loginOptions.ru";
import { notificationsEn } from "./workspace/notifications.en";
import { notificationsKa } from "./workspace/notifications.ka";
import { notificationsRu } from "./workspace/notifications.ru";
import { privacyNoticeEn } from "./workspace/privacyNotice.en";
import { privacyRetentionEn } from "./workspace/privacyRetention.en";
import { privacyRetentionKa } from "./workspace/privacyRetention.ka";
import { privacyRetentionRu } from "./workspace/privacyRetention.ru";
import { privacyNoticeKa } from "./workspace/privacyNotice.ka";
import { privacyNoticeRu } from "./workspace/privacyNotice.ru";
import { qualityEn } from "./workspace/quality.en";
import { qualityKa } from "./workspace/quality.ka";
import { qualityRu } from "./workspace/quality.ru";
import { quickRepliesEn } from "./workspace/quickReplies.en";
import { quickRepliesKa } from "./workspace/quickReplies.ka";
import { quickRepliesRu } from "./workspace/quickReplies.ru";
import { reviewSettingsEn } from "./workspace/reviewSettings.en";
import { reviewSettingsKa } from "./workspace/reviewSettings.ka";
import { reviewSettingsRu } from "./workspace/reviewSettings.ru";
import { settingsEn } from "./workspace/settings.en";
import { settingsKa } from "./workspace/settings.ka";
import { settingsRu } from "./workspace/settings.ru";
import { settingsRecordsEn } from "./workspace/settingsRecords.en";
import { settingsRecordsKa } from "./workspace/settingsRecords.ka";
import { settingsRecordsRu } from "./workspace/settingsRecords.ru";
import { shareEn } from "./workspace/share.en";
import { shareKa } from "./workspace/share.ka";
import { shareRu } from "./workspace/share.ru";
import { widgetSitesEn } from "./workspace/widgetSites.en";
import { widgetSitesKa } from "./workspace/widgetSites.ka";
import { widgetSitesRu } from "./workspace/widgetSites.ru";

export const workspaceEn = {
  workspace: workspaceCommonEn,
  channels: channelsEn,
  channelPages: channelPagesEn,
  channelSetup: channelSetupEn,
  loginOptions: loginOptionsEn,
  billing: billingEn,
  billingLifecycle: billingLifecycleEn,
  settings: { ...settingsEn, ...settingsRecordsEn },
  notifications: notificationsEn,
  callSettings: callSettingsEn,
  reviewSettings: reviewSettingsEn,
  calendarSync: calendarSyncEn,
  quickReplies: quickRepliesEn,
  admin: adminEn,
  adminSecurity: adminSecurityEn,
  adminActions: adminActionsEn,
  adminMetrics: adminMetricsEn,
  adminChurn: adminChurnEn,
  adminStory: adminStoryEn,
  adminReplySpeed: adminReplySpeedEn,
  adminReplyGuard: adminReplyGuardEn,
  adminSystem: adminSystemEn,
  adminTeam: adminTeamEn,
  adminIncident: adminIncidentEn,
  share: shareEn,
  privacyNotice: privacyNoticeEn,
  dataExports: dataExportsEn,
  quality: qualityEn,
  customerMemory: customerMemoryEn,
  privacyRetention: privacyRetentionEn,
  widgetSites: widgetSitesEn,
  adminSpend: adminSpendEn,
  dataTasks: dataTasksEn,
  formFields: formFieldsEn,
} as const;

export const workspaceRu: Translation<typeof workspaceEn> = {
  workspace: workspaceCommonRu,
  channels: channelsRu,
  channelPages: channelPagesRu,
  channelSetup: channelSetupRu,
  loginOptions: loginOptionsRu,
  billing: billingRu,
  billingLifecycle: billingLifecycleRu,
  settings: { ...settingsRu, ...settingsRecordsRu },
  notifications: notificationsRu,
  callSettings: callSettingsRu,
  reviewSettings: reviewSettingsRu,
  calendarSync: calendarSyncRu,
  quickReplies: quickRepliesRu,
  admin: adminRu,
  adminSecurity: adminSecurityRu,
  adminActions: adminActionsRu,
  adminMetrics: adminMetricsRu,
  adminChurn: adminChurnRu,
  adminStory: adminStoryRu,
  adminReplySpeed: adminReplySpeedRu,
  adminReplyGuard: adminReplyGuardRu,
  adminSystem: adminSystemRu,
  adminTeam: adminTeamRu,
  adminIncident: adminIncidentRu,
  share: shareRu,
  privacyNotice: privacyNoticeRu,
  dataExports: dataExportsRu,
  quality: qualityRu,
  customerMemory: customerMemoryRu,
  privacyRetention: privacyRetentionRu,
  widgetSites: widgetSitesRu,
  adminSpend: adminSpendRu,
  dataTasks: dataTasksRu,
  formFields: formFieldsRu,
};

export const workspaceKa: Translation<typeof workspaceEn> = {
  workspace: workspaceCommonKa,
  channels: channelsKa,
  channelPages: channelPagesKa,
  channelSetup: channelSetupKa,
  loginOptions: loginOptionsKa,
  billing: billingKa,
  billingLifecycle: billingLifecycleKa,
  settings: { ...settingsKa, ...settingsRecordsKa },
  notifications: notificationsKa,
  callSettings: callSettingsKa,
  reviewSettings: reviewSettingsKa,
  calendarSync: calendarSyncKa,
  quickReplies: quickRepliesKa,
  admin: adminKa,
  adminSecurity: adminSecurityKa,
  adminActions: adminActionsKa,
  adminMetrics: adminMetricsKa,
  adminChurn: adminChurnKa,
  adminStory: adminStoryKa,
  adminReplySpeed: adminReplySpeedKa,
  adminReplyGuard: adminReplyGuardKa,
  adminSystem: adminSystemKa,
  adminTeam: adminTeamKa,
  adminIncident: adminIncidentKa,
  share: shareKa,
  privacyNotice: privacyNoticeKa,
  dataExports: dataExportsKa,
  quality: qualityKa,
  customerMemory: customerMemoryKa,
  privacyRetention: privacyRetentionKa,
  widgetSites: widgetSitesKa,
  adminSpend: adminSpendKa,
  dataTasks: dataTasksKa,
  formFields: formFieldsKa,
};

export { workspaceHe } from "./workspace/section.he";
export { workspaceDe } from "./workspace/section.de";
