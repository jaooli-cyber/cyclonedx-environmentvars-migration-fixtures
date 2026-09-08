#!/usr/bin/env bash
set -euo pipefail

BASE_COMMIT="a1c8aeb2e4e6a72851fd937f210e9b5add1cf514"
CANDIDATE_COMMIT="0ebfa3951e5cf0976e16debcf14c0ef8687fb4ef"
BASE_TREE="c006ae3111e11ca64158a9e32664cd7705bd7f32"
CANDIDATE_TREE="fd058cd7108af73cc070ad90b96a759807cb87ea"
ROOT_SHA256="c18273619269372dbe3ec6a497daafc9f4729974d462fa0aed835ab9a0d62a23"
BASE_FORMULATION_SHA256="487fd1d6ff0a8b046c68d458a36e03e83e65f54bf029134e24af5a3e94ee8692"
CANDIDATE_FORMULATION_SHA256="f8072e7f79be45fd9189748923a509cad8e9749a368f5a0919905bdd1eb9d181"

if [[ $# -ne 1 ]]; then
  echo "usage: $0 OUTPUT_DIRECTORY" >&2
  exit 64
fi

output=$1
if [[ -e "$output" ]]; then
  echo "output already exists: $output" >&2
  exit 73
fi

mkdir -p "$output/base" "$output/candidate"
cache=$(mktemp -d)
trap 'rm -rf -- "$cache"' EXIT

git clone --quiet --filter=blob:none --no-checkout \
  https://github.com/CycloneDX/specification.git "$cache/specification"
git -C "$cache/specification" fetch --quiet origin \
  "$BASE_COMMIT" "+refs/pull/1088/head:refs/remotes/origin/pr-1088"

[[ "$(git -C "$cache/specification" rev-parse "$BASE_COMMIT^{commit}")" == "$BASE_COMMIT" ]]
[[ "$(git -C "$cache/specification" rev-parse "$CANDIDATE_COMMIT^{commit}")" == "$CANDIDATE_COMMIT" ]]
[[ "$(git -C "$cache/specification" rev-parse "$BASE_COMMIT:schema/2.0")" == "$BASE_TREE" ]]
[[ "$(git -C "$cache/specification" rev-parse "$CANDIDATE_COMMIT:schema/2.0")" == "$CANDIDATE_TREE" ]]

git -C "$cache/specification" archive "$BASE_COMMIT" schema/2.0 \
  | tar -x -C "$output/base" --strip-components=2
git -C "$cache/specification" archive "$CANDIDATE_COMMIT" schema/2.0 \
  | tar -x -C "$output/candidate" --strip-components=2

echo "$ROOT_SHA256  $output/base/cyclonedx-2.0.schema.json" | sha256sum -c --quiet
echo "$ROOT_SHA256  $output/candidate/cyclonedx-2.0.schema.json" | sha256sum -c --quiet
echo "$BASE_FORMULATION_SHA256  $output/base/model/cyclonedx-formulation-2.0.schema.json" | sha256sum -c --quiet
echo "$CANDIDATE_FORMULATION_SHA256  $output/candidate/model/cyclonedx-formulation-2.0.schema.json" | sha256sum -c --quiet

printf '%s\n' "base=$BASE_COMMIT" "candidate=$CANDIDATE_COMMIT" > "$output/REVISIONS.txt"
