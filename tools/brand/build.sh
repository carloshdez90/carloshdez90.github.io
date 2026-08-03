#!/usr/bin/env bash
#
# Regenerates every raster brand asset from its two vector sources:
#
#   favicon.svg           (repo root)  -> the icon, one hand-tuned outline
#   tools/brand/og-card.html           -> the social share cards
#
# Nothing here is edited by hand. Change the source, re-run this, commit both.
#
#   ./tools/brand/build.sh
#
# Requires Chrome (rendering) and ImageMagick (the .ico container).

set -euo pipefail

cd "$(dirname "$0")/../.."          # repo root
ROOT=$(pwd)
BRAND="$ROOT/tools/brand"

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || { echo "Chrome not found at $CHROME"; exit 1; }
command -v magick >/dev/null || { echo "ImageMagick (magick) not found"; exit 1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Chrome will not screenshot an .svg directly at a chosen size, so each source
# is wrapped in a page that pins it to exact pixels.
shoot() {                            # shoot <src-url> <w> <h> <out.png>
  local src=$1 w=$2 h=$3 out=$4
  "$CHROME" --headless --disable-gpu --hide-scrollbars \
            --default-background-color=00000000 \
            --window-size="$w,$h" --screenshot="$out" "$src" >/dev/null 2>&1
  [ -s "$out" ] || { echo "failed to render $out"; exit 1; }
}

wrap() {                             # wrap <svg-path> <px> -> prints file:// url
  local svg="$1"
  local px="$2"
  local page="$TMP/wrap-$px-$(basename "$svg" .svg).html"
  {
    printf '<style>html,body{margin:0;padding:0;width:%spx;height:%spx;overflow:hidden}\n' "$px" "$px"
    printf 'img{display:block;width:%spx;height:%spx}</style>\n' "$px" "$px"
    printf '<img src="file://%s/%s">\n' "$ROOT" "$svg"
  } > "$page"
  echo "file://$page"
}

echo "==> icon"
# Rounded, cream — the .ico fallback for browsers that ignore the SVG.
for px in 16 32 48; do
  shoot "$(wrap tools/brand/_ico.svg "$px")" "$px" "$px" "$TMP/ico-$px.png"
done
magick "$TMP/ico-16.png" "$TMP/ico-32.png" "$TMP/ico-48.png" "$ROOT/favicon.ico"

# Square, opaque — iOS applies its own mask and paints black behind alpha.
shoot "$(wrap tools/brand/_apple.svg 180)" 180 180 "$ROOT/apple-touch-icon.png"
shoot "$(wrap tools/brand/_apple.svg 192)" 192 192 "$ROOT/icon-192.png"
shoot "$(wrap tools/brand/_apple.svg 512)" 512 512 "$ROOT/icon-512.png"

echo "==> share cards"
shoot "file://$BRAND/og-card.html"          1200 630 "$ROOT/og-card.png"
shoot "file://$BRAND/og-card.html?lang=es"  1200 630 "$ROOT/og-card.es.png"

echo
for f in favicon.svg favicon.ico apple-touch-icon.png icon-192.png icon-512.png \
         og-card.png og-card.es.png; do
  printf '  %-24s %s\n' "$f" "$(magick identify -format '%wx%h %b' "$ROOT/$f" 2>/dev/null | head -1)"
done

# The card reuses the site's palette, so a rebuild is the right moment to catch
# it drifting away from the pages.
echo
echo "==> design tokens"
"$ROOT/tools/check-tokens.py"
