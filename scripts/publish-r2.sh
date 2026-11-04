#!/usr/bin/env bash
# Publishes one installer to the PRIVATE R2 bucket, where the sipilstock-apps Worker serves it read-only at
# <PUBLIC_BASE>/<prefix>/... . The same file is used by zlabx/Apps (launcher/packaging/r2/publish.sh, its MSI)
# and zlabx/SipilBIM (scripts/publish-r2.sh, its installer) and must stay identical in both; zlabx/Apps
# `scripts/desktop_publish.py` writes the same manifest.
#
#   usage: publish.sh <installer file> <version>
#   env:   R2_BUCKET  S3_ENDPOINT  (+ AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY for the aws CLI)
#          APP        manifest "app" id, e.g. launcher | sipilbim
#          PREFIX     R2 folder / URL path, e.g. launcher | sipilbim
#          MAGIC_HEX  first bytes of a valid file: d0cf11e0 (MSI) | 4d5a (Windows exe)
#          ALIAS      optional stable file name for a "latest" download link, e.g. SipilStockApps-x64.msi
#          NOTES_URL  optional release notes page
#          PUBLIC_BASE (default https://sipilstock.com)   SKIP_PUBLIC_CHECK=1 (tests only)
#
# Layout:  <prefix>/desktop/<version>/<file>   immutable, uploaded first
#          <prefix>/<ALIAS>                    stable "latest" copy (optional)
#          <prefix>/desktop/latest.json        manifest, uploaded LAST
# Rules:   "latest" never moves backwards; a version that is already published is left alone (bump the
#          version to publish again); an installer path is never overwritten with different bytes.
set -euo pipefail

file=${1:?usage: publish.sh <installer file> <version>}
version=${2:?usage: publish.sh <installer file> <version>}
: "${R2_BUCKET:?}" "${S3_ENDPOINT:?}" "${APP:?}" "${PREFIX:?}" "${MAGIC_HEX:?}"
public=${PUBLIC_BASE:-https://sipilstock.com}
public=${public%/}
name=$(basename "$file")
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

notice() { echo "::notice title=R2 publish::$*"; echo "$*"; }
fail() { echo "::error title=R2 publish::$*"; echo "ERROR: $*" >&2; exit 1; }
s3() { aws "$@" --endpoint-url "$S3_ENDPOINT"; }

[[ "$version" =~ ^[0-9]+(\.[0-9]+)*$ ]] || { notice "'$version' is not a plain numeric version; not publishing"; exit 0; }
[[ "$name" =~ ^[A-Za-z0-9._-]+$ ]] || fail "unsafe file name '$name'"
[ -f "$file" ] || fail "$file not found"
n=$(( ${#MAGIC_HEX} / 2 ))
[ "$(head -c "$n" "$file" | od -An -tx1 | tr -d ' \n')" = "$MAGIC_HEX" ] || fail "$name does not start with $MAGIC_HEX: not the expected kind of installer"

size=$(wc -c < "$file" | tr -d ' ')
sha=$(sha256sum "$file" | cut -d' ' -f1)
key="$PREFIX/desktop/$version/$name"
manifest_key="$PREFIX/desktop/latest.json"
echo "installer: $name  $size bytes  sha256 $sha"

# --- Should this version be published?
if s3 s3 cp "s3://$R2_BUCKET/$manifest_key" "$tmp/existing.json" --only-show-errors 2>/dev/null; then
  have=$(jq -r '.version // empty' "$tmp/existing.json")
  if [ -n "$have" ]; then
    if [ "$have" = "$version" ]; then notice "$version is already published; bump the version to publish again"; exit 0; fi
    newest=$(printf '%s\n%s\n' "$have" "$version" | sort -V | tail -n 1)
    if [ "$newest" = "$have" ]; then notice "R2 already serves $have, newer than $version; leaving it"; exit 0; fi
    echo "R2 serves $have; publishing $version"
  fi
else
  echo "R2 has no manifest yet; first publish of $APP"
fi

# --- 1. The versioned installer (immutable)
if s3 s3api head-object --bucket "$R2_BUCKET" --key "$key" > "$tmp/head.json" 2>/dev/null; then
  existing_sha=$(jq -r '.Metadata.sha256 // ""' "$tmp/head.json")
  [ "$existing_sha" = "$sha" ] || fail "$key already exists with different content ($existing_sha); bump the version instead of overwriting"
  echo "installer already in R2 with the same SHA-256"
else
  s3 s3 cp "$file" "s3://$R2_BUCKET/$key" --only-show-errors \
    --content-type application/octet-stream \
    --content-disposition "attachment; filename=\"$name\"" \
    --cache-control "public, max-age=31536000, immutable" \
    --metadata "sha256=$sha"
fi

# --- 2. Stable "latest" copy for download links (short cache so updates show quickly)
if [ -n "${ALIAS:-}" ]; then
  [[ "$ALIAS" =~ ^[A-Za-z0-9._-]+$ ]] || fail "unsafe alias '$ALIAS'"
  s3 s3 cp "$file" "s3://$R2_BUCKET/$PREFIX/$ALIAS" --only-show-errors \
    --content-type application/octet-stream \
    --content-disposition "attachment; filename=\"$ALIAS\"" \
    --cache-control "public, max-age=300" \
    --metadata "sha256=$sha,version=$version"
fi

# --- 3. The manifest, last, so it never points at a file that is not there yet
jq -n --arg app "$APP" --arg version "$version" --arg at "${RELEASED_AT:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}" \
      --arg notes "${NOTES_URL:-}" --arg name "$name" --arg url "$public/$key" \
      --argjson size "$size" --arg sha "$sha" \
  '{schema:1, app:$app, version:$version, released_at:$at, notes_url:$notes,
    installer:{name:$name, url:$url, size:$size, sha256:$sha}}' > "$tmp/latest.json"
s3 s3 cp "$tmp/latest.json" "s3://$R2_BUCKET/$manifest_key" --only-show-errors \
  --content-type application/json --cache-control "public, max-age=60"

# --- 4. What the public URL serves
if [ "${SKIP_PUBLIC_CHECK:-}" != 1 ]; then
  head_len() { curl -fsSI "$1" | tr -d '\r' | awk -F': *' 'tolower($1)=="content-length"{print $2}'; }
  for url in "$public/$key" ${ALIAS:+"$public/$PREFIX/$ALIAS"}; do
    [ "$(head_len "$url")" = "$size" ] || fail "$url does not serve $size bytes"
    magic=$(curl -fsS -r "0-$((n - 1))" "$url" | od -An -tx1 | tr -d ' \n')
    [ "$magic" = "$MAGIC_HEX" ] || fail "$url does not start with $MAGIC_HEX (got $magic)"
  done
  curl -fsS -H 'Cache-Control: no-cache' "$public/$manifest_key" | jq -S . > "$tmp/live.json"
  jq -S . "$tmp/latest.json" | diff -q - "$tmp/live.json" > /dev/null || fail "the live manifest differs from the uploaded one"
  echo "public check OK: $public/$key ($size bytes), manifest matches"
fi
notice "published $APP $version ($name, $size bytes)"
echo "::notice title=manifest::$(jq -c . "$tmp/latest.json")"
