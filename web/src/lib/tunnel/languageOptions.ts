import type { CountryProfileView, LanguageOption } from "@/api/types";
import { capitalizeFirst } from "@/lib/format";

/**
 * The customer languages a business in this country can choose: the
 * country's defaults first, then those offered on request, each once, with
 * names starting with a capital letter.
 */
export function languageOptions(profile: CountryProfileView | undefined): LanguageOption[] {
  if (!profile) {
    return [];
  }
  const seen = new Set<string>();
  return [...profile.default_customer_languages, ...profile.on_request_customer_languages]
    .filter((option) => {
      if (seen.has(option.tag)) {
        return false;
      }
      seen.add(option.tag);
      return true;
    })
    .map((option) => ({
      ...option,
      native_name: capitalizeFirst(option.native_name, option.tag),
      display_name: capitalizeFirst(option.display_name),
    }));
}
