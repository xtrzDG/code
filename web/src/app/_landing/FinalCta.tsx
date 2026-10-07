import { IconArrowRight } from "@/components/icons";
import { MagneticButton, Reveal } from "@/components/siteMotion";
import { ButtonLink } from "@/components/ui";
import type { Translator } from "@/i18n/translate";
import { CREATE_PATH } from "@/lib/navigation";

/** The closing call to action: a card with a light running round its edge, coming out of the depth. */
export function FinalCta({ t }: { t: Translator["t"] }) {
  return (
    <section aria-labelledby="cta-title" className="overflow-x-clip border-t border-line py-16 sm:py-24">
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6">
        <Reveal depth={1}>
          <div className="landing-beam relative overflow-hidden rounded-2xl border border-line bg-surface px-6 py-12 text-center sm:px-12 sm:py-16">
            <div
              className="pointer-events-none absolute inset-x-0 -bottom-24 h-64 bg-[radial-gradient(50%_50%_at_50%_50%,color-mix(in_oklab,var(--accent-solid)_22%,transparent),transparent)]"
              aria-hidden
            />
            <div className="relative mx-auto max-w-xl space-y-5">
              <h2 id="cta-title" className="text-2xl font-semibold tracking-tight text-balance text-ink sm:text-3xl">
                {t("landing.cta.title")}
              </h2>
              <p className="text-pretty text-ink-muted">{t("landing.cta.text")}</p>
              <MagneticButton>
                <ButtonLink href={CREATE_PATH} size="lg" trailingIcon={<IconArrowRight className="size-4 rtl:-scale-x-100" aria-hidden />}>
                  {t("landing.cta.button")}
                </ButtonLink>
              </MagneticButton>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
