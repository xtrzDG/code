import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderInLocale, textsIn } from "@/test/render";

import { StillIndexingNote } from "./StillIndexingNote";

describe("StillIndexingNote: a list while a data task still fills it", () => {
  it.each(["en", "ru", "ka"] as const)("says the list may be incomplete in %s", (locale) => {
    const { t } = textsIn(locale);
    renderInLocale(<StillIndexingNote isIndexing />, { locale });

    expect(screen.getByRole("status").textContent).toContain(t("dataTasks.indexing.title"));
  });

  it("says nothing once the list is complete or before it loaded", () => {
    const { container } = renderInLocale(<StillIndexingNote isIndexing={false} />);
    const { container: loading } = renderInLocale(<StillIndexingNote isIndexing={undefined} />);

    expect(container.textContent).toBe("");
    expect(loading.textContent).toBe("");
  });
});
