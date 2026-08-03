#!/usr/bin/env python3
"""
Guards the one thing that inline CSS cannot guarantee on its own: that the
design tokens are the same on every page.

The site inlines its CSS deliberately — it removes a render-blocking request,
and gzipped it costs under 3 KB a page. The price is that the palette lives as
14 hand-maintained copies. This turns "I remembered to change all of them" into
something a machine checks.

    ./tools/check-tokens.py            # report, exit 1 on drift
    ./tools/check-tokens.py -v         # also print every token and its value

Checks, in order:

  1. Every page declares the same token names, in both the light and the dark
     scope. A page missing a token is drift that has already happened.
  2. Every token has the same value everywhere.
  3. The theme-init script — the one that must stay inline to avoid a flash of
     the wrong theme on load — is byte-identical across pages.
  4. Templates under tools/ (the share card) reuse the palette, so any token
     they do declare must match the site. They are allowed to declare a subset.

Exits 0 when everything agrees, 1 otherwise. No dependencies.
"""

import glob
import io
import os
import re
import sys

LIGHT_SEL = ':root, :root[data-theme="light"]'
DARK_SEL = '[data-theme="dark"]'


def css_block(css, selector):
    """Return the body of the rule for `selector`, matching braces properly.

    A regex that stops at the first '}' is wrong the moment a block contains a
    nested rule, so scan instead.
    """
    i = css.find(selector)
    if i == -1:
        return None
    i = css.find('{', i)
    if i == -1:
        return None
    depth, start = 0, i + 1
    for j in range(i, len(css)):
        if css[j] == '{':
            depth += 1
        elif css[j] == '}':
            depth -= 1
            if depth == 0:
                return css[start:j]
    return None


def inline_css(html):
    return "\n".join(re.findall(r'<style[^>]*>(.*?)</style>', html, re.S))


def theme_init(html):
    """The IIFE that sets data-theme before first paint."""
    for body in re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S):
        if 'data-theme' in body and 'localStorage' in body:
            return re.sub(r'\s+', ' ', body).strip()
    return None


def tokens(block):
    if not block:
        return {}
    return {name: val.strip()
            for name, val in re.findall(r'(--[a-z0-9-]+)\s*:\s*([^;]+);', block)}


def light_block(css):
    """The light palette.

    Pages scope it as ':root, :root[data-theme="light"]' so the theme toggle can
    override it; standalone templates like the share card just use ':root'.
    Accept either, or a template that drifts is silently never compared.
    """
    return css_block(css, LIGHT_SEL) or css_block(css, ':root')


def collect(path):
    html = io.open(path, encoding='utf-8').read()
    css = inline_css(html)
    return {
        'light': tokens(light_block(css)),
        'dark': tokens(css_block(css, DARK_SEL)),
        'theme_init': theme_init(html),
    }


def main():
    verbose = '-v' in sys.argv or '--verbose' in sys.argv
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    os.chdir(root)

    pages = sorted(glob.glob('*.html') + glob.glob('notes/*.html'))
    partials = sorted(glob.glob('tools/**/*.html', recursive=True))
    if not pages:
        print('no pages found — run this from the repo, not elsewhere')
        return 1

    data = {p: collect(p) for p in pages + partials}
    problems = []

    # 1 + 2 — token names and values across the real pages
    for scope in ('light', 'dark'):
        names = {p: set(data[p][scope]) for p in pages}
        expected = set.union(*names.values()) if names else set()

        for p in pages:
            missing = expected - names[p]
            if missing:
                problems.append(
                    f'{p}: no declara {len(missing)} token(s) en scope {scope}: '
                    + ', '.join(sorted(missing)))

        for name in sorted(expected):
            values = {}
            for p in pages:
                v = data[p][scope].get(name)
                if v is not None:
                    values.setdefault(v, []).append(p)
            if len(values) > 1:
                lines = [f'{scope} {name} tiene {len(values)} valores distintos:']
                for v, ps in sorted(values.items(), key=lambda kv: -len(kv[1])):
                    lines.append(f'      {v}   en {len(ps)} pagina(s): '
                                 + ', '.join(sorted(ps)[:3])
                                 + (' …' if len(ps) > 3 else ''))
                problems.append('\n    '.join(lines))
            elif verbose and values:
                print(f'  {scope:<6} {name:<18} {next(iter(values))}')

    # 3 — the theme-init script
    inits = {}
    for p in pages:
        inits.setdefault(data[p]['theme_init'], []).append(p)
    if len(inits) > 1:
        problems.append(
            f'el script de tema difiere entre paginas ({len(inits)} variantes): '
            + '; '.join(f'{len(ps)}x {sorted(ps)[0]}' for ps in inits.values()))
    if None in inits:
        problems.append('paginas sin script de tema (van a parpadear en modo '
                        'oscuro): ' + ', '.join(sorted(inits[None])))

    # 4 — templates may declare a subset, but never a conflicting value
    canonical = data[pages[0]]['light']
    for p in partials:
        for name, val in data[p]['light'].items():
            if name in canonical and canonical[name] != val:
                problems.append(f'{p}: {name} = {val}, pero el sitio usa '
                                f'{canonical[name]}')

    n_tokens = len(set(data[pages[0]]['light']) | set(data[pages[0]]['dark']))
    print(f'\n{len(pages)} paginas · {len(partials)} plantilla(s) · '
          f'{n_tokens} tokens por pagina')

    if problems:
        print(f'\n✗ {len(problems)} problema(s):\n')
        for pr in problems:
            print(f'  - {pr}')
        print()
        return 1

    print('✓ tokens, valores y script de tema consistentes en todo el sitio\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
