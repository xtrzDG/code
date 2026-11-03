/** Types of scripts/bundle-secrets.mjs for its tests (src/test/bundleSecrets.test.ts). */

export interface SecretRule {
  name: string;
  pattern: RegExp;
}

export interface SecretValue {
  name: string;
  value: string;
}

export interface SecretHit {
  file: string;
  rule: string;
  excerpt: string;
}

export const SECRET_RULES: readonly SecretRule[];

export function documentedVariables(envExample: string): string[];

export function isSecretVariable(name: string): boolean;

export function secretValues(names: readonly string[], env: Record<string, string | undefined>): SecretValue[];

export function masked(text: string): string;

export function findSecrets(
  file: string,
  text: string,
  options?: { values?: readonly SecretValue[]; isBrowserFile?: boolean },
): SecretHit[];
