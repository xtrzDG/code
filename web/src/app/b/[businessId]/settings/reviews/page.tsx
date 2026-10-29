import { pageMetadata } from "@/components/business/pageMetadata";

import { ReviewsTab } from "../_components/ReviewsTab";

export const generateMetadata = pageMetadata("settings/reviews");

/** Settings → Reviews: feedback after visits, the Google review link and the numbers. */
export default function SettingsReviewsPage() {
  return <ReviewsTab />;
}
