/**
 * Behind the hero: three slow colour clouds (aurora) and a floor of lines
 * running towards the viewer, the way into the product. Decorative, pure
 * CSS (src/styles/landing.css); still under reduced motion.
 */
export function HeroBackdrop() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="landing-aurora">
        <span />
        <span />
        <span />
      </div>
      <div className="landing-floor">
        <div className="landing-floor-plane">
          <span />
        </div>
      </div>
    </div>
  );
}
