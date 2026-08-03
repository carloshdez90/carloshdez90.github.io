#!/usr/bin/env python3
"""
Keeps the served tree honest in both directions:

  * BROKEN  — a page points at a file that is not there. Visible immediately.
  * ORPHAN  — a file is served but nothing points at it. Invisible for years.

The second is why this exists. A stylesheet from a previous version of the site
sat at /css/main.css long after every page had stopped linking it, still public,
still carrying the old palette. Nothing breaks, so nothing tells you.

    ./tools/check-assets.py            # report, exit 1 on either problem
    ./tools/check-assets.py -v         # also list what is in use

A note on the method, because the obvious approach is wrong: matching filenames
as substrings gives false confidence in both directions. 'twitter.svg' appears
to be referenced by any page carrying a twitter:card meta tag; a thumbnail named
'37-27.jpg' matches path coordinates inside unrelated SVGs. References are only
counted from attributes that actually load a resource, from CSS url(), and from
`content=` on og:image / twitter:image.

Some files are reachable without any page linking them — the browser asks for
them by convention, or a crawler does. Those are listed in ENTRY_POINTS.
"""

import glob
import io
import os
import re
import sys
from urllib.parse import urlparse, unquote

SITE = 'carloshdez.com'

# Requested by convention rather than by a link, so absence of references here
# means nothing. Keep this list short and justified.
ENTRY_POINTS = {
    'index.html',            # /
    'index.es.html',         # language switch target, also linked
    'favicon.ico',           # requested at /favicon.ico with no markup at all
    'robots.txt',            # crawlers
    'sitemap.xml',           # named by robots.txt
    'CNAME',                 # GitHub Pages custom domain
    'site.webmanifest',      # linked, but harmless to list
    '.vercelignore',
    '.gitignore',
    '.htaccess',
}

# References that live inside JSON rather than in markup: the Person schema in
# the JSON-LD block, and the icon list in site.webmanifest ("src"). Missing the
# manifest here reported both PWA icons as orphans on the first run.
JSONLD_URL = re.compile(r'"(?:image|logo|url|contentUrl|src)"\s*:\s*"([^"]+)"')

ATTR = re.compile(r'''\b(?:src|href|srcset|poster)\s*=\s*["']([^"']+)["']''', re.I)
OGIMG = re.compile(
    r'''<meta[^>]+(?:og:image|twitter:image)["'][^>]*content\s*=\s*["']([^"']+)["']''',
    re.I)
CSSU = re.compile(r'''url\(\s*['"]?([^'")]+)['"]?\s*\)''', re.I)

TEXT_EXT = ('.html', '.css', '.xml', '.webmanifest', '.json', '.svg', '.txt')
ASSET_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf', '.ico', '.css',
             '.js', '.woff', '.woff2', '.webmanifest', '.xml', '.txt')


def tracked_files():
    """Everything git would ship, minus what .vercelignore holds back."""
    import subprocess
    out = subprocess.run(['git', 'ls-files'], capture_output=True, text=True).stdout.split()
    out += subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'],
                          capture_output=True, text=True).stdout.split()

    ignored = []
    if os.path.exists('.vercelignore'):
        for line in io.open('.vercelignore', encoding='utf-8'):
            line = line.split('#')[0].strip()
            if line:
                ignored.append(line.rstrip('/'))

    def served(f):
        for pat in ignored:
            if f == pat or f.startswith(pat + '/'):
                return False
        return True

    # git ls-files still lists a tracked file after it is deleted from disk.
    # Filtering on existence is what makes a dangling reference detectable at
    # all — without it, deleting a linked file reads as "still there".
    return sorted({f for f in set(out) if served(f) and os.path.exists(f)})


def resolve(raw, from_file):
    """Turn one reference into a repo-relative path, or None if external."""
    u = raw.strip().split(',')[0].split(' ')[0]
    if not u or u.startswith(('data:', 'mailto:', '#', 'javascript:', 'tel:')):
        return None
    p = urlparse(u)
    if p.scheme in ('http', 'https'):
        if p.netloc != SITE and not p.netloc.endswith('.' + SITE):
            return None
        if p.netloc != SITE:          # a different host on the same domain
            return None
        path = p.path or '/'
    elif p.scheme:
        return None
    else:
        path = u
    path = unquote(path.split('?')[0].split('#')[0])
    if path.endswith('/'):
        path += 'index.html'
    if path.startswith('/'):
        return path.lstrip('/')
    return os.path.normpath(os.path.join(os.path.dirname(from_file), path))


def main():
    verbose = '-v' in sys.argv or '--verbose' in sys.argv
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

    files = tracked_files()
    present = set(files)
    sources = [f for f in files if f.endswith(TEXT_EXT)]

    referenced = {}                    # path -> the files that point at it
    for f in sources:
        try:
            txt = io.open(f, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        raws = (ATTR.findall(txt) + OGIMG.findall(txt) + CSSU.findall(txt)
                + JSONLD_URL.findall(txt))
        for raw in raws:
            target = resolve(raw, f)
            if target and target != f:
                referenced.setdefault(target, []).append(f)

    broken = {t: srcs for t, srcs in referenced.items() if t not in present}

    assets = [f for f in files
              if f.endswith(ASSET_EXT) and os.path.basename(f) not in ENTRY_POINTS
              and f not in ENTRY_POINTS]
    orphans = [a for a in assets if a not in referenced]

    print(f'\n{len(files)} archivos servidos · {len(referenced)} referencias internas')

    if verbose:
        print('\n  en uso:')
        for a in sorted(set(assets) - set(orphans)):
            print(f'    {a}  <- {len(referenced[a])} pagina(s)')

    ok = True
    if broken:
        ok = False
        print(f'\n✗ {len(broken)} referencia(s) rota(s):\n')
        for t, srcs in sorted(broken.items()):
            print(f'  - {t}\n      citado en: ' + ', '.join(sorted(set(srcs))[:4]))

    if orphans:
        ok = False
        total = sum(os.path.getsize(o) for o in orphans if os.path.exists(o))
        print(f'\n✗ {len(orphans)} archivo(s) publicos sin una sola referencia '
              f'({total:,}B):\n')
        for o in orphans:
            print(f'  - {o}')
        print('\n  Borralos, o si son alcanzables a proposito agregalos a '
              'ENTRY_POINTS en este script.')

    if ok:
        print('✓ sin referencias rotas y sin archivos huerfanos\n')
        return 0
    print()
    return 1


if __name__ == '__main__':
    sys.exit(main())
