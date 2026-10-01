"use client";

import { Fragment } from "react";

import { cn } from "@/lib/cn";

import { parseMarkdown, type InlineSpan, type MarkdownBlock } from "./markdown";

function Spans({ spans }: { spans: readonly InlineSpan[] }) {
  return (
    <>
      {spans.map((span, index) =>
        span.bold ? (
          <strong key={index} className="font-semibold text-ink">
            {span.text}
          </strong>
        ) : (
          <Fragment key={index}>{span.text}</Fragment>
        ),
      )}
    </>
  );
}

function Block({ block }: { block: MarkdownBlock }) {
  switch (block.kind) {
    case "heading":
      return block.level === 1 ? (
        <h2 className="text-xl font-semibold text-ink" dir="auto">
          <Spans spans={block.spans} />
        </h2>
      ) : block.level === 2 ? (
        <h3 className="pt-2 text-base font-semibold text-ink" dir="auto">
          <Spans spans={block.spans} />
        </h3>
      ) : (
        <h4 className="text-sm font-semibold text-ink" dir="auto">
          <Spans spans={block.spans} />
        </h4>
      );
    case "paragraph":
      return (
        <p dir="auto">
          <Spans spans={block.spans} />
        </p>
      );
    case "list":
      return (
        <ul className="list-disc space-y-1 ps-5" dir="auto">
          {block.items.map((item, index) => (
            <li key={index}>
              <Spans spans={item} />
            </li>
          ))}
        </ul>
      );
    case "quote":
      return (
        <div className="space-y-2 rounded-xl border border-warning/40 bg-warning-soft px-4 py-3 text-ink" dir="auto">
          {block.paragraphs.map((paragraph, index) => (
            <p key={index}>
              <Spans spans={paragraph} />
            </p>
          ))}
        </div>
      );
    case "table":
      return (
        <div className="-mx-1 overflow-x-auto px-1">
          <table className="w-full min-w-[36rem] border-collapse text-left text-xs">
            <thead>
              <tr>
                {block.header.map((cell, index) => (
                  <th key={index} scope="col" className="border-b border-line-strong px-2 py-2 font-semibold text-ink" dir="auto">
                    <Spans spans={cell} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="align-top">
                  {row.map((cell, index) => (
                    <td key={index} className="border-b border-line px-2 py-2" dir="auto">
                      <Spans spans={cell} />
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

/**
 * A document we ship (Markdown) as readable text; nothing in it becomes HTML.
 * `hideTitle` leaves out the first top-level heading (shown by a dialog title).
 */
export function MarkdownDocument({
  source,
  className,
  lang,
  hideTitle = false,
}: {
  source: string;
  className?: string;
  lang?: string;
  hideTitle?: boolean;
}) {
  const parsed = parseMarkdown(source);
  const titleIndex = hideTitle ? parsed.findIndex((block) => block.kind === "heading" && block.level === 1) : -1;
  const blocks = titleIndex >= 0 ? parsed.filter((_, index) => index !== titleIndex) : parsed;
  return (
    <article lang={lang} className={cn("space-y-3 text-sm leading-relaxed text-ink-muted", className)}>
      {blocks.map((block, index) => (
        <Block key={index} block={block} />
      ))}
    </article>
  );
}
