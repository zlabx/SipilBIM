#!/usr/bin/env bash
# Rehearses publish.sh against a fake `aws` that stores objects in a local folder, so the decision logic
# (first publish, same version, newer, older, immutable installer) is tested without R2 credentials.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
script="$here/publish-r2.sh"
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
export FAKE_R2="$work/r2"; mkdir -p "$FAKE_R2" "$work/bin"

cat > "$work/bin/aws" <<'SHIM'
#!/usr/bin/env bash
# minimal `aws s3 cp` / `aws s3api head-object` over $FAKE_R2/<bucket>/<key>
loc() { local u=${1#s3://}; echo "$FAKE_R2/$u"; }
meta=""; key=""; bucket=""; pos=()
while [ $# -gt 0 ]; do
  case "$1" in
    --metadata) meta=$2; shift 2;;
    --bucket) bucket=$2; shift 2;;
    --key) key=$2; shift 2;;
    --endpoint-url|--content-type|--content-disposition|--cache-control) shift 2;;
    --only-show-errors) shift;;
    *) pos+=("$1"); shift;;
  esac
done
case "${pos[0]} ${pos[1]}" in
  "s3 cp")
    src=${pos[2]}; dst=${pos[3]}
    if [[ $src == s3://* ]]; then [ -f "$(loc "$src")" ] || exit 1; cp "$(loc "$src")" "$dst"
    else mkdir -p "$(dirname "$(loc "$dst")")"; cp "$src" "$(loc "$dst")"; echo "$meta" > "$(loc "$dst").meta"; fi;;
  "s3api head-object")
    f="$FAKE_R2/$bucket/$key"; [ -f "$f" ] || exit 254
    m=$(cat "$f.meta" 2>/dev/null || true); sha=$(tr ',' '\n' <<<"$m" | sed -n 's/^sha256=//p')
    echo "{\"Metadata\":{\"sha256\":\"$sha\"}}";;
  *) echo "fake aws: unsupported ${pos[*]}" >&2; exit 2;;
esac
SHIM
chmod +x "$work/bin/aws"; export PATH="$work/bin:$PATH"

export R2_BUCKET=apps S3_ENDPOINT=https://fake APP=sipilbim PREFIX=sipilbim MAGIC_HEX=4d5a \
       SKIP_PUBLIC_CHECK=1 PUBLIC_BASE=https://sipilstock.com
mk() { { printf 'MZ'; head -c "$2" /dev/urandom; } > "$work/$1"; }
# run <file> <version>: output goes to last.log (no pipe, so `set -o pipefail` cannot misfire)
run() { "$script" "$@" > "$work/last.log" 2>&1 || true; }
said() { grep -q -- "$1" "$work/last.log"; }
ver() { jq -r .version "$FAKE_R2/apps/sipilbim/desktop/latest.json"; }
ok() { echo "ok - $1"; }
bad() { echo "FAIL - $1"; echo "--- last output:"; cat "$work/last.log"; exit 1; }
f() { echo "$work/sipilbim-setup-v$1.exe"; }

mk a.bin 2000; cp "$work/a.bin" "$(f 0.3.0)"
mk b.bin 3000; cp "$work/b.bin" "$(f 0.4.0)"
mk c.bin 2500; cp "$work/c.bin" "$(f 0.10.0)"
mk d.bin 2100

run "$(f 0.3.0)" 0.3.0
said "published sipilbim 0.3.0" || bad "first publish"
[ "$(ver)" = 0.3.0 ] || bad "manifest version"
[ -f "$FAKE_R2/apps/sipilbim/desktop/0.3.0/sipilbim-setup-v0.3.0.exe" ] || bad "versioned installer missing"
jq -e '.schema==1 and .app=="sipilbim" and .installer.size==2002 and (.installer.sha256|length)==64' \
  "$FAKE_R2/apps/sipilbim/desktop/latest.json" > /dev/null || bad "manifest content"
ok "first publish writes the installer and the manifest"

run "$(f 0.3.0)" 0.3.0
said "already published" || bad "same version"
ok "a version that is already published is left alone"

run "$(f 0.4.0)" 0.4.0
said "published sipilbim 0.4.0" || bad "newer"
[ "$(ver)" = 0.4.0 ] || bad "latest did not move to 0.4.0"
ok "a newer version moves latest"

run "$(f 0.10.0)" 0.10.0
[ "$(ver)" = 0.10.0 ] || bad "0.10.0 must beat 0.4.0 (numeric order)"
ok "0.10.0 counts as newer than 0.4.0"

run "$(f 0.3.0)" 0.3.0
[ "$(ver)" = 0.10.0 ] || bad "latest moved backwards"
ok "latest never moves backwards"

# Same version path, different bytes: the manifest is removed so the version check passes, then refused.
rm "$FAKE_R2/apps/sipilbim/desktop/latest.json"
cp "$work/d.bin" "$(f 0.3.0)"
run "$(f 0.3.0)" 0.3.0
said "different content" || bad "immutability"
ok "an installer path is never overwritten with different bytes"

printf 'not an exe' > "$(f 0.5.0)"
run "$(f 0.5.0)" 0.5.0
said "not the expected kind" || bad "magic bytes"
ok "a file of the wrong kind is refused"

run "$(f 0.4.0)" 0.5.0-rc1
said "not a plain numeric version" || bad "pre-release"
ok "pre-release versions are not published"

echo "all publish.sh checks passed"
