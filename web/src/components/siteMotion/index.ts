/**
 * The public site's motion: the same reveals, staggers, tilting cards,
 * magnetic buttons and depth layers as "@/components/motion", moved by CSS
 * (src/styles/siteMotion.css) and a shared IntersectionObserver instead of
 * the motion library, so a public page ships no animation engine
 * (src/app/_landing/publicBundle.test.ts keeps it that way).
 */

export { AnimatedNumber } from "@/components/motion/AnimatedNumber";
export { MagneticButton } from "./MagneticButton";
export { Parallax } from "./Parallax";
export { Reveal } from "./Reveal";
export { Stagger } from "./Stagger";
export { StaggerItem } from "./StaggerItem";
export { TiltCard } from "./TiltCard";
export { TiltLayer } from "./TiltLayer";
