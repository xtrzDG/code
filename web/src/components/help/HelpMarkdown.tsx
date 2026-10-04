"use client";

/**
 * A help article as readable text (lib/help/helpMarkdown.ts): nothing in it
 * becomes HTML. A link to another article opens it in place (`onArticle`,
 * the drawer) or on its help center page; a cabinet link leads into the
 * business the person is in (plain text outside one); an https link opens
 * in a new tab.
 */

import Link from "next/link";
import { Fragment, type ReactNode } from "react";

import { IconExternal, IconSparkles } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { parseHelpMarkdown, type HelpBlock, type HelpSpan } from "@/lib/help/helpMarkdown";
import { cabinetHref, helpArticlePath } from "@/lib/help/helpTopics";

export interface HelpLinkHandlers {
  /** Opens another article in place; without it the help center page opens. */
  onArticle?: (slug: string) => void;
  /** The business a cabinet link leads into. */
  businessId: string | null;
  /** After following a link out of the article (the drawer closes). */
  onLeave?: () => void;
}

const LINK = "font-medium text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent";

function SpanText({ span }: { span: HelpSpan }) {
  const text = span.code ? (
    <code className="rounded bg-surface-muted px-1 py-0.5 font-mono text-[0.85em] text-ink" dir="ltr">
      {span.text}
    </code>
  ) : (
    span.text
  );
  return span.bold ? <strong className="font-semibold text-ink">{text}</strong> : <>{text}</>;
}

function SpanLink({ span, handlers }: { span: HelpSpan; handlers: HelpLinkHandlers }) {
  const { t } = useI18n();
  const link = span.link;
  const content = <SpanText span={span} />;
  if (!link) {
    return content;
  }
  if (link.kind === "external") {
    return (
      <a href={link.href} target="_blank" rel="noopener noreferrer" className={LINK}>
        {content}
        <IconExternal className="ms-0.5 inline size-3.5 align-[-0.125em]" aria-hidden />
        <span className="sr-only"> ({t("helpCenter.opensInNewTab")})</span>
      </a>
    );
  }
  if (link.kind === "cabinet") {
    const href = cabinetHref(link.page, handlers.businessId);
    return href ? (
      <Link href={href} onClick={handlers.onLeave} className={LINK}>
        {content}
      </Link>
    ) : (
      content
    );
  }
  if (handlers.onArticle) {
    const open = handlers.onArticle;
    return (
      <button type="button" onClick={() => open(link.slug)} className={cn(LINK, "cursor-pointer")}>
        {content}
      </button>
    );
  }
  return (
    <Link href={helpArticlePath(link.slug)} onClick={handlers.onLeave} className={LINK}>
      {content}
    </Link>
  );
}

function Spans({ spans, handlers }: { spans: readonly HelpSpan[]; handlers: HelpLinkHandlers }) {
  return (
    <>
      {spans.map((span, index) => (
        <Fragment key={index}>{span.link ? <SpanLink span={span} handlers={handlers} /> : <SpanText span={span} />}</Fragment>
      ))}
    </>
  );
}

function Block({ block, handlers }: { block: HelpBlock; handlers: HelpLinkHandlers }): ReactNode {
  const spans = (value: readonly HelpSpan[]) => <Spans spans={value} handlers={handlers} />;
  switch (block.kind) {
    case "heading":
      return block.level === 2 ? (
        <h3 className="pt-3 text-base font-semibold text-ink" dir="auto">
          {spans(block.spans)}
        </h3>
      ) : (
        <h4 className="pt-1 text-sm font-semibold text-ink" dir="auto">
          {spans(block.spans)}
        </h4>
      );
    case "paragraph":
      return <p dir="auto">{spans(block.spans)}</p>;
    case "list": {
      const items = block.items.map((item, index) => <li key={index}>{spans(item)}</li>);
      return block.ordered ? (
        <ol className="list-decimal space-y-1.5 ps-5 marker:font-medium marker:text-ink-subtle" dir="auto">
          {items}
        </ol>
      ) : (
        <ul className="list-disc space-y-1.5 ps-5 marker:text-ink-subtle" dir="auto">
          {items}
        </ul>
      );
    }
    case "tip":
      return (
        <div className="flex gap-3 rounded-xl border border-accent/25 bg-accent-soft px-4 py-3 text-ink" dir="auto">
          <IconSparkles className="mt-0.5 size-4 shrink-0 text-accent" aria-hidden />
          <p>{spans(block.spans)}</p>
        </div>
      );
    case "table":
      return (
        <div className="-mx-1 overflow-x-auto px-1">
          <table className="w-full border-collapse text-start text-xs">
            <thead>
              <tr>
                {block.header.map((cell, index) => (
                  <th key={index} scope="col" className="border-b border-line-strong px-2 py-2 text-start font-semibold text-ink" dir="auto">
                    {spans(cell)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="align-top">
                  {row.map((cell, index) => (
                    <td key={index} className="border-b border-line px-2 py-2" dir="auto">
                      {spans(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
  }
}

export function HelpMarkdown({
  source,
  lang,
  className,
  ...handlers
}: HelpLinkHandlers & { source: string; lang?: string; className?: string }) {
  return (
    <div lang={lang} className={cn("space-y-3 text-sm leading-relaxed text-ink-muted", className)}>
      {parseHelpMarkdown(source).map((block, index) => (
        <Block key={index} block={block} handlers={handlers} />
      ))}
    </div>
  );
}
