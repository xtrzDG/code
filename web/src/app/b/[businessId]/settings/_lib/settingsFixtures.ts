/** Test data shared by the Settings page's unit tests. */

import type { BusinessMember } from "./team";
import type { BusinessView } from "./general";

export const member = (overrides: Partial<BusinessMember>): BusinessMember => ({
  user_id: "user_1",
  role: "staff",
  display_name: null,
  phone_number: null,
  email: null,
  is_verified: true,
  ...overrides,
});

export const business: BusinessView = {
  id: "business_1",
  name: "Café Tbilisi",
  niche_key: "restaurant",
  country_code: "GE",
  city: "Tbilisi",
  timezone: "Asia/Tbilisi",
  currency_code: "GEL",
  languages: ["ka", "en"],
  default_language: "ka",
  owner_language: "ka",
  plan_key: "voice_and_chat",
  status: "live",
  service_mode: "full",
  data_region: "eu",
  recording_retention_days: 90,
  members: [member({ user_id: "user_owner", role: "owner", display_name: "Dato" })],
  manager_contacts: [],
  published_assistant_version_id: null,
  viewer_role: "owner",
  revision: 4,
  created_at: 1,
};
