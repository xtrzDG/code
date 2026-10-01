/** Number helpers of the insights sections (counts, shares, model costs, paging). */

/** Model cost in millionths of a US dollar as money: 7200 -> "$0.0072". */
export function formatMicroUsd(microUsd: number, locale: string): string {
  const dollars = microUsd / 1_000_000;
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: dollars !== 0 && Math.abs(dollars) < 1 ? 4 : 2,
  }).format(dollars);
}

/** Share of a part in whole percent (0 for an empty total), for bar lengths. */
export function sharePercent(part: number, total: number): number {
  if (total <= 0 || part <= 0) {
    return 0;
  }
  return Math.min(100, Math.round((part / total) * 100));
}

/** A percentage for display: 37.5 -> "38%" (locale-aware). */
export function formatPercent(percent: number, locale: string): string {
  return new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 0 }).format(percent / 100);
}

/** The first `pages × pageSize` items: client-side "show more" over a loaded list. */
export function takePage<T>(items: readonly T[], pages: number, pageSize: number): { visible: T[]; hasMore: boolean } {
  const count = Math.max(1, pages) * pageSize;
  return { visible: items.slice(0, count), hasMore: items.length > count };
}
