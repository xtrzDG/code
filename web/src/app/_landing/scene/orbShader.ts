/**
 * The assistant's orb: a sphere that breathes (its surface wobbles a
 * little) with three colours flowing through it, a bright core facing the
 * viewer and a light rim (fresnel), like a lit glass bead.
 */

export const ORB_VERTEX_SHADER = /* glsl */ `
uniform float uTime;
varying vec3 vNormal;
varying vec3 vViewDirection;
varying vec3 vLocal;

float wobble(vec3 p) {
  return sin(p.x * 2.1 + uTime * 0.9) * sin(p.y * 2.4 + uTime * 0.7) * sin(p.z * 1.8 + uTime * 0.8);
}

void main() {
  vec3 displaced = position + normal * wobble(position) * 0.045;
  vec4 viewPosition = modelViewMatrix * vec4(displaced, 1.0);
  vNormal = normalize(normalMatrix * normal);
  vViewDirection = normalize(-viewPosition.xyz);
  vLocal = position;
  gl_Position = projectionMatrix * viewPosition;
}
`;

export const ORB_FRAGMENT_SHADER = /* glsl */ `
uniform float uTime;
uniform float uPulse;
uniform vec3 uColorA;
uniform vec3 uColorB;
uniform vec3 uColorC;
varying vec3 vNormal;
varying vec3 vViewDirection;
varying vec3 vLocal;

void main() {
  vec3 normal = normalize(vNormal);
  float facing = max(dot(normal, normalize(vViewDirection)), 0.0);
  float rim = pow(1.0 - facing, 2.6);
  float t = uTime * 0.28;
  float currentA = sin(vLocal.x * 2.6 + t * 2.0 + sin(vLocal.y * 3.2 - t)) * 0.5 + 0.5;
  float currentB = sin(vLocal.y * 2.9 - t * 1.7 + sin(vLocal.z * 2.3 + t * 1.2)) * 0.5 + 0.5;
  vec3 color = mix(uColorA, uColorB, currentA);
  color = mix(color, uColorC, currentB * 0.6);
  // Lit from the upper left (in view space, so the highlight stays put as the camera moves).
  float light = max(dot(normal, normalize(vec3(-0.45, 0.6, 0.65))), 0.0);
  color *= 0.5 + 0.6 * light;
  color += pow(light, 28.0) * 0.75;
  // A message arriving lights the core for a moment.
  color += pow(facing, 3.0) * uPulse * 0.35;
  color = mix(color, uColorB * 1.25, rim * 0.45);
  gl_FragColor = vec4(color, 1.0);
  #include <colorspace_fragment>
}
`;
