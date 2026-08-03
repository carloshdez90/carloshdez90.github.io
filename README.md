# carloshdez.com

The personal site of Carlos Hernández — a bilingual, hand-written static site.
No framework, no bundler, no build step for the pages themselves.

This file explains how the thing is put together and, where a choice looks
unusual, why it was made that way.

---

## 1. What is here

```
index.html                  the site, English
index.es.html               the site, Spanish
notes/                      6 articles × 2 languages = 12 pages
img/
  carlos.png                portrait; used by JSON-LD and the share card
  notes/*.jpg               one 1200×630 share card per article
cv-carlos-hernandez.pdf     CV, English
cv-carlos-hernandez.es.pdf  CV, Spanish
favicon.svg  favicon.ico  apple-touch-icon.png  icon-192.png  icon-512.png
og-card.png  og-card.es.png    home-page share cards, one per language
site.webmanifest  sitemap.xml  robots.txt  CNAME
tools/                      build + verification scripts — NOT served, see §3
.github/workflows/checks.yml
```

14 pages, 36 served files. That is the whole site.

The English home page is organised in six numbered sections: **I** Production
work · **II** Field notes · **III** Research · **IV** Speaking · **V** Workshop ·
**VI** About. The Spanish page mirrors it exactly.

---

## 2. No build step, and why

Every page is a complete, self-contained HTML document: markup, CSS in a
`<style>` block, and two small scripts inline. You can open any file in a
browser, straight off disk, and see the real page.

That is a deliberate trade, not laziness:

- **The CSS is inline** because it removes a render-blocking request. Gzipped it
  costs about **2.7 KB per page** — the raw 12 KB number is misleading. Pulling
  it into `css/site.css` would save those 2.7 KB starting from the *second* page
  a visitor opens, at the cost of an extra round trip on the *first*. The
  dominant visit here is one page, opened from a link, then gone.
- **The CSS is not identical across pages.** The home page carries 12.3 KB;
  articles carry 7.3–9.4 KB because each one brings the rules its own content
  needs. A single shared file would either ship everything to everyone or
  fragment into several files anyway.
- **The price** is that the palette lives as 14 hand-maintained copies. That is
  what `tools/check-tokens.py` exists for (§5). The problem was never the
  duplication; it was that nothing could see it drift.

**When this stops being the right call:** past roughly 30 pages, or the moment
shared components are wanted, the answer is to generate pages from templates —
not to link an external stylesheet. Extracting the CSS solves the smaller half
of the problem.

### The two inline scripts

```js
// 1. in <head> — must run before first paint
(function () {
  var stored = null;
  try { stored = localStorage.getItem('theme'); } catch (e) {}
  document.documentElement.setAttribute('data-theme', stored || 'light');
})();

// 2. at end of body — the toggle button
```

The first one **cannot** be moved to an external file. It runs before the first
paint so a returning dark-mode visitor never sees a white flash. An external
`<script>` is fetched after parsing begins, which reintroduces exactly that
flash. Inline here is the correct implementation, not a shortcut.

Both blocks are byte-identical on all 14 pages, and CI enforces that.

---

## 3. Deployment

The site is served by **Vercel**, despite the repository being named
`carloshdez90.github.io`. GitHub Pages holds the `CNAME` and 301-redirects
everything to `carloshdez.com`, so there is one effective host.

Vercel deploys the tree **verbatim**: every file in the repo becomes a public
URL. There is no directory listing, but the repo is public, so paths are not
secret either.

What is *not* served:

| Excluded by | What |
|---|---|
| `.vercelignore` | `tools/`, `.htaccess` |
| Vercel's own defaults | `.git`, `.gitignore`, `.DS_Store`, `.env*` |

`.vercelignore` is the right mechanism here — **not** `_config.yml` or
`.nojekyll`, which are Jekyll concepts and would do nothing on Vercel.

---

## 4. Bilingual structure

Each page exists twice, distinguished by an `.es` infix:

```
/                            /index.es.html
/notes/deletable.html        /notes/deletable.es.html
```

Every page declares the pair, plus an `x-default`:

```html
<link rel="alternate" hreflang="en" href="https://carloshdez.com/…">
<link rel="alternate" hreflang="es" href="https://carloshdez.com/….es.html">
<link rel="alternate" hreflang="x-default" href="https://carloshdez.com/…">
```

Language-dependent things must be switched **per page**, and each has been
missed at least once:

- `og:image` → `og-card.png` / `og-card.es.png`
- `og:locale` / `og:locale:alternate`
- the CV link → `cv-carlos-hernandez.pdf` / `cv-carlos-hernandez.es.pdf`
- `<html lang>`, `canonical`, `description`

The Spanish CV once lagged three months behind the English one. Both PDFs are
now generated from a single content definition that lives in a separate private
repository; only the finished PDFs are copied here.

---

## 5. Verification — what runs, and when

Two scripts, both stdlib-only Python, no dependencies to install.

### `tools/check-tokens.py`

Guards what inline CSS cannot guarantee on its own:

1. All 14 pages declare the same 16 design tokens, in the light scope
   (`:root, :root[data-theme="light"]`) and the dark scope
   (`[data-theme="dark"]`).
2. Every token holds the same value everywhere.
3. The theme-init script is byte-identical across pages.
4. `tools/brand/og-card.html` reuses the palette, so any token it declares must
   match the site. It may declare a subset.

### `tools/check-assets.py`

Checks the served tree in both directions:

- **Broken** — a page points at a file that is not there. Loud and obvious.
- **Orphan** — a file is served but nothing points at it. Silent for years.

The second is the reason it exists. A stylesheet from a previous version of the
site sat at `/css/main.css` long after every page had stopped linking it, still
public, still carrying the old violet palette. 38 such files were removed in one
sweep. Nothing was broken, so nothing had ever said a word.

If a file is meant to be reachable without any page linking it (`favicon.ico`,
`robots.txt`, `CNAME`…), add it to `ENTRY_POINTS` in that script rather than
letting the check go stale.

### When each runs

| | Trigger | Needs |
|---|---|---|
| `check-tokens.py` | **every push**, via Actions | python3 |
| `check-assets.py` | **every push**, via Actions | python3 + git |
| private-material grep | **every push**, via Actions | git |
| `tools/brand/build.sh` | **manual**, when the mark or card copy changes | Chrome, ImageMagick |

CI lives in GitHub Actions rather than a Vercel build command for a concrete
reason: `.vercelignore` keeps `tools/` out of what Vercel uploads, so a Vercel
build could not find the scripts. Actions checks out the full repo from git.

`build.sh` stays manual because it needs Chrome and ImageMagick, and its outputs
are committed binaries that change perhaps twice a year. It re-runs the token
check at the end, since regenerating the card is exactly when the card can drift
away from the site.

---

## 6. Brand assets

Two vector sources, everything else generated. Full detail in
[`tools/brand/README.md`](tools/brand/README.md).

```
./tools/brand/build.sh
```

| Source | Produces |
|---|---|
| `favicon.svg` | `favicon.ico`, `apple-touch-icon.png`, `icon-192.png`, `icon-512.png` |
| `tools/brand/og-card.html` | `og-card.png`, `og-card.es.png` |

The mark is the capital **C** of Newsreader — the serif the masthead is set in —
lifted out of the variable font as an outline, so it renders on machines that
have never seen the webfont. `favicon.svg` carries both themes and follows the
browser.

**The card copy is duplicated by hand from the hero. It does not read it.**
Change the hero, change `og-card.html`, re-run the build.

After regenerating, force a re-scrape or the old card is served for days:
[LinkedIn](https://www.linkedin.com/post-inspector/) ·
[Facebook](https://developers.facebook.com/tools/debug/) ·
[X](https://cards-dev.twitter.com/validator).

---

## 7. Typography and colour

Three families, all from Google Fonts:

| Role | Family | Used for |
|---|---|---|
| serif | Newsreader | masthead, hero, article prose |
| sans | DM Sans | UI, body text in listings |
| mono | JetBrains Mono | labels, metrics, code |

16 tokens define the palette. The anchors:

```
light   --bg #faf9f6   --text #18181c   --wine #7d2929   --gold #8a6e2f
dark    --bg #0c0c0e   --text #ebebec   --wine #a13a3a   --gold #c9a35e
```

Wine is the accent and the only saturated colour in the design. Never introduce
a token in one page alone — CI will reject it, correctly.

---

## 8. Editorial rules that are not style preferences

- **Client work is described by its engineering patterns and outcomes only.**
  Entries carrying enterprise work are labelled *"specifics under NDA"* and do
  not name the client. Estates, topology, vendor terms and cost figures stay
  out. The employer appears once, in the hero, as a fact of employment.
- **Metrics carry their window.** `−52% pipeline wall clock` is followed by
  *measured p50 over a 14-day window*. A number without its measurement
  conditions is a claim, not evidence.
- **No placeholders.** Nothing ships to the index until it is real. Two
  placeholder article entries were removed for this reason.
- **This repository is public.** The knowledge base it draws from is not, lives
  elsewhere, and must never appear here in any form. CI greps for it on every
  push.

---

## 9. Adding an article

1. Copy the closest existing pair in `notes/` — both languages. Never ship one
   without the other.
2. Update in both: `<title>`, `description`, `canonical`, all three `hreflang`
   links, `og:*`, `twitter:*`, and the `<html lang>` attribute.
3. Produce a 1200×630 card at `img/notes/<slug>.jpg` and point `og:image` at it.
4. Add the entry to the *Field notes* section of `index.html` **and**
   `index.es.html`.
5. Add both URLs to `sitemap.xml`, each with its `xhtml:link` alternates.
6. Run the checks:

```bash
./tools/check-tokens.py && ./tools/check-assets.py
```

Step 6 catches the two things most easily forgotten: a card that was never
created, and CSS copied from a page whose palette had moved on.

---

## 10. Local preview

No tooling required — the pages open straight from disk. For correct
root-absolute paths (`/favicon.svg`, `/og-card.png`), serve the folder:

```bash
python3 -m http.server 4321
```
