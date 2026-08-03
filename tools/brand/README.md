# Brand assets

Everything the site needs to have an identity in a browser tab and in a shared
link. Two vector sources, everything else generated.

```
./tools/brand/build.sh
```

## Sources — edit these

| File | Produces |
|---|---|
| `../../favicon.svg` | `favicon.ico`, `apple-touch-icon.png`, `icon-192.png`, `icon-512.png` |
| `og-card.html` | `og-card.png`, `og-card.es.png` |

`_ico.svg` and `_apple.svg` are flattened copies of `favicon.svg` — same artwork
without the `prefers-color-scheme` block, because a `.ico` and a PNG have no
theme to respond to. If the mark changes, change all three.

## The mark

The capital **C** of [Newsreader](https://fonts.google.com/specimen/Newsreader),
the serif the site sets its masthead in, at `wght 600 / opsz 14`. It was pulled
out of the variable font as an outline rather than referenced as text, so it
renders identically on a machine that has never seen the webfont.

Weight 600 rather than the masthead's 500: at 16px the hairline of a 500 breaks
up and the C reads as an O. `opsz 14` rather than 36 for the same reason — the
display optical size thins the strokes exactly where a favicon cannot afford it.

`favicon.svg` carries both themes and switches with the browser, wine on cream
in light and a lifted wine on near-black in dark. The rasters are cream-backed
only; that is the fallback path and cream stays legible against either chrome.

`apple-touch-icon.png` is square and fully opaque on purpose. iOS applies its
own rounded mask and paints black behind any transparency, so shipping our own
corners would round it twice.

## The share cards

1200×630, referenced by `og:image` / `twitter:image` in `index.html` and
`index.es.html`. They exist because `twitter:card` is set to
`summary_large_image`, which promises a wide image — the previous `og:image` was
the 400×400 portrait, so every share rendered as a cropped thumbnail.

The copy in `og-card.html` duplicates the masthead and hero of the two index
pages. **It does not read them.** If the hero changes, change the card and
re-run the build.

## After regenerating

Facebook, LinkedIn and X cache cards aggressively and will keep serving the old
one for days. Force a re-scrape:

- <https://developers.facebook.com/tools/debug/>
- <https://www.linkedin.com/post-inspector/>
- <https://cards-dev.twitter.com/validator>

## Design tokens

`build.sh` finishes by running `../check-tokens.py`, which verifies that the 16
custom properties are declared with the same values on all 14 pages, that the
theme-init script is identical everywhere, and that the palette in
`og-card.html` still matches the site.

The pages inline their CSS on purpose — it removes a render-blocking request and
costs under 3 KB gzipped per page — but that means the palette exists as 14
copies. The checker is what keeps those copies honest. Run it on its own with:

```
./tools/check-tokens.py -v
```

## Requirements

Chrome (rendering) and ImageMagick (assembling the multi-resolution `.ico`).
No fonts to install — the cards pull Newsreader, DM Sans and JetBrains Mono
from Google Fonts at render time, so the build needs network.
