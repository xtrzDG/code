/**
 * Behind a landing hero: three slow colour clouds (aurora) and a floor of
 * lines running towards the viewer, the way into the product. Decorative,
 * pure CSS (src/styles/landing.css); still under reduced motion. Its sizes
 * are fixed (`.hero-backdrop`) and the heroes render it after their content,
 * so it never moves while the page streams in (no layout shift).
 */
export function HeroBackdrop() {
  return (
    <div aria-hidden className="hero-backdrop pointer-events-none absolute inset-0 -z-20 overflow-hidden">
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
