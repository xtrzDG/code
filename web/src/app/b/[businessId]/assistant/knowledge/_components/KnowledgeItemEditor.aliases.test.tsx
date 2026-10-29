import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { CurrentUserView, KnowledgeItemDetails } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import type { Locale } from "@/i18n/config";
import { languageName } from "@/lib/format";
import type { AliasRow } from "@/lib/knowledge/aliases";
import { ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business as cafe } from "../../../settings/_lib/settingsFixtures";
import { KnowledgeItemEditor } from "./KnowledgeItemEditor";

vi.mock("@/api/client", () => ({
  api: {
    GET: vi.fn(),
    POST: vi.fn(),
    PUT: vi.fn(),
    PATCH: vi.fn(),
    DELETE: vi.fn(),
  },
}));

const me = {
  user: { id: "user_owner", is_platform_admin: false },
} as unknown as CurrentUserView;
const business = { ...cafe, languages: ["en", "ka", "ru", "he"] };
const { t, tp } = textsIn("en");

const STORED: AliasRow[] = [
  { language: "ka", text: "იმერული ხაჭაპური", status: "approved" },
  { language: "ru", text: "Хачапури по-имеретински", status: "suggested" },
  { language: "he", text: "חצ'אפורי אימרולי", status: "approved" },
];

const item = (aliases: AliasRow[] = STORED) => ({
  kind: "menu_item" as const,
  title: "Imeretian khachapuri",
  body: "Cheese bread",
  price_minor: 1500,
  duration_minutes: null,
  languages: ["en"],
  aliases,
  is_active: true,
});

const details = (aliases: AliasRow[]) =>
  ({
    ...item(aliases),
    id: "knowledge_item_1",
  }) as unknown as KnowledgeItemDetails;

function renderEditor({ locale = "en", aliases }: { locale?: Locale; aliases?: AliasRow[] } = {}) {
  const onSaved = vi.fn();
  const onClose = vi.fn();
  renderInLocale(
    <BusinessProvider business={business} me={me}>
      <KnowledgeItemEditor
        target={{ mode: "edit", id: "knowledge_item_1", item: item(aliases) }}
        kinds={["menu_item", "faq"]}
        onClose={onClose}
        onSaved={onSaved}
      />
    </BusinessProvider>,
    { locale },
  );
  return { onSaved, onClose };
}

const group = (language: string) => document.querySelector<HTMLElement>(`[data-alias-language="${language}"]`)!;
const chips = (language: string) =>
  [...group(language).querySelectorAll<HTMLElement>("[data-alias-status]")].map((chip) => [
    chip.querySelector("[data-user-content]")?.textContent,
    chip.dataset.aliasStatus,
  ]);

describe("KnowledgeItemEditor: the item's names in the business's other languages", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.POST).mockReset();
    vi.mocked(api.PATCH).mockReset();
  });

  it("shows the stored names as chips in Georgian, Russian and Hebrew, the suggestion marked", () => {
    renderEditor();

    expect(screen.getByRole("heading", { name: t("knowledge.aliases.title") })).toBeTruthy();
    // The item is written in English: no English group, one per other language.
    expect(document.querySelector('[data-alias-language="en"]')).toBeNull();
    expect(chips("ka")).toEqual([["იმერული ხაჭაპური", "approved"]]);
    expect(chips("ru")).toEqual([["Хачапури по-имеретински", "suggested"]]);
    expect(chips("he")).toEqual([["חצ'אפורי אימרולי", "approved"]]);
    expect(within(group("ru")).getByText(t("knowledge.aliases.suggested"))).toBeTruthy();
    expect(screen.getByText(t("knowledge.aliases.suggestedHint"))).toBeTruthy();
    expect(within(group("ka")).getByText(languageName("ka", "en"))).toBeTruthy();
  });

  it("accepts a suggestion, adds a name with Enter without saving, and saves the names", async () => {
    const user = userEvent.setup();
    vi.mocked(api.PATCH).mockImplementation((() => ok(details(STORED))) as never);
    const { onSaved } = renderEditor();

    await user.click(
      screen.getByRole("button", {
        name: t("knowledge.aliases.accept", {
          text: "Хачапури по-имеретински",
        }),
      }),
    );
    expect(chips("ru")).toEqual([["Хачапури по-имеретински", "approved"]]);

    const russian = screen.getByRole("textbox", {
      name: t("knowledge.aliases.placeholder", {
        language: languageName("ru", "en"),
      }),
    });
    await user.type(russian, "  Хачапури   с сыром {Enter}");
    expect(api.PATCH).not.toHaveBeenCalled();
    expect(chips("ru")).toEqual([
      ["Хачапури по-имеретински", "approved"],
      ["Хачапури с сыром", "approved"],
    ]);

    await user.click(
      screen.getByRole("button", {
        name: t("knowledge.aliases.remove", { text: "חצ'אפורי אימרולי" }),
      }),
    );
    expect(
      within(group("he")).getByText(t("knowledge.aliases.none", { language: languageName("he", "en") })),
    ).toBeTruthy();

    await user.click(screen.getByRole("button", { name: t("common.save") }));
    const [, init] = vi.mocked(api.PATCH).mock.calls[0] as unknown as [string, { body: { aliases: AliasRow[] } }];
    expect(init.body).toEqual({
      aliases: [
        { language: "ka", text: "იმერული ხაჭაპური", status: "approved" },
        { language: "ru", text: "Хачапури по-имеретински", status: "approved" },
        { language: "ru", text: "Хачапури с сыром", status: "approved" },
      ],
    });
    expect(onSaved).toHaveBeenCalled();
  });

  it("refuses an empty name, the same name twice and a fourth name in a language", async () => {
    const user = userEvent.setup();
    renderEditor({
      aliases: [
        { language: "ka", text: "ხაჭაპური", status: "approved" },
        { language: "ka", text: "იმერული", status: "approved" },
        { language: "ka", text: "ყველიანი", status: "suggested" },
      ],
    });
    const georgian = screen.getByRole("textbox", {
      name: t("knowledge.aliases.placeholder", {
        language: languageName("ka", "en"),
      }),
    });

    await user.type(georgian, "   {Enter}");
    expect(within(group("ka")).getByRole("alert").textContent).toBe(t("validation.required"));

    await user.clear(georgian);
    await user.type(georgian, " ხაჭაპური {Enter}");
    expect(within(group("ka")).getByRole("alert").textContent).toBe(t("knowledge.aliases.duplicate"));

    await user.clear(georgian);
    await user.type(georgian, "პური{Enter}");
    expect(within(group("ka")).getByRole("alert").textContent).toBe(t("knowledge.aliases.tooMany"));
    expect(chips("ka")).toHaveLength(3);
  });

  it("joins the model's suggestions to the form; saving unchanged names sends nothing", async () => {
    const user = userEvent.setup();
    const suggested: AliasRow[] = [...STORED.slice(0, 2), { language: "he", text: "חצ'אפורי", status: "suggested" }];
    vi.mocked(api.POST).mockImplementation((() => ok(details(suggested))) as never);
    const { onClose } = renderEditor({ aliases: STORED.slice(0, 2) });

    await user.click(screen.getByRole("button", { name: t("knowledge.aliases.suggest") }));
    const [path, init] = vi.mocked(api.POST).mock.calls[0] as unknown as [
      string,
      { params: { path: Record<string, string> } },
    ];
    expect(path).toBe("/v1/businesses/{business_id}/knowledge/{item_id}/aliases/suggest");
    expect(init.params.path).toEqual({
      business_id: business.id,
      item_id: "knowledge_item_1",
    });
    expect(await screen.findByText(tp("knowledge.aliases.suggestedCount", 1))).toBeTruthy();
    expect(chips("he")).toEqual([["חצ'אפורי", "suggested"]]);

    await user.click(screen.getByRole("button", { name: t("common.save") }));
    expect(api.PATCH).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it("says so when the model has nothing new, and keeps the owner's unsaved names", async () => {
    const user = userEvent.setup();
    vi.mocked(api.POST).mockImplementation((() => ok(details(STORED))) as never);
    renderEditor();

    const hebrew = screen.getByRole("textbox", {
      name: t("knowledge.aliases.placeholder", {
        language: languageName("he", "en"),
      }),
    });
    await user.type(hebrew, "לחם גבינה{Enter}");
    await user.click(screen.getByRole("button", { name: t("knowledge.aliases.suggest") }));

    expect(await screen.findByText(t("knowledge.aliases.nothingSuggested"))).toBeTruthy();
    expect(chips("he")).toEqual([
      ["חצ'אפורי אימרולי", "approved"],
      ["לחם גבינה", "approved"],
    ]);
  });

  it("asks to save a new title before suggesting translations of it", async () => {
    const user = userEvent.setup();
    renderEditor();

    const title = screen.getByRole("textbox", {
      name: t("knowledge.form.title"),
    });
    await user.clear(title);
    await user.type(title, "Adjarian khachapuri");

    expect(screen.getByRole("button", { name: t("knowledge.aliases.suggest") }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByText(t("knowledge.aliases.saveTitleFirst"))).toBeTruthy();
  });

  it("reads in Italian, the language names in Italian too", () => {
    const italian = textsIn("it");
    renderEditor({ locale: "it" });

    expect(
      screen.getByRole("heading", {
        name: italian.t("knowledge.aliases.title"),
      }),
    ).toBeTruthy();
    expect(within(group("ka")).getByText(languageName("ka", "it"))).toBeTruthy();
    expect(
      screen.getByRole("button", {
        name: italian.t("knowledge.aliases.suggest"),
      }),
    ).toBeTruthy();
  });
});
