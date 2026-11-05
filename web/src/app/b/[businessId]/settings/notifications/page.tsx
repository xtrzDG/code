import { pageMetadata } from "@/components/business/pageMetadata";

import { NotificationsTab } from "../_components/NotificationsTab";

export const generateMetadata = pageMetadata("settings/notifications");

/** Settings → Notifications: who hears about handoffs, leads and bookings, and where. */
export default function SettingsNotificationsPage() {
  return <NotificationsTab />;
}
