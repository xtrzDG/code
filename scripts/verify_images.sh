#!/usr/bin/env bash
# Were a commit's images built, attested and signed by this repository's CI
# on main?
#
#   GITHUB_REPOSITORY=owner/repo scripts/verify_images.sh <commit-sha>
#
# For the backend and the cabinet image (ghcr.io/<owner>/assistant-workshop-
# backend and -web, tagged with the full commit SHA by ci.yml's job
# "publish-images"):
#   - the tag is resolved to its digest, and everything below is checked
#     against that digest, never the tag;
#   - cosign: a keyless signature whose certificate GitHub's OIDC issuer
#     gave to .github/workflows/ci.yml of this repository on refs/heads/main,
#     run for exactly this commit;
#   - gh attestation: SLSA build provenance signed by the same workflow, on
#     refs/heads/main, from exactly this commit, on a GitHub-hosted runner.
# Deploy smoke runs it for every deployed commit (deploy-smoke.yml) and CI
# right after publishing. Needs bash, docker (buildx), cosign and gh with
# GH_TOKEN (packages: read, attestations: read); a private package needs a
# `docker login ghcr.io` first. IMAGE_REGISTRY overrides the registry path.
# Exit codes: 0 verified, 1 not verified, 2 wrong usage.
set -euo pipefail

if [ "$#" -ne 1 ] || ! printf '%s' "$1" | grep -Eq '^[0-9a-f]{40}$'; then
  awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0" >&2
  exit 2
fi
if [ -z "${GITHUB_REPOSITORY:-}" ] || ! printf '%s' "$GITHUB_REPOSITORY" | grep -Eq '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'; then
  echo "Set GITHUB_REPOSITORY to owner/repo." >&2
  exit 2
fi

sha="$1"
repository="$GITHUB_REPOSITORY"
owner="${repository%%/*}"
registry="${IMAGE_REGISTRY:-ghcr.io/${owner,,}}"
workflow=".github/workflows/ci.yml"
branch="refs/heads/main"
issuer="https://token.actions.githubusercontent.com"
identity="https://github.com/$repository/$workflow@$branch"
failures=0

for image in backend web; do
  name="$registry/assistant-workshop-$image"
  digest="$(docker buildx imagetools inspect "$name:$sha" --format '{{.Manifest.Digest}}' 2>/dev/null || true)"
  if ! printf '%s' "$digest" | grep -Eq '^sha256:[0-9a-f]{64}$'; then
    echo "FAIL  $name:$sha is not in the registry: CI on main did not publish this commit."
    failures=$((failures + 1))
    continue
  fi
  reference="$name@$digest"

  if cosign verify "$reference" \
    --certificate-oidc-issuer "$issuer" \
    --certificate-identity "$identity" \
    --certificate-github-workflow-repository "$repository" \
    --certificate-github-workflow-ref "$branch" \
    --certificate-github-workflow-sha "$sha" \
    > /dev/null; then
    echo "ok    signature   $reference"
  else
    echo "FAIL  signature   $reference: no signature by $identity for $sha"
    failures=$((failures + 1))
  fi

  if gh attestation verify "oci://$reference" \
    --repo "$repository" \
    --signer-workflow "$repository/$workflow" \
    --source-ref "$branch" \
    --source-digest "$sha" \
    --deny-self-hosted-runners \
    > /dev/null; then
    echo "ok    provenance  $reference"
  else
    echo "FAIL  provenance  $reference: no SLSA provenance from $workflow on $branch for $sha"
    failures=$((failures + 1))
  fi
done

if [ "$failures" -gt 0 ]; then
  echo "$failures check(s) failed: these images cannot be traced to a reviewed commit of main." >&2
  exit 1
fi
echo "Both images of $sha were built, attested and signed by CI on main."
