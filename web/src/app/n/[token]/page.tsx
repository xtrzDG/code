import type { Metadata } from "next";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { IconAlert, IconClock } from "@/components/icons";
import { ButtonLink, EmptyState } from "@/components/ui";
import { getI18n } from "@/i18n/server";
import { businessIdOfLinkToken, linkTargetPath } from "@/lib/notificationLinks";
import { HOME_PATH, businessPath } from "@/lib/navigation";
import { getServerApi, serverFetch } from "@/server/api";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("notifications.link.invalidTitle"), robots: { index: false } };
}

/**
 * A notification link (`{cabinet}/n/{token}` in an e-mail, an SMS, a chat
 * message or a device notification). Signing in comes first (the proxy
 * sends visitors to /login and back here); then the API says where the
 * link leads, after checking its signature, its expiry and that this user
 * works in its business, and the page opens there. An expired, altered or
 * foreign link says so instead.
 */
export default async function NotificationLinkPage({ params }: PageProps<"/n/[token]">) {
  const { token } = await params;
  const { t } = await getI18n();
  const businessId = businessIdOfLinkToken(token);
  if (businessId !== null) {
    const api = await getServerApi();
    const result = await api.GET("/v1/businesses/{business_id}/notification-links/{token}", {
      params: { path: { business_id: businessId, token } },
    });
    // Not found (altered, foreign, not this user's business): explained below.
    // Signed out meanwhile: serverFetch signs in again and comes back here.
    const isUnknown = result.response.status === 404 || result.response.status === 422;
    const view = isUnknown ? null : await serverFetch(Promise.resolve(result));
    if (view && !view.is_expired) {
      redirect(linkTargetPath(view));
    }
    if (view) {
      return (
        <LinkProblem
          icon={<IconClock className="size-6" />}
          title={t("notifications.link.expiredTitle")}
          description={t("notifications.link.expiredDescription")}
          action={<ButtonLink href={businessPath(view.business_id)}>{t("notifications.link.openBusiness")}</ButtonLink>}
        />
      );
    }
  }
  return (
    <LinkProblem
      icon={<IconAlert className="size-6" />}
      title={t("notifications.link.invalidTitle")}
      description={t("notifications.link.invalidDescription")}
      action={<ButtonLink href={HOME_PATH}>{t("notifications.link.toBusinesses")}</ButtonLink>}
    />
  );
}

function LinkProblem({
  icon,
  title,
  description,
  action,
}: {
  icon: ReactNode;
  title: string;
  description: string;
  action: ReactNode;
}) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-lg items-center px-4">
      <EmptyState className="w-full rounded-2xl border border-line bg-surface" icon={icon} title={title} description={description} action={action} />
    </main>
  );
}
