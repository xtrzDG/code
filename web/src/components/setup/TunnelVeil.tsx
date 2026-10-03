/**
 * The calm behind a tunnel screen's content: the backdrop's rings and
 * floor lines fade out under it, so they never cross a heading or a card
 * (src/styles/tunnel.css, `.tunnel-veil`). Put it first in a `relative
 * isolate` screen.
 */
export function TunnelVeil() {
  return <div aria-hidden data-tunnel-veil className="tunnel-veil" />;
}
