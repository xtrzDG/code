"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useMutation } from "@/api/useMutation";
import type { Schema } from "@/api/types";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconBell, IconExternal } from "@/components/icons";
import { Button, Card, Field, Input, Select, UserSentence, buttonClasses } from "@/components/ui";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import { formatLinkCode, notificationLanguages, startCommand } from "../_lib/channels";

const MAX_NAME_LENGTH = 100;

type TelegramLink = Schema<"TelegramLinkView">;

/**
 * A one-time link that subscribes a manager to notifications from the
 * platform's Telegram bot (handoffs, bookings, leads).
 */
export function StaffTelegramCard({ canManage }: { canManage: boolean }) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const router = useRouter();
  const [name, setName] = useState("");
  const [language, setLanguage] = useState(business.owner_language);
  const [nameError, setNameError] = useState(false);
  const [created, setCreated] = useState<{ name: string; link: TelegramLink } | null>(null);

  const create = useMutation((body: { name: string; language: string }) =>
    api.POST("/v1/businesses/{business_id}/manager-contacts/telegram-link", {
      params: { path: { business_id: business.id } },
      body,
    }),
  );

  const linked = (business.manager_contacts ?? []).filter((contact) => contact.channel === "telegram");

  // The bot adds the manager on the server when they open the link (often on
  // another device): reload the business when the owner comes back here.
  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState === "visible") {
        router.refresh();
      }
    };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [router]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = name.trim();
    if (trimmed === "") {
      setNameError(true);
      return;
    }
    const result = await create.run({ name: trimmed, language });
    if (result.ok) {
      setCreated({ name: trimmed, link: result.data });
    }
  };

  const startOver = () => {
    setCreated(null);
    setName("");
  };

  return (
    <Card>
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent" aria-hidden>
            <IconBell className="size-5" />
          </span>
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-ink">{t("channels.telegramLink.title")}</h3>
            <p className="mt-1 text-sm text-ink-muted">{t("channels.telegramLink.description")}</p>
          </div>
        </div>

        {created ? (
          <TelegramLinkResult name={created.name} link={created.link} onAnother={startOver} />
        ) : canManage ? (
          <form onSubmit={onSubmit} noValidate className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
              <Field label={t("channels.telegramLink.name")} required error={nameError ? t("channels.telegramLink.nameRequired") : undefined}>
                {(control) => (
                  <Input
                    {...control}
                    value={name}
                    maxLength={MAX_NAME_LENGTH}
                    dir="auto"
                    autoComplete="off"
                    placeholder={t("channels.telegramLink.namePlaceholder")}
                    onChange={(event) => {
                      setName(event.target.value);
                      setNameError(false);
                    }}
                  />
                )}
              </Field>
              <Field label={t("channels.telegramLink.language")}>
                {(control) => (
                  <Select {...control} value={language} onChange={(event) => setLanguage(event.target.value)}>
                    {notificationLanguages(business.owner_language, business.languages).map((tag) => (
                      <option key={tag} value={tag}>
                        {languageName(tag, locale)}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            </div>
            <Button type="submit" isLoading={create.isPending} loadingText={t("channels.telegramLink.creating")}>
              {t("channels.telegramLink.create")}
            </Button>
          </form>
        ) : null}

        <div className="border-t border-line pt-4 text-sm">
          {linked.length > 0 ? (
            <>
              <p className="text-ink-subtle">{t("channels.telegramLink.linked")}</p>
              <ul className="mt-2 flex flex-wrap gap-2">
                {linked.map((contact) => (
                  <li
                    key={`${contact.address}-${contact.name}`}
                    dir="auto"
                    data-user-content
                    className="rounded-full bg-surface-muted px-3 py-1 text-xs font-medium text-ink"
                  >
                    {contact.name}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-ink-muted">{t("channels.telegramLink.noneLinked")}</p>
          )}
          <Link
            href={businessPath(business.id, "settings/notifications")}
            className="mt-3 inline-block font-medium text-accent hover:underline"
          >
            {t("channels.telegramLink.manage")}
          </Link>
        </div>
      </div>
    </Card>
  );
}

function TelegramLinkResult({ name, link, onAnother }: { name: string; link: TelegramLink; onAnother: () => void }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const message = startCommand(link.code);
  const bot = link.bot_username ? `@${link.bot_username}` : null;

  return (
    <div className="space-y-4 rounded-xl border border-accent/30 bg-accent-soft/40 p-4" role="status">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-semibold text-ink">
          <UserSentence text={t("channels.telegramLink.resultTitle")} values={{ name }} />
        </p>
        <p className="text-xs text-ink-muted">{t("channels.telegramLink.expires", { time: format.dateTime(link.expires_at) })}</p>
      </div>

      <div className="flex flex-col items-center gap-1 rounded-xl bg-surface px-4 py-5 text-center shadow-sm">
        <span className="text-xs tracking-wide text-ink-subtle uppercase">{t("channels.telegramLink.code")}</span>
        <span className="font-mono text-2xl font-semibold tracking-[0.2em] text-ink sm:text-3xl" dir="ltr" aria-label={link.code.split("").join(" ")}>
          {formatLinkCode(link.code)}
        </span>
      </div>

      {link.deep_link ? (
        <>
          <p className="text-sm text-ink-muted">
            <UserSentence text={t("channels.telegramLink.instruction")} values={{ name }} />
          </p>
          <p className="truncate rounded-lg bg-surface px-3 py-2 font-mono text-xs text-ink" dir="ltr">
            {link.deep_link}
          </p>
          <div className="flex flex-wrap gap-2">
            <a
              href={link.deep_link}
              target="_blank"
              rel="noopener noreferrer"
              className={buttonClasses({ size: "sm" })}
            >
              <IconExternal className="size-4" aria-hidden />
              <span>{t("channels.telegramLink.openLink")}</span>
            </a>
            <CopyButton value={link.deep_link} label={t("channels.telegramLink.copyLink")} />
          </div>
        </>
      ) : (
        <>
          <p className="text-sm text-ink-muted">
            {bot ? (
              <UserSentence text={t("channels.telegramLink.instructionNoLink", { bot })} values={{ name }} />
            ) : (
              <UserSentence text={t("channels.telegramLink.instructionNoBot")} values={{ name }} />
            )}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <code className="rounded-lg bg-surface px-3 py-2 font-mono text-sm text-ink" dir="ltr">
              {message}
            </code>
            <CopyButton value={message} label={t("channels.telegramLink.copyMessage")} />
          </div>
        </>
      )}

      <Button variant="ghost" size="sm" onClick={onAnother}>
        {t("channels.telegramLink.another")}
      </Button>
    </div>
  );
}
