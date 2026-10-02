import { getI18n } from "@/i18n/server";

import { ConversationDetailSkeleton } from "./_components/ConversationDetailSkeleton";

/** A conversation on its way (the feed beside it stays: it lives in the layout). */
export default async function ConversationLoading() {
  const { t } = await getI18n();
  return <ConversationDetailSkeleton label={t("conversations.loadingOne")} />;
}
