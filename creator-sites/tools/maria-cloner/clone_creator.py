#!/usr/bin/env python3
"""FAST creator private-preview cloner.

    python clone_creator.py <data.json> <out_worktree_dir> [--browser-check] [--no-commit] [--base youtube|tiktok|none]

data.json = a VERIFY-BRIEF.md "pass" file (slug, name, links, onlyfans_url, email, avatar_url, followers,
video_mode, youtube{channel_id,url,subs,videos[]}, tiktok{handle,videos[]}, pronouns_stated, left_out ...).

What it does (never deploys, pushes or emails):
  1. picks the finished base site by video_mode (youtube/mixed -> lucas-dell, tiktok -> matty-lee, none -> quinn-finite)
  2. git worktree add -b agent/<slug>-preview <out> 8be08f9   (repo: aynarilla-final-review)
  3. copies the base site to sites/<slug>/ (no public/, validation/, node_modules/, base media)
  4. regenerates every identity block (header slot, banner, menu, links, stats, collab, footer, DEFAULT/SOCIALS,
     build.py routes, check.mjs + browser-check.py expectations), then swaps all remaining tokens
     (video IDs, URLs, handles, names, slug, pronouns) in every text file
  5. downloads avatar + covers, writes media-catalog.json/.js, socials/followers/brand-config, provenance, README
  6. bubble-letters wordmark + Movie Club bubble, export-brand icons/social card
  7. npm run build, npm test, leak check (base name/handles/IDs must be 0 hits), commit sites/<slug>/** only
"""
import argparse, hashlib, html as H, io, json, math, os, re, shutil, socket, subprocess, sys, time
import urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

CODE = Path(os.environ.get('CREATOR_CODE_ROOT','C:/Users/Servi/code'))
REPO = Path(os.environ.get('CREATOR_SOURCE_REPO',str(CODE/'aynarilla-final-review')))
START_COMMIT = os.environ.get('CREATOR_START_COMMIT','8be08f9')
BASES = {
    'youtube': ('lucas-dell', Path(os.environ.get('CREATOR_BASE_YOUTUBE',str(CODE / 'creator-lucas-dell/sites/lucas-dell')))),
    'tiktok': ('matty-lee', Path(os.environ.get('CREATOR_BASE_TIKTOK',str(CODE / 'creator-matty-lee/sites/matty-lee')))),
    'none': ('quinn-finite', Path(os.environ.get('CREATOR_BASE_NONE',str(CODE / 'creator-quinn-finite/sites/quinn-finite')))),
}
SKIP_DIRS = {'public', 'validation', 'node_modules', '__pycache__', '.wrangler', '.wrangler-cache'}
TEXT_EXT = {'.html', '.js', '.json', '.css', '.py', '.mjs', '.md', '.jsonc', '.example', '.txt', '.sql'}
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
TODAY = date.today().isoformat()
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
MONTH = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

DOMAINS = [('onlyfans', 'onlyfans.com'), ('fanvue', 'fanvue.com'), ('fansly', 'fansly.com'), ('fanfix', 'fanfix.io'), ('instagram', 'instagram.com'),
           ('tiktok', 'tiktok.com'), ('youtube', 'youtube.com'), ('youtube', 'youtu.be'), ('x', 'x.com'), ('x', 'twitter.com'),
           ('twitch', 'twitch.tv'), ('kick', 'kick.com'), ('bluesky', 'bsky.app'), ('threads', 'threads.net'), ('threads', 'threads.com'),
           ('snapchat', 'snapchat.com'), ('facebook', 'facebook.com'), ('discord', 'discord.gg'), ('discord', 'discord.com'),
           ('linktree', 'linktr.ee'), ('linkme', 'link.me'), ('beacons', 'beacons.ai'), ('allmylinks', 'allmylinks.com'),
           ('wildskirts', 'wildskirts.com'), ('patreon', 'patreon.com'), ('kofi', 'ko-fi.com'), ('throne', 'throne.com')]
PNAME = {'onlyfans': 'OnlyFans', 'fanvue': 'Fanvue', 'fansly': 'Fansly', 'fanfix': 'Fanfix', 'instagram': 'Instagram', 'tiktok': 'TikTok', 'youtube': 'YouTube',
         'x': 'X', 'twitch': 'Twitch', 'kick': 'Kick', 'bluesky': 'Bluesky', 'threads': 'Threads', 'snapchat': 'Snapchat',
         'facebook': 'Facebook', 'discord': 'Discord', 'linktree': 'Linktree', 'linkme': 'LinkMe', 'beacons': 'Beacons',
         'allmylinks': 'AllMyLinks', 'wildskirts': 'WildSkirts', 'patreon': 'Patreon', 'kofi': 'Ko-fi', 'throne': 'Throne', 'website': 'Website'}
ORDER = ['onlyfans', 'fanvue', 'fansly', 'fanfix', 'instagram', 'tiktok', 'youtube', 'x', 'twitch', 'kick', 'bluesky', 'threads', 'snapchat',
         'facebook', 'discord', 'patreon', 'kofi', 'throne', 'wildskirts', 'website', 'linktree', 'linkme', 'beacons', 'allmylinks']
HUBKEYS = {'linktree', 'linkme', 'beacons', 'allmylinks', 'website'}
PAYWALL = {'onlyfans', 'fanvue', 'fansly', 'fanfix', 'wildskirts'}


class Fail(Exception):
    pass


# ----------------------------------------------------------------------------------------------------- helpers
def rd(p): return Path(p).read_text(encoding='utf-8')


def wr(p, s): Path(p).parent.mkdir(parents=True, exist_ok=True); Path(p).write_text(s, encoding='utf-8', newline='')


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jdump(o): return json.dumps(o, indent=2, ensure_ascii=False) + '\n'


def host(u):
    h = urllib.parse.urlsplit(u).netloc.lower().split('@')[-1].split(':')[0]
    for pre in ('www.', 'm.', 'mobile.'):
        if h.startswith(pre): h = h[len(pre):]
    return h


def disp(u):
    """URL without scheme, www. and trailing slash (the base's display form, e.g. linktr.ee/lucasdell)."""
    s = re.sub(r'^https?://', '', u.strip())
    s = re.sub(r'^www\.', '', s)
    return s.rstrip('/')


def plat_key(platform, url):
    h = host(url)
    for k, dm in DOMAINS:
        if h == dm or h.endswith('.' + dm): return k
    p = re.sub(r'[^a-z]', '', (platform or '').lower())
    p = {'twitter': 'x', 'yt': 'youtube', 'ig': 'instagram', 'of': 'onlyfans', 'hub': 'website', 'site': 'website',
         'officialsite': 'website', 'ownwebsite': 'website', 'linktr': 'linktree'}.get(p, p)
    return p if p in PNAME else 'website'


def handle_of(k, url):
    sp = urllib.parse.urlsplit(url)
    parts = [x for x in sp.path.split('/') if x]
    if k == 'website': return disp(url)
    if k == 'youtube' and parts and parts[0] in ('c', 'user', 'channel') and len(parts) > 1: return parts[1]
    if k == 'bluesky' and len(parts) > 1 and parts[0] == 'profile': return parts[1]
    return (parts[0] if parts else host(url)).lstrip('@')


def fmt_count(c):
    if isinstance(c, str): return c.strip()
    c = float(c)
    for div, suf in ((1e9, 'B'), (1e6, 'M'), (1e3, 'K')):
        if c >= div:
            v = c / div
            s = f'{v:.1f}'.rstrip('0').rstrip('.')
            return s + suf
    return str(int(c))


def nice_date(iso):
    y, m, d = (int(x) for x in iso[:10].split('-'))
    return f'{MON[m - 1]} {d}, {y}'


def fetch(url, timeout=25):
    if re.match(r'^[A-Za-z]:[\\/]', url) or url.startswith('file:'):
        return Path(url.removeprefix('file:///').removeprefix('file:')).read_bytes()
    parts=urllib.parse.urlsplit(url)
    url=urllib.parse.urlunsplit((parts.scheme,parts.netloc,urllib.parse.quote(parts.path,safe='/%:@'),urllib.parse.quote(parts.query,safe='=&%:+,/@?'),parts.fragment))
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def multi_replace(text, mapping, pre=r'', post=r'', flags=0):
    """Single-pass, longest-first replacement (no chained replacements)."""
    mapping = {k: v for k, v in mapping.items() if k and k != v}
    if not mapping: return text, 0
    keys = sorted(mapping, key=len, reverse=True)
    rx = re.compile(pre + '(' + '|'.join(re.escape(k) for k in keys) + ')' + post, flags)
    n = [0]
    if flags & re.I:
        low = {k.lower(): v for k, v in mapping.items()}
        def f(m): n[0] += 1; return low[m.group(1).lower()]
    else:
        def f(m): n[0] += 1; return mapping[m.group(1)]
    return rx.sub(f, text), n[0]


def sub1(text, pattern, repl, label, flags=re.S, count=1, optional=False):
    """Regex substitution that must match exactly `count` times (or 0 when optional)."""
    rx = re.compile(pattern, flags)
    hits = len(rx.findall(text))
    if hits == 0 and optional: return text
    if hits != count: raise Fail(f'{label}: expected {count} match(es), found {hits}')
    return rx.sub(repl if callable(repl) else (lambda m: repl), text)


def jsq(s):  # safe inside a JS single-quoted string
    return s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ')


def free_port(lo=18900, hi=18990):
    if os.environ.get('CREATOR_QA_PORT'):
        lo = hi = int(os.environ['CREATOR_QA_PORT'])
    for p in range(lo, hi + 1):
        with socket.socket() as s:
            try: s.bind(('127.0.0.1', p)); return p
            except OSError: continue
    raise Fail('no free port in %d-%d' % (lo, hi))


def run(cmd, cwd, env=None, check=True, timeout=900):
    r = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, encoding='utf-8', errors='replace',
                       shell=isinstance(cmd, str), timeout=timeout)
    if check and r.returncode:
        raise Fail(f'command failed ({r.returncode}): {cmd}\n{(r.stdout or "")[-3000:]}\n{(r.stderr or "")[-3000:]}')
    return r


# ----------------------------------------------------------------------------------------------------- identity
class Base:
    """Identity facts of the finished base site, read from its own files."""
    def __init__(self, mode, slug, d):
        self.mode, self.slug, self.dir = mode, slug, d
        self.brand = json.loads(rd(d / 'brand-config.json'))
        self.socials = json.loads(rd(d / 'assets/socials.json'))
        self.cat = json.loads(rd(d / 'assets/media-catalog.json'))
        self.name = self.brand['name']
        self.first = self.name.split()[0]
        self.last = self.name.split()[-1] if len(self.name.split()) > 1 else ''
        self.hub = self.brand['hub']
        idx = rd(d / 'index.html')
        self.emails = sorted(set(re.findall(r'mailto:([^"\'<>\s]+@[^"\'<>\s]+)', idx + rd(d / 'tools/build.py'))))
        his, her = len(re.findall(r'\bhis\b', idx)), len(re.findall(r'\bher\b', idx))
        self.pron = 'she' if her > his else 'he'
        bub = sorted((d / 'assets').glob('*-movie-bubble.webp'))
        self.bubble = bub[0].name if bub else ''
        self.long_ids = [v['id'] for v in self.cat.get('long', [])]
        self.all_ids = sorted({v['id'] for k in ('long', 'movies', 'profile', 'rail', 'shorts', 'all') for v in self.cat.get(k, []) if isinstance(v, dict)}
                              | {v['id'] for v in self.cat.get('excluded', []) if isinstance(v, dict) and 'id' in v})
        self.all_ids = sorted(set(self.all_ids) | set(re.findall(r'/assets/covers/([\w-]+?)-(?:youtube|public-cover)\.jpg', idx)))
        self.channel_id = self.cat.get('channelId', '')


class Creator:
    """Normalized new-creator identity from a VERIFY-BRIEF pass file."""
    def __init__(self, d, force_mode=None):
        self.raw = d
        self.slug = d['slug'].strip().lower()
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', self.slug): raise Fail('bad slug ' + self.slug)
        self.name = re.sub(r'\s+', ' ', d['name']).strip().replace("'", '\u2019')
        if re.search(r'[<>"\\]', self.name): raise Fail('name has unsafe characters')
        name_parts = self.name.split()
        natural_first = name_parts[1] if len(name_parts)>1 and name_parts[0].rstrip('.').lower()=='dr' else name_parts[0]
        self.first = (d.get('short_name') or natural_first).strip()
        self.first_slug = re.sub(r'[^a-z0-9]+', '-', self.first.lower()).strip('-') or self.slug
        self.email = (d.get('email') or '').strip() or None
        ps = (d.get('pronouns_stated') or 'unknown').lower()
        self.pron = 'she' if re.search(r'\bshe\b|\bher\b', ps) else 'he' if re.search(r'\bhe\b|\bhim\b', ps) else 'they' if 'they' in ps else 'name'
        # socials -------------------------------------------------------------------------------------
        soc = {}
        def add(platform, url):
            url = (url or '').strip()
            if not re.match(r'^https?://', url): return
            k = plat_key(platform, url)
            if k in soc:
                if soc[k]['url'].rstrip('/') == url.rstrip('/'): return
                if k != 'website': return
                n = 2
                while f'website{n}' in soc: n += 1
                k = f'website{n}'
            soc[k] = {'name': PNAME.get(re.sub(r'\d+$', '', k), 'Website'), 'handle': handle_of(re.sub(r'\d+$', '', k), url), 'url': url}
        if d.get('onlyfans_url'): add('OnlyFans', d['onlyfans_url'])
        for l in d.get('links') or []: add(l.get('platform', ''), l.get('url', ''))
        yt, tt = d.get('youtube') or {}, d.get('tiktok') or {}
        if yt and 'youtube' not in soc:
            add('YouTube', yt.get('url') or (f"https://www.youtube.com/channel/{yt['channel_id']}" if yt.get('channel_id') else ''))
        if tt and tt.get('handle') and 'tiktok' not in soc: add('TikTok', f"https://www.tiktok.com/@{tt['handle'].lstrip('@')}")
        if d.get('hub'): add('hub', d['hub'])
        rank = lambda k: ORDER.index(re.sub(r'\d+$', '', k)) if re.sub(r'\d+$', '', k) in ORDER else len(ORDER) - 5
        self.socials = dict(sorted(soc.items(), key=lambda kv: (rank(kv[0]), kv[0])))
        if not self.socials: raise Fail('no official links')
        hub = (d.get('hub') or '').strip()
        if not hub:
            hub = next((v['url'] for k, v in self.socials.items() if re.sub(r'\d+$', '', k) in HUBKEYS), '')
        self.hub_given = bool(hub)
        # videos ---------------------------------------------------------------------------------------
        mode = force_mode or (d.get('video_mode') or 'none').lower()
        ytv = [v for v in (yt.get('videos') or []) if v.get('playable', True) is not False and re.fullmatch(r'[\w-]{11}', str(v.get('id', '')))]
        ttv = []
        for v in tt.get('videos') or []:
            if v.get('playable', True) is False: continue
            vid = str(v.get('id') or (re.search(r'/video/(\d+)', v.get('url', '')) or [None, ''])[1])
            if re.fullmatch(r'\d{15,25}', vid): ttv.append({**v, 'id': vid})
        if mode == 'mixed': mode = 'youtube' if ytv else 'tiktok'
        if mode == 'youtube' and not ytv: mode = 'tiktok' if ttv else 'none'
        if mode == 'tiktok' and not ttv: mode = 'none'
        if mode not in BASES: mode = 'none'
        self.mode = mode
        self.channel_id = yt.get('channel_id', '') if mode == 'youtube' else ''
        self.tt_handle = (tt.get('handle') or self.socials.get('tiktok', {}).get('handle', '')).lstrip('@')
        self.videos = []
        if mode == 'youtube':
            for v in ytv[:12]:
                self.videos.append({'id': v['id'], 'title': re.sub(r'\s+', ' ', v.get('title') or 'YouTube video').strip(),
                                    'published': str(v.get('published') or '')[:10]})
        elif mode == 'tiktok':
            for v in ttv[:12]:
                pub = v.get('published') or ''
                if not re.fullmatch(r'20\d{2}-\d{2}-\d{2}', pub): pub = ''
                cap = v.get('title') or v.get('caption') or ''
                cap = re.sub(r'(?:\s*(?<!\w)[#@][\w.]+)+\s*$', '', cap)   # trailing hashtag/mention run
                cap = re.sub(r'(?<!\w)[#@]([\w.]+)', r'\1', cap)            # inline #word -> word
                cap = re.sub(r'\s+', ' ', cap).strip(' -·|')
                if len(cap) > 72: cap = cap[:72].rsplit(' ', 1)[0].rstrip(',.;:') + '…'
                self.videos.append({'id': v['id'], 'title': cap or f'TikTok video{" · " + nice_date(pub) if pub else ""}', 'published': pub,
                                    'source_url': v.get('url') or '', 'cover': v.get('cover') or ''})
        self.primary = {'youtube': 'youtube', 'tiktok': 'tiktok'}.get(mode)
        if self.primary and self.primary not in self.socials: raise Fail(f'{self.primary} link missing')
        nonpay = [k for k in self.socials if k not in PAYWALL]
        self.main_key = self.primary or (nonpay[0] if nonpay else next(iter(self.socials)))
        self.main_handle = self.socials[self.main_key]['handle'] if self.main_key not in HUBKEYS else self.slug
        self.hub = hub or self.socials[self.main_key]['url']
        self.hub_key = next((k for k, v in self.socials.items() if v['url'].rstrip('/') == self.hub.rstrip('/')), None)
        if not self.hub_key:  # hub given but not a link we kept -> add it
            k = plat_key('hub', self.hub)
            self.socials[k if k not in self.socials else 'website9'] = {'name': PNAME.get(k, 'Website'), 'handle': handle_of(k, self.hub), 'url': self.hub}
            self.hub_key = k if k in self.socials and self.socials[k]['url'] == self.hub else 'website9'
        self.head_key = next(iter(self.socials))  # header slot: OnlyFans first if present, else first official link
        # followers -------------------------------------------------------------------------------------
        self.followers = []
        for f in d.get('followers') or []:
            if f.get('count') in (None, '', 0): continue
            k = plat_key(f.get('platform', ''), f.get('url', ''))
            self.followers.append({'key': k, 'platform': PNAME.get(k, f.get('platform', 'Profile')), 'display': fmt_count(f['count']),
                                   'url': f.get('url') or self.socials.get(k, {}).get('url', self.hub), 'checked': str(f.get('checked') or TODAY)[:10]})
        self.checked = max([f['checked'] for f in self.followers] + [str(d.get('checked') or TODAY)[:10]])
        self.left_out = [{'id': str(x.get('id')), 'reason': x.get('reason', 'left out')} for x in d.get('left_out') or [] if x.get('id')]
        self.avatar_url = d.get('avatar_url') or ''
        self.avatar_source = d.get('avatar_source') or self.avatar_url
        if not self.avatar_url: raise Fail('avatar_url missing')
        self.origin = f'https://{self.slug}.amh-creator-previews.pages.dev'
        # pronoun forms
        P = {'he': ('his', 'he has'), 'she': ('her', 'she has'), 'they': ('their', 'they have'), 'name': (self.first + '\u2019s', self.first + ' has')}
        self.poss, self.subj_has = P[self.pron]

    def cap(self, s): return s[:1].upper() + s[1:]

    def blob(self):
        """Identity strings that legitimately belong to the NEW creator (never flagged as base leaks)."""
        parts = [self.name, self.slug, self.email or '', self.hub, self.channel_id, self.tt_handle]
        parts += [v['url'] + ' ' + v['handle'] for v in self.socials.values()]
        parts += [v['id'] + ' ' + v.get('title', '') for v in self.videos] + [x['id'] for x in self.left_out]
        return ' | '.join(parts).lower()


# ----------------------------------------------------------------------------------------------------- cloner
class Clone:
    def __init__(self, data_path, out, base_override=None, commit=True, browser=False):
        self.t0 = time.time(); self.times = {}; self._t = time.time()
        self.data = json.loads(Path(data_path).read_text(encoding='utf-8-sig'))
        self.c = Creator(self.data, base_override)
        bslug, bdir = BASES[self.c.mode]
        self.b = Base(self.c.mode, bslug, bdir)
        self.out = Path(out).resolve()
        self.site = self.out / 'sites' / self.c.slug
        self.commit, self.browser = commit, browser
        self.report = {'slug': self.c.slug, 'mode': self.c.mode, 'base': bslug, 'out': str(self.out)}

    def lap(self, name):
        now = time.time(); self.times[name] = round(now - self._t, 2); self._t = now
        print(f'  [{self.times[name]:6.2f}s] {name}', flush=True)

    # ---- 1. worktree + copy ------------------------------------------------------------------------
    def worktree(self):
        c = self.c
        if self.out.exists() and any(self.out.iterdir()): raise Fail(f'{self.out} exists and is not empty')
        self.out.parent.mkdir(parents=True, exist_ok=True)
        if self.out.exists(): self.out.rmdir()
        branch = os.environ.get('CREATOR_BRANCH_PREFIX', 'agent/') + f'{c.slug}-preview'  # Claude batch uses claude/
        if run(['git', '-C', str(REPO), 'rev-parse', '--verify', '--quiet', 'refs/heads/' + branch], REPO, check=False).returncode == 0:
            raise Fail(f'branch {branch} already exists')
        run(['git', '-C', str(REPO), 'worktree', 'add', '-q', '-b', branch, str(self.out), START_COMMIT], REPO)
        if self.site.exists(): raise Fail(f'sites/{c.slug} already exists at {START_COMMIT}')
        self.report['branch'] = branch
        b = self.b
        drop = {b.brand['avatar'], b.brand['wordmark'], 'assets/' + b.bubble, 'assets/social-preview.png', 'assets/favicon.svg',
                'assets/favicon.ico', 'assets/favicon-32.png', 'assets/favicon-96.png', 'assets/favicon-animated.gif', 'assets/apple-touch-icon.png',
                'assets/icon-192.png', 'assets/icon-512.png', 'assets/share-animated.gif', 'assets/share-animated.mp4'}
        def ignore(dirpath, names):
            rel = Path(dirpath).relative_to(b.dir).as_posix()
            out = set()
            for n in names:
                rp = (n if rel == '.' else rel + '/' + n)
                if n in SKIP_DIRS or rp in drop or rel == 'assets/covers' or (rel == 'img'): out.add(n)
            return out
        shutil.copytree(b.dir, self.site, ignore=ignore)
        for k in b.socials:  # base-only platform icons (e.g. social-wildskirts.svg) are not carried over
            if k not in self.c.socials and k not in ('youtube', 'tiktok', 'instagram', 'x', 'onlyfans', 'linktree', 'website'):
                (self.site / f'assets/social-{k}.svg').unlink(missing_ok=True)
        (self.site / 'img').mkdir(exist_ok=True); (self.site / 'assets/covers').mkdir(exist_ok=True)
        self.copy_icons()

    def copy_icons(self):
        pool = {}
        for p in sorted(CODE.glob('creator-*/sites/*/assets/social-*.svg')):
            pool.setdefault(p.name, p)
        for k in list(self.c.socials) + ['youtube', 'tiktok', 'website']:
            dst = self.site / f'assets/social-{k}.svg'
            if dst.exists(): continue
            src = pool.get(f'social-{k}.svg') or pool.get(f'social-{re.sub(r"[0-9]+$", "", k)}.svg') or pool.get('social-website.svg') or pool.get('social-linktree.svg')
            if not src: raise Fail('no icon for ' + k)
            shutil.copy2(src, dst)

    # ---- 2. media -------------------------------------------------------------------------------------
    def media(self):
        c, site = self.c, self.site
        jobs = {'avatar': self.avatar}
        if c.mode == 'youtube': jobs['covers'] = self.yt_covers
        if c.mode == 'tiktok': jobs['covers'] = self.tt_covers
        with ThreadPoolExecutor(4) as ex:
            futs = {k: ex.submit(f) for k, f in jobs.items()}
            for k, f in futs.items(): f.result()
        if c.mode != 'none' and not c.videos: raise Fail('no covers could be downloaded')

    def avatar(self):
        from PIL import Image
        raw = Path(self.data['avatar_local_file']).read_bytes() if self.data.get('avatar_local_file') else fetch(self.c.avatar_url)
        im = Image.open(io.BytesIO(raw)); im.load(); im = im.convert('RGB')
        crop = self.data.get('avatar_crop')
        if crop: x, y, w, h = crop; im = im.crop((x, y, x + w, y + h))
        else:
            s = min(im.size); l, t = (im.width - s) // 2, (im.height - s) // 2; im = im.crop((l, t, l + s, t + s))
        im = im.resize((900, 900), Image.Resampling.LANCZOS)
        self.avatar_rel = f'img/{self.c.slug}-avatar.jpg'
        im.save(self.site / self.avatar_rel, 'JPEG', quality=90, optimize=True)
        self.avatar_orig_sha = hashlib.sha256(raw).hexdigest()

    def cache_cover(self, vid):
        for prefix in ('creator-*','codex-c100-*'):
            for p in CODE.glob(f'{prefix}/sites/*/assets/covers/{vid}-*.jpg'):
                return p
        return None

    def yt_covers(self):
        site, kept = self.site, []
        def one(v):
            for q in ('maxresdefault', 'hqdefault'):
                url = f'https://i.ytimg.com/vi/{v["id"]}/{q}.jpg'
                try:
                    b = fetch(url)
                    if len(b) > 2000: return v, url, b
                except Exception: pass
            return v, None, None
        with ThreadPoolExecutor(8) as ex: res = list(ex.map(one, self.c.videos))
        self.cover_prov = []
        for v, url, b in res:
            if not b: print('    cover missing, dropped', v['id']); continue
            f = f'{v["id"]}-youtube.jpg'; (site / 'assets/covers' / f).write_bytes(b)
            v['image'] = f'/assets/covers/{f}'; kept.append(v)
            self.cover_prov.append({'video': v['id'], 'url': url, 'file': f, 'sha256': hashlib.sha256(b).hexdigest()})
        self.c.videos = kept

    def tt_covers(self):
        site, c, kept = self.site, self.c, []
        def one(v):
            vurl = f'https://www.tiktok.com/@{c.tt_handle}/video/{v["id"]}'
            if v.get('cover'):
                try:
                    b = fetch(v['cover'])
                    if len(b) > 2000:
                        return v, {'source': v['cover'].split('?')[0] + ' (public cover supplied by the matched official TikTok profile)', 'profile': f'https://www.tiktok.com/embed/@{c.tt_handle}', 'oembed': None, 'oembedReturnedHtml': None}, b
                except Exception: pass
            tries = [u for u in (v.get('source_url'), vurl) if u]
            for u in tries:
                oe = 'https://www.tiktok.com/oembed?url=' + urllib.parse.quote(u, safe=':/@')
                try:
                    j = json.loads(fetch(oe))
                    if j.get('thumbnail_url'):
                        b = fetch(j['thumbnail_url'])
                        if len(b) > 2000: return v, {'source': j['thumbnail_url'].split('?')[0] + ' (signed TikTok oEmbed thumbnail; query string omitted)', 'oembed': oe, 'oembedReturnedHtml': bool(j.get('html'))}, b
                except Exception: pass
            emb = f'https://www.tiktok.com/embed/v2/{v["id"]}'  # oEmbed often omits thumbnail_url when rate-limited
            try:
                m = re.search(r'<script[^>]*id="__FRONTITY_CONNECT_STATE__"[^>]*>(.*?)</script>', fetch(emb).decode('utf-8', 'replace'), re.S)
                vd = next(iter(json.loads(m.group(1))['source']['data'].values()))['videoData']
                for cu in vd['itemInfos'].get('covers') or []:
                    b = fetch(cu)
                    if len(b) > 2000: return v, {'source': cu.split('?')[0] + f' (public cover from the TikTok embed page {emb}; signed query string omitted)', 'oembed': None, 'oembedReturnedHtml': None}, b
            except Exception: pass
            p = self.cache_cover(v['id'])
            if p: return v, {'source': 'byte-identical public TikTok cover from the local AMH cover cache (TikTok oEmbed/embed unavailable now)', 'oembed': None, 'oembedReturnedHtml': None}, p.read_bytes()
            return v, None, None
        with ThreadPoolExecutor(6) as ex: res = list(ex.map(one, c.videos))
        self.cover_prov = []
        for v, meta, b in res:
            if not b: print('    cover missing, dropped', v['id']); continue
            f = f'{v["id"]}-public-cover.jpg'; (site / 'assets/covers' / f).write_bytes(b)
            v['image'] = f'/assets/covers/{f}'; kept.append(v)
            self.cover_prov.append({'video': v['id'], 'platform': 'tiktok', 'url': f'https://www.tiktok.com/@{c.tt_handle}/video/{v["id"]}', 'file': f, **meta,
                                    'sha256': hashlib.sha256(b).hexdigest()})
        c.videos = kept

    # ---- 3. catalog ----------------------------------------------------------------------------------
    def build_catalog(self):
        c, b = self.c, self.b
        V = c.videos; N = len(V)
        self.cats = {'all': 'All videos'}
        if N >= 4: self.cats.update({'recent': 'Recent', 'earlier': 'Earlier'})
        desc_t = (b.cat.get('long') or [{}])[0].get('desc', '')
        entries = []
        for i, v in enumerate(V):
            pub = v.get('published') or ''
            if c.mode == 'youtube':
                tag = 'YouTube' + (f' · {pub[:4]}' if pub else '')
                url = f'https://www.youtube.com/watch?v={v["id"]}'
            else:
                tag = 'TikTok' + (f' · {MON[int(pub[5:7]) - 1]} {pub[:4]}' if pub else '')
                url = f'https://www.tiktok.com/@{c.tt_handle}/video/{v["id"]}'
            e = {'id': v['id'], 'title': v['title'], 'tag': tag, 'category': ('recent' if i < math.ceil(N / 2) else 'earlier') if N >= 4 else 'recent',
                 'published': pub, 'image': v['image'], 'video': url, 'url': url, 'type': c.mode, 'desc': desc_t}
            keys = list((b.cat.get('long') or [{}])[0].keys()) or list(e)
            entries.append({k: e[k] for k in keys if k in e})
        self.long = entries
        cyc = lambda lst, start, n: [lst[(start + j) % N] for j in range(min(n, N))] if N else []
        sel = {'movies': entries[:7], 'profile': cyc(entries, 1, 6), 'long': entries, 'rail': entries[-min(4, N):] if N else [], 'shorts': []}
        cat = {}
        for k in b.cat:
            if k == 'creator': cat[k] = c.name
            elif k == 'channel': cat[k] = c.socials[c.main_key]['url']
            elif k == 'channelId': cat[k] = c.channel_id
            elif k == 'checked': cat[k] = TODAY
            elif k in sel: cat[k] = sel[k]
            elif k == 'excluded': cat[k] = c.left_out
            elif k == 'noEmbeddableVideo': cat[k] = True
            elif k == 'sources':
                cat[k] = [{'platform': v['name'] + (' (official hub)' if k2 == c.hub_key else ''), 'url': v['url'],
                           'result': 'Link only (media never scraped).'} for k2, v in c.socials.items()]
            elif k == 'verificationNote':
                if c.mode == 'youtube':
                    newest = max((e['published'] for e in entries if e['published']), default='')
                    cat[k] = (f'{N} playable public uploads from the official YouTube channel feed, each tested in the embed player '
                              f'(checked {c.checked}{", most recent upload " + newest if newest else ""}). Covers from the official YouTube thumbnail CDN.')
                elif c.mode == 'tiktok':
                    cat[k] = (f'{N} public TikTok videos from tiktok.com/@{c.tt_handle} (official profile), each tested in the TikTok player and '
                              f'oEmbed (checked {c.checked}). Titles are short plain-text summaries of each public caption.')
                else:
                    cat[k] = ("No embeddable public video was found from links on the official hub, so the videos route shows a "
                              "'Watch on' panel with official links instead of players. No covers were made up.")
            else: cat[k] = b.cat[k] if not isinstance(b.cat[k], list) else []
        self.cat = cat
        self.ids_new = [e['id'] for e in entries]

    # ---- 4. maps for the generic text pass -----------------------------------------------------------
    def build_maps(self):
        c, b = self.c, self.b
        self.idmap = {}
        if self.ids_new:
            for i, old in enumerate(b.long_ids): self.idmap[old] = self.ids_new[i % len(self.ids_new)]
            for old in b.all_ids:
                self.idmap.setdefault(old, self.ids_new[0])
        if b.channel_id:
            self.idmap[b.channel_id] = c.channel_id or ''
            self.idmap['UU' + b.channel_id[2:]] = ('UU' + c.channel_id[2:]) if c.channel_id else ''
        urls = {}
        def variants(u, target):
            for a, t in ((u, target), (u.rstrip('/'), target.rstrip('/')), (u.rstrip('/') + '/', target.rstrip('/') + '/')):
                urls.setdefault(a, t)
                urls.setdefault(a.replace('https://', 'http://'), t)
                if '://www.' in a: urls.setdefault(a.replace('://www.', '://'), t)
                elif '://' in a: urls.setdefault(a.replace('://', '://www.', 1), t)
            urls['www.' + disp(u)] = disp(target)
            urls[disp(u)] = disp(target)
        for k, v in b.socials.items():
            if k in c.socials: tgt = c.socials[k]['url']
            elif k == next(iter(b.socials)): tgt = c.socials[c.head_key]['url']   # base header slot (OnlyFans) -> new header slot
            elif k in HUBKEYS: tgt = c.hub
            else: tgt = c.hub
            variants(v['url'], tgt)
        variants(b.hub, c.hub)
        variants(b.brand['origin'], c.origin)
        if b.mode == 'tiktok':  # base tiktok profile prefix also covers /video/<id> links
            pass
        for e in b.emails: urls['mailto:' + e] = ('mailto:' + c.email) if c.email else c.hub; urls[e] = c.email or disp(c.hub)
        self.urlmap = urls
        # files / slug
        self.filemap = {b.brand['avatar']: self.avatar_rel, b.brand['wordmark']: f'assets/{c.slug}-wordmark.webp'}
        if b.bubble: self.filemap[b.bubble] = f'{c.first_slug}-movie-bubble.webp'
        self.slugmap = {b.slug: c.slug}
        # handles
        hm = {}
        for k, v in b.socials.items():
            h = v['handle'].lstrip('@')
            if h in hm or k in HUBKEYS and '.' in h: continue
            cands = [k2 for k2, v2 in b.socials.items() if v2['handle'].lstrip('@') == h]
            tk = next((k2 for k2 in cands if k2 in c.socials and k2 not in HUBKEYS), None)
            hm[h] = c.socials[tk]['handle'] if tk else c.main_handle
        bh = b.brand.get('handle', '').lstrip('@')
        if bh and bh not in hm: hm[bh] = c.main_handle
        self.handlemap = {**{('@' + k): ('@' + v) for k, v in hm.items()}, **hm}
        # names
        nm = {b.name.upper(): c.name.upper(), b.name: c.name}
        if b.first != b.name:
            nm.update({b.first + '\u2019s': c.first + '\u2019s', b.first + "'s": c.first + '\u2019s', b.first: c.first})
        else:
            nm.update({b.name + '\u2019s': c.name + '\u2019s', b.name + "'s": c.name + '\u2019s'})
        self.namemap = nm

    def swap(self, s):
        """Generic identity swap used for every text file after the structural rewrites."""
        c, b = self.c, self.b
        s, _ = multi_replace(s, self.idmap, r'(?<![\w-])', r'(?![\w-])')
        s, _ = multi_replace(s, self.urlmap, r'', r'')
        s, _ = multi_replace(s, self.filemap)
        s, _ = multi_replace(s, self.slugmap, r'(?<![\w])', r'(?![\w])')
        s, _ = multi_replace(s, self.handlemap, r'(?<![\w.@/-])', r'(?![\w-])', re.I)
        s, _ = multi_replace(s, self.namemap, r'(?<![\w])', r'(?![\w])')
        if b.pron != c.pron:
            bp, bs = {'he': ('his', 'he'), 'she': ('her', 'she')}[b.pron]
            s = re.sub(rf'\b{bs} has\b', c.subj_has, s)
            s = re.sub(rf'\b{bs.capitalize()} has\b', c.cap(c.subj_has), s)
            s = re.sub(rf'\b{bp}\b', c.poss, s)
            s = re.sub(rf'\b{bp.capitalize()}\b', c.cap(c.poss), s)
        return s

    # ---- 5. structural rewrites ----------------------------------------------------------------------
    def gen_blocks(self):
        c = self.c; E = H.escape
        S = c.socials
        nonpay = [k for k in S if k not in PAYWALL and k != c.hub_key]
        self.watch_keys = (nonpay[:2])
        others = [k for k in nonpay if k != c.primary] or nonpay  # collab extras / audience: not the video platform itself
        g = {}
        hk = c.head_key
        g['header'] = (f'<a class="fanfix-nav" href="{E(S[hk]["url"])}" target="_blank" rel="noopener" aria-label="{E(S[hk]["name"])} — {E(c.name)}">'
                       f'<img src="/assets/social-{hk}.svg" alt=""><span>{E(S[hk]["name"])}</span></a>')
        if c.email:
            g['menu_collab'] = f'<p data-k="menu.collab">Business contact (public): <a href="mailto:{E(c.email)}">{E(c.email)}</a></p>'
            g['c_lede'] = f'<p class="lede" data-k="c.lede">For collaboration inquiries, {E(c.name)}’s public business contact is <a href="mailto:{E(c.email)}">{E(c.email)}</a>.</p>'
            extra = ''.join(f'<a class="btn ghost" href="{E(S[k]["url"])}" target="_blank" rel="noopener">{E(S[k]["name"])} ↗</a>' for k in others[:1])
            g['panel'] = (f'<div class="panel reveal collab-links" id="collabPanel"><h3>Get in touch</h3><p class="account-note">Public business email, as listed on '
                          f'{E(c.poss)} official profile.</p><a class="btn" href="mailto:{E(c.email)}">Email ↗</a><a class="btn ghost" href="{E(c.hub)}" target="_blank" '
                          f'rel="noopener">Official links ↗</a>{extra}<p class="account-note">This preview sends and stores nothing.</p></div>')
        else:
            g['menu_collab'] = f'<p data-k="menu.collab">No public business email is listed. Reach {E(c.first)} through {E(c.poss)} official links.</p>'
            g['c_lede'] = f'<p class="lede" data-k="c.lede">No public business email is listed for {E(c.name)}. For collaboration inquiries, use {E(c.poss)} official links.</p>'
            extra = ''.join(f'<a class="btn ghost" href="{E(S[k]["url"])}" target="_blank" rel="noopener">{E(S[k]["name"])} ↗</a>' for k in others[:2])
            g['panel'] = (f'<div class="panel reveal collab-links" id="collabPanel"><h3>Get in touch</h3><p class="account-note">No public business email is listed. '
                          f'These are {E(c.name)}’s official public links.</p><a class="btn" href="{E(c.hub)}" target="_blank" rel="noopener">Official links '
                          f'({E(S[c.hub_key]["name"])}) ↗</a>{extra}<p class="account-note">This preview sends and stores nothing.</p></div>')
        plat = PNAME.get(c.primary or '', '')
        aud = ' &amp; '.join(E(S[k]['name']) for k in others[:2]) or 'Official links'
        pts = [f'{plat} videos' if plat else 'Creator', f'{aud} audience', f'Official links via {E(S[c.hub_key]["name"])}']
        g['points'] = '<div class="points">' + ''.join(f'<div><i>0{i + 1}</i><span><b>{p}</b></span></div>' for i, p in enumerate(pts)) + '</div>'
        g['eyebrow'] = f'data-k="p.eyebrow">{plat} · videos · links<' if plat else 'data-k="p.eyebrow">Creator · official links<'
        g['footer'] = (f'<nav class="footer-socials" aria-label="{E(c.name)}’s social profiles">' + ''.join(
            f'<a class="social-{k}" href="{E(v["url"])}" target="_blank" rel="noopener" aria-label="{E(c.name)} on {E(v["name"])}"><img src="/assets/social-{k}.svg" '
            f'alt="" width="25" height="25"><span>{E(v["name"])}</span></a>' for k, v in S.items()) + '</nav>')
        g['linklist'] = ('<div class="links" id="linkList" data-listbox="links">' + ''.join(
            f'<a href="{E(v["url"])}">{E(c.name)} on {E(v["name"])}</a>' for k, v in S.items() if k != c.hub_key) + '</div>')
        if c.followers:
            cells = ''.join(f'<a href="{E(f["url"])}" target="_blank" rel="noopener"><b>{E(f["display"])}</b><span>{E(f["platform"])} '
                            f'{"subscribers" if f["key"] == "youtube" else "followers"}</span></a>' for f in c.followers)
            where = ' and '.join(disp(f['url']) for f in c.followers)
            what = (f'Public {c.followers[0]["platform"]} {"subscriber" if c.followers[0]["key"] == "youtube" else "follower"} count' if len(c.followers) == 1
                    else 'Public follower counts')
            g['stats'] = (f'<div class="stats creator-stats">{cells}</div><details class="followers-note"><summary>{"Count" if len(c.followers) == 1 else "Counts"} · '
                          f'{nice_date(c.checked)}</summary>{what} shown on {E(where)}, checked {nice_date(c.checked)}. Other platform counts are not shown.</details>')
        else:
            g['stats'] = ''
        cards = [(k, f'Watch on {S[k]["name"]}', '@' + S[k]['handle'] if k not in HUBKEYS else disp(S[k]['url'])) for k in self.watch_keys]
        cards.append((c.hub_key, 'All official links', disp(c.hub)))
        self.watch_cards = cards
        g['watchgrid'] = '<div class="watch-on-grid">' + ''.join(
            f'<a class="watch-on-card" href="{E(S[k]["url"])}" target="_blank" rel="noopener"><img src="/assets/social-{k}.svg" alt="" width="40" height="40">'
            f'<span><b>{E(t)}</b><small>{E(h)}</small></span><em>↗</em></a>' for k, t, h in cards) + '</div>'
        self.g = g

    def patch_index(self):
        c, b, g = self.c, self.b, self.g
        p = self.site / 'index.html'; s = rd(p)
        S = c.socials
        s = sub1(s, r'<a class="fanfix-nav" href="[^"]*"[^>]*>.*?</a>', g['header'], 'header slot')
        s = sub1(s, r'<p data-k="menu\.collab">.*?</p>', g['menu_collab'], 'menu collab')
        s = sub1(s, r'<p class="lede" data-k="c\.lede">.*?</p>', g['c_lede'], 'collab lede')
        s = sub1(s, r'<div class="panel reveal collab-links" id="collabPanel">.*?</div>', g['panel'], 'collab panel')
        s = sub1(s, r'<div class="points">(?:<div><i>\d+</i><span><b>.*?</b></span></div>)+</div>', g['points'], 'collab points')
        s = sub1(s, r'data-k="p\.eyebrow">[^<]*<', g['eyebrow'], 'profile eyebrow')
        s = sub1(s, r'<p class="profile-kind">[^<]*</p>', '<p class="profile-kind">Creator</p>', 'profile kind')
        s = sub1(s, r'<nav class="footer-socials" aria-label="[^"]*">.*?</nav>', g['footer'], 'footer socials')
        s = sub1(s, r'<div class="links" id="linkList" data-listbox="links">.*?</div>', g['linklist'], 'noscript links')
        s = sub1(s, r'<div class="stats creator-stats">.*?</details>', g['stats'], 'stats', optional=True)
        s = sub1(s, r'(<a class="avatar" id="avatarBox" href=")[^"]*(")', lambda m: m.group(1) + H.escape(S[c.main_key]['url'] if c.mode != 'none' else c.hub) + m.group(2), 'avatar href')
        s = sub1(s, r'(<div id="av"><img src="[^"]*" alt=")[^"]*(" width=")\d+(" height=")\d+', lambda m: m.group(1) + H.escape(c.name) + ' — public profile photo' + m.group(2) + '900' + m.group(3) + '900', 'avatar alt')
        s = sub1(s, r'(i\.alt=")[^"]*(";i\.src=C\.avatar)', lambda m: m.group(1) + c.name + ' — public profile photo' + m.group(2), 'avatar js alt')
        s = sub1(s, r"(av\.textContent=')[^'](')", lambda m: m.group(1) + jsq(c.name[:1].upper()) + m.group(2), 'avatar initial')
        s = sub1(s, r'(<a class="avatar-caption" href="/videos/">)[^<]*(</a>)', lambda m: m.group(1) + (f'Watch {H.escape(c.name)}’s videos ↗' if c.mode != 'none' else f'Where to watch {H.escape(c.first)} ↗') + m.group(2), 'avatar caption')
        has_ig = 'instagram' in S
        if 'data-pane="p-ig"' in s:
            if not has_ig:
                s = sub1(s, r'\s*<button class="tab" data-pane="p-ig">.*?</button>', '', 'ig tab')
                s = sub1(s, r'\s*<div class="pane" id="p-ig">.*?</div>\s*<div class="cta-row">.*?</div>\s*</div>', '', 'ig pane')
                s = sub1(s, r'<a href="#watch" data-tab="p-ig">Instagram</a>', '', 'menu ig tab')
            lede_plat = PNAME[c.primary] + (' videos' if c.mode == 'youtube' else '')
            s = sub1(s, r'data-k="w\.lede">[^<]*<', f'data-k="w.lede">{lede_plat}{" and Instagram" if has_ig else " and official links"} — all in one place.<', 'watch lede', optional=True)
        dock_key = 'instagram' if has_ig else ([k for k in S if k not in PAYWALL] or [c.main_key])[0]
        s = sub1(s, r'<a data-soc="instagram" target="_blank" rel="noopener" data-track="dock-ig">Follow</a>',
                 f'<a data-soc="{dock_key}" target="_blank" rel="noopener" data-track="dock-{dock_key}">Follow</a>', 'dock follow', optional=True)
        if 'data-watch-on' in s:
            s = sub1(s, r'<div class="watch-on-grid">.*?</div>', g['watchgrid'], 'watch-on grid')
            msub = ''.join(f'<a href="{H.escape(S[k]["url"])}" target="_blank" rel="noopener">{H.escape(S[k]["name"])} ↗</a>' for k in self.watch_keys) or \
                f'<a href="{H.escape(c.hub)}" target="_blank" rel="noopener">Official links ↗</a>'
            s = sub1(s, r'<div class="msub"><a href="https?://[^"]*" target="_blank".*?</div>', f'<div class="msub">{msub}</div>', 'menu watch-on links')
        # DEFAULT + SOCIALS + ICLS + icon list + nav socials
        m = re.search(r'const DEFAULT = (\{.*?\});\n', s, re.S)
        if not m: raise Fail('DEFAULT not found')
        D = json.loads(m.group(1))
        D['brandImage'] = f'/assets/{c.slug}-wordmark.webp'; D['avatar'] = '/' + self.avatar_rel
        socmap = {k: (disp(v['url']) if k in ('website',) or k.startswith('website') else v['handle']) for k, v in S.items()}
        if 'ytUploads' in D.get('socials', {}) and c.channel_id: socmap['ytUploads'] = 'UU' + c.channel_id[2:]
        D['socials'] = socmap
        covers = [e['image'] for e in self.long]
        D['photos'] = ['/' + self.avatar_rel] + ([covers[i % len(covers)] for i in range(len(D.get('photos', [])) - 1)] if covers else [])
        links = []
        for k, v in S.items():
            sdisp = ('@' + v['handle']) if k not in HUBKEYS and not k.startswith('website') and k != 'youtube' else disp(v['url'])
            links.append({'t': v['name'], 's': sdisp, 'icon': k, 'go': 'Watch' if k == c.primary else 'Open', 'url': v['url'],
                          'feat': k == (c.primary or (self.watch_keys[0] if self.watch_keys else None))})
        tail = [l for l in D.get('links', []) if l.get('icon') in ('shop', 'email')]
        for l in tail:
            if l['icon'] == 'email': l['s'] = 'Business email' if c.email else 'Via official links'
        D['links'] = links + tail
        f = D.get('featured', {})
        ids = self.ids_new or ['']
        for k in list(f):
            if k == 'introYt': f[k] = ids[0] if c.mode == 'youtube' else ''
            elif k == 'yt': f[k] = ids[1 % len(ids)] if c.mode == 'youtube' else ''
            elif k == 'tt': f[k] = ids[1 % len(ids)] if c.mode == 'tiktok' else ''
            elif k == 'watch': f[k] = ids[0] if c.mode == 'tiktok' else ''
        D['featured'] = f
        s = s[:m.start(1)] + json.dumps(D, ensure_ascii=False) + s[m.end(1):]
        socjs = '{' + ','.join(f'{json.dumps(k)}: {{"name": {json.dumps(v["name"], ensure_ascii=False)}, "handle": {json.dumps(socmap[k], ensure_ascii=False)}, "url": {json.dumps(v["url"])}}}' for k, v in S.items()) + '}'
        s = sub1(s, r'const SOCIALS=\{.*?\};\n', 'const SOCIALS=' + socjs + ';\n', 'SOCIALS')
        icls = {'tiktok': 'tt', 'youtube': 'yt', 'instagram': 'ig', 'email': 'em', 'x': 'tt', 'shop': 'rose', 'onlyfans': 'fanfix', 'fansly': 'fanfix', 'link': 'rose', 'star': 'rose'}
        ic = {k: icls.get(k, 'rose') for k in S}
        ic.update({k: icls[k] for k in ('email', 'shop', 'link', 'star')})
        s = sub1(s, r'const ICLS=\{[^}]*\};', 'const ICLS={' + ','.join(f'{k if re.fullmatch(r"[a-z]\w*", k) else json.dumps(k)}:"{v}"' for k, v in ic.items()) + '};', 'ICLS')
        imgkeys = [k for k in S if k != 'onlyfans' and f'id="i-{k}"' not in s]
        s = sub1(s, r"\[(?:'[\w-]+',?)+\]\.includes\(k\)", '[' + ','.join(f"'{k}'" for k in imgkeys) + '].includes(k)', 'platformIcon list')
        nav3 = [k for k in S if k not in PAYWALL][:3] or list(S)[:3]
        s = sub1(s, r"\$\('#navSoc'\)\.innerHTML=\[[^\]]*\]", "$('#navSoc').innerHTML=[" + ','.join(f"'{k}'" for k in nav3) + ']', 'nav socials')
        # Instagram fallback text inside renderReels uses the IG handle; generic pass maps it.
        s = sub1(s, r"(text:')[^']*(',url:location)", lambda m: m.group(1) + jsq(f'Watch {c.name}’s {PNAME[c.primary]} videos' if c.primary else f'{c.name} — official links') + m.group(2), 'share text', optional=True)
        wr(p, s)

    def patch_build(self):
        c, b = self.c, self.b
        p = self.site / 'tools/build.py'; s = rd(p)
        E = H.escape
        if re.search(r"^labels=\{", s, re.M):
            s = sub1(s, r"^labels=\{.*?\}$", 'labels=' + repr(self.cats), 'video labels', flags=re.M)
            newest = max((e['published'] for e in self.long if e['published']), default='')
            nd = f' (latest upload {MONTH[int(newest[5:7]) - 1]} {newest[:4]})' if newest else ''
            if c.mode == 'youtube':
                lede = f'Public YouTube videos from {E(c.name)}’s channel{nd}. Choose a cover to watch with native playback controls.'
            else:
                lede = f'Recent public TikTok videos from {E(c.name)} (@{E(c.tt_handle)}){nd}. Choose a cover to watch with TikTok’s native player.'
            s = sub1(s, r"(^ page\(label,.*?<p class=\"route-lede\">).*?(</p>)", lambda m: m.group(1) + lede.replace('\\', '\\\\').replace("'", "\\'") + m.group(2), 'videos lede', flags=re.M)
        if "page('Where to watch'" in s:
            lst = repr([(k, t, h) for k, t, h in self.watch_cards])
            s = sub1(s, r"for k,t,h in \[.*?\]\)", f"for k,t,h in {lst})", 'where-to-watch list')
        socl = f'These are {E(c.name)}’s public profiles, as listed on {E(c.poss)} official links; this page is a preview concept, not {E(c.poss)} official site.'
        s = sub1(s, r"(^page\('Socials & links'.*?<p class=\"route-lede\">).*?(</p>)", lambda m: m.group(1) + socl.replace("'", "\\'") + m.group(2), 'socials lede', flags=re.M)
        biz = (f'Business (public): <a href="mailto:{E(c.email)}">{E(c.email)}</a> · Official links: <a href="\'+HUB+\'" target="_blank" rel="noopener">{E(disp(c.hub))}</a>'
               if c.email else f'Business: no public email is listed. Use <a href="\'+HUB+\'" target="_blank" rel="noopener">{E(c.poss)} official links</a>.')
        s = sub1(s, r"(^page\('Socials & links'.*</div>)(<p[^>]*style=\"margin-top:30px\">)(.*?)(</p></div>','/socials/'\))",
                 lambda m: m.group(1) + m.group(2) + biz + m.group(4), 'socials business line', flags=re.M)
        wr(p, s)

    def patch_checks(self):
        c, b = self.c, self.b
        # ---- check.mjs
        p = self.site / 'tools/check.mjs'; s = rd(p)
        cat = self.cat
        for k in ('long', 'movies', 'profile', 'rail'):
            s = sub1(s, rf'assert\.equal\(cat\.{k}\.length,\d+\)', f'assert.equal(cat.{k}.length,{len(cat.get(k, []))})', 'check count ' + k, optional=True)
        if c.mode == 'tiktok':
            s = sub1(s, r'tiktok\\\.com\\/@[^\\/]+\\/video', lambda m: 'tiktok\\.com\\/@' + re.escape(c.tt_handle) + '\\/video', 'tiktok url regex', optional=True)
        keys = list(c.socials)
        absent = re.search(r'assert\((!socials\.\w+(?:&&!socials\.\w+)*)\);', s)
        absent_keys = re.findall(r'!socials\.(\w+)', absent.group(1)) if absent else []
        absent_keys = [k for k in dict.fromkeys(absent_keys + [k for k in b.socials]) if k not in c.socials]
        line = (f"const socials=JSON.parse(fs.readFileSync('assets/socials.json'));assert.deepEqual(Object.keys(socials),{json.dumps(keys)});"
                f"assert.equal(socials[{json.dumps(keys[0])}].url,{json.dumps(c.socials[keys[0]]['url'])});"
                f"assert.equal(socials[{json.dumps(c.main_key)}].url,{json.dumps(c.socials[c.main_key]['url'])});"
                + (f"assert({'&&'.join('!socials[' + json.dumps(k) + ']' for k in absent_keys)});" if absent_keys else ''))
        s = sub1(s, r"const socials=JSON\.parse\(fs\.readFileSync\('assets/socials\.json'\)\);[^\n]*?(?=\r?\n)", line, 'check socials line')
        # base identity joins the "Old identity" list (minus anything that is legitimately the new creator's)
        blob = c.blob()
        toks = [b.name, b.slug] + [v['handle'] for v in b.socials.values() if len(v['handle']) >= 5] + [i for i in b.all_ids if i not in self.ids_new]
        toks = [t for t in dict.fromkeys(toks) if t and t.lower() not in blob]
        def add_old(m):
            body = m.group(1)
            alts = [a for a in body.split('|') if not (len(a) >= 3 and re.escape(a).lower() in blob)]
            self.old_alts = [re.escape(t).replace('/', r'\/') for t in toks]
            return '/' + '|'.join(alts + ['__CLONE_OLD_IDENTITY__']) + '/i.test(s)'
        s = sub1(s, r'/((?:[^/\n]|\\/)+)/i\.test\(s\)', add_old, 'old identity regex')
        wr(p, s)
        # ---- browser-check.py
        p = self.site / 'tools/browser-check.py'; s = rd(p)
        mv, pr, rl = cat.get('movies', []), cat.get('profile', []), cat.get('rail', [])
        nlinks = len(c.socials) + 2
        def counts(m):
            t = m.group(0)
            t = re.sub(r"(\.movie-pick'\)\.count\(\),)\d+", rf"\g<1>{len(mv)}", t)
            t = re.sub(r"(\.short-card'\)\.count\(\),)\d+", rf"\g<1>{len(rl)}", t)
            t = re.sub(r"(#linkList a'\)\.count\(\),)\d+", rf"\g<1>{nlinks}", t)
            t = re.sub(r"(#profileVideosLeft \.profile-video'\)\.count\(\),)\d+", rf"\g<1>{min(3, len(pr))}", t)
            t = re.sub(r"(#profileVideosRight \.profile-video'\)\.count\(\),)\d+", rf"\g<1>{max(0, len(pr) - 3)}", t)
            t = re.sub(r"(watch-on-card'\)\.count\(\),)\d+", rf"\g<1>{len(self.watch_cards)}", t)
            return t
        s = sub1(s, r"check\(kind\+' rendered counts'.*?(?=\r?\n)", counts, 'browser counts')
        if mv:
            s = sub1(s, r"for i in range\(\d+\):(\r?\n\s+check\(kind\+' carousel)", lambda m: f"for i in range({len(mv)}):" + m.group(1), 'carousel loop')
            s = sub1(s, r"(eq\(p\.locator\('#movieTitle'\)\.inner_text\(\),)\[.*?\](\[i\]\))", lambda m: m.group(1) + repr([e['title'] for e in mv]) + m.group(2), 'carousel titles')
        if rl:
            s = sub1(s, r"for i in range\(\d+\):(\r?\n\s+check\(kind\+' rail)", lambda m: f"for i in range({len(rl)}):" + m.group(1), 'rail loop')
        s = sub1(s, r"expected=\{.*?\}(?=\r?\n)", 'expected=' + repr({k: v['url'] for k, v in c.socials.items()}), 'expected socials')
        if 'instagram' not in c.socials:
            s = sub1(s, r"[ \t]*p\.locator\('\[data-pane=\"p-ig\"\]'\)\.click\(\);check\(kind\+' Instagram tab exact fallback'.*?\r?\n", '', 'ig check', optional=True)
        s = re.sub(r"(\.social-link'\)\.count\(\),)\d+", rf"\g<1>{len(c.socials)}", s)
        if re.search(r"^\s*paths=\[", s, re.M):
            vp = ['/videos/'] + [f'/videos/{k}/' for k in self.cats if k != 'all'] if c.mode != 'none' else ['/videos/']
            s = sub1(s, r"paths=\[[^\]]*'/videos/[^\]]*\]", 'paths=' + repr(vp + ['/socials/', '/shop/', '/privacy/', '/terms/', '/order/', '/thanks/', '/404.html']), 'route paths')
        if 'wexp=' in s:
            s = sub1(s, r"wexp=\[.*?\](?=\r?\n)", 'wexp=' + repr([c.socials[k]['url'] for k, _, _ in self.watch_cards]), 'watch-on expected')
            s = sub1(s, r"(stats b'\)\.all_inner_texts\(\),)\[.*?\]\)", lambda m: m.group(1) + repr([f['display'] for f in c.followers]) + ')', 'follower cells', optional=True)
            s = re.sub(r"(watch-on-card'\)\.count\(\),)\d+", rf"\g<1>{len(self.watch_cards)}", s)
            s = sub1(s, r"(avatar links to official hub',lambda:eq\(p\.locator\('#avatarBox'\)\.get_attribute\('href'\),)'[^']*'", lambda m: m.group(1) + repr(c.hub), 'avatar hub check', optional=True)
            if 'tiktok' in c.socials or 'youtube' in c.socials:
                s = sub1(s, r",eq\(p\.locator\('a\[href\*=\"tiktok\.com\"\]'\)\.count\(\),0\),eq\(p\.locator\('a\[href\*=\"youtube\.com\"\]'\)\.count\(\),0\)", '', 'no tt/yt surfaces', optional=True)
        wr(p, s)
        # ---- auxiliary UI checks (not part of npm test): keep their counts in step with the new catalog
        nav3 = [k for k in c.socials if k not in PAYWALL][:3] or list(c.socials)[:3]
        aux = [(r"(\.profile-screen img'\)\.count\(\)==)\d+", len(pr)), (r"(\.stats b'\)\.count\(\)==)\d+", len(c.followers)),
               (r"(\.fanfix-nav'\)\.count\(\)\+p\.locator\('#navSoc a'\)\.count\(\)==)\d+", 1 + len(nav3)),
               (r"(\[data-video\]'\)\.count\(\)==)\d+", len(cat.get('long', []))), (r"(\.short-placeholder'\)\.count\(\)==)\d+", len(rl))]
        for f in ('upper-ui-check.py', 'release-ui-check.py'):
            p = self.site / 'tools' / f
            if not p.exists(): continue
            s = rd(p)
            for rx, n in aux: s = re.sub(rx, lambda m, n=n: m.group(1) + str(n), s)
            if c.followers: s = re.sub(r"(\.stats b'\)\.inner_text\(\)==)'[^']*'", lambda m: m.group(1) + repr(c.followers[0]['display']), s)
            s = re.sub(r"(\.stats b'\)\.all_inner_texts\(\)==)\[[^\]]*\]", lambda m: m.group(1) + repr([f['display'] for f in c.followers]), s)
            wr(p, s)

    def patch_js(self):
        c = self.c
        p = self.site / 'assets/brand.js'
        if p.exists():
            s = rd(p); hk = c.head_key; v = c.socials[hk]
            s = sub1(s, r'<a href="[^"]*" target="_blank" rel="noopener"><img class="fanfix-icon" src="/assets/social-onlyfans\.svg" alt="">OnlyFans</a>',
                     f'<a href="{H.escape(v["url"])}" target="_blank" rel="noopener"><img class="fanfix-icon" src="/assets/social-{hk}.svg" alt="">{H.escape(v["name"])}</a>', 'phone dock slot', optional=True)
            wr(p, s)
        p = self.site / 'assets/intro-youtube.js'
        if p.exists() and self.long:
            s = rd(p)
            t = f"{c.name} — {self.long[0]['title']}" + (' (TikTok)' if c.mode == 'tiktok' else '')
            s = sub1(s, r"(player\.title=')(?:[^'\\]|\\.)*(')", lambda m: m.group(1) + jsq(t) + m.group(2), 'intro title', optional=True)
            wr(p, s)

    # ---- 6. generic pass on every text file ------------------------------------------------------------
    def text_pass(self):
        n = 0
        for f in self.site.rglob('*'):
            if not f.is_file() or f.suffix.lower() not in TEXT_EXT or 'fonts' in f.parts: continue
            if f.name in ('media-catalog.json', 'media-catalog.js', 'socials.json', 'followers.json', 'brand-config.json') or 'PROVENANCE' in f.name: continue
            s = rd(f); t = self.swap(s)
            if t != s: wr(f, t); n += 1
        self.report['text_files_changed'] = n
        p = self.site / 'tools/check.mjs'  # base identity tokens are added only after the swap pass
        wr(p, rd(p).replace('__CLONE_OLD_IDENTITY__', '|'.join(self.old_alts) or 'a^'))
        p = self.site / 'tools/enrich-build.py'
        if p.exists():
            wr(p, rd(p).replace("socials['linktree']['url']", "brand['hub']"))

    # ---- 7. data files + docs ------------------------------------------------------------------------
    def write_data(self):
        c, b, site = self.c, self.b, self.site
        wr(site / 'assets/media-catalog.json', jdump(self.cat))
        wr(site / 'assets/media-catalog.js', 'window.CREATOR_CATALOG=' + json.dumps(self.cat, ensure_ascii=False, separators=(',', ':')) + ';\n')
        socmap = {k: {'name': v['name'], 'handle': (disp(v['url']) if k.startswith('website') else v['handle']), 'url': v['url']} for k, v in c.socials.items()}
        wr(site / 'assets/socials.json', jdump(socmap))
        quinn_style = any(' ' in p.get('label', '') for p in json.loads(rd(b.dir / 'assets/followers.json')).get('profiles', []))
        prof = [{'platform': f['platform'], 'display': f['display'],
                 'label': (f'{f["platform"]} ' if quinn_style else '') + ('subscribers' if f['key'] == 'youtube' else 'followers'),
                 'url': f['url'], 'source': f'{f["url"]} (public profile page, read {f["checked"]})'} for f in c.followers]
        note = ('Only counts read on public profile pages are shown. No other counts are shown.' if prof else 'No public follower counts are shown.')
        wr(site / 'assets/followers.json', jdump({'checkedAt': c.checked, 'profiles': prof, 'note': note}))
        brand = {'name': c.name, 'handle': '@' + c.main_handle, 'origin': c.origin, 'avatar': self.avatar_rel,
                 'wordmark': f'assets/{c.slug}-wordmark.webp', 'hub': c.hub}
        if 'hero_photo_top' in self.data:
            top=int(self.data['hero_photo_top']);assert 0<=top<=200;brand['hero_photo_top']=top
        if self.data.get('hero_photo_fit') in ('contain','cover'):brand['hero_photo_fit']=self.data['hero_photo_fit']
        if self.data.get('avatar_kind')=='concept_wordmark':brand['avatar_kind']='concept_wordmark'
        if self.data.get('official_destination'):
            dest=self.data['official_destination'];assert str(dest['url']).startswith('https://')
            brand['official_destination']={'url':str(dest['url']),'label':str(dest['label'])}
        wr(site / 'brand-config.json', json.dumps(brand, indent=2, ensure_ascii=False))
        for fn in ('package.json',):
            j = json.loads(rd(site / fn)); j['name'] = f'{c.slug}-preview'; wr(site / fn, json.dumps(j, indent=2) + '\n')
        for fn in ('wrangler.jsonc', 'wrangler.jsonc.example'):
            if (site / fn).exists(): wr(site / fn, re.sub(r'("name":\s*")[^"]*(")', rf'\g<1>{c.slug}-preview\2', rd(site / fn), count=1))
        # covers provenance (file name kept from the template, as the bases do)
        cp = site / 'assets/covers/YOUTUBE-PROVENANCE.json'
        if c.mode == 'youtube':
            wr(cp, jdump({'checkedAt': TODAY, 'source': 'Official YouTube thumbnail CDN, unmodified bytes', 'channel': c.socials['youtube']['url'], 'covers': self.cover_prov}))
        elif c.mode == 'tiktok':
            wr(cp, jdump({'note': 'Filename kept from the template. All covers are public TikTok covers (oEmbed thumbnail_url).', 'checkedAt': TODAY,
                          'profile': c.socials['tiktok']['url'], 'covers': self.cover_prov}))
        else:
            wr(cp, jdump({'note': f'No covers: no embeddable public video was found for {c.name}. This file is kept so tools can verify there are zero covers.',
                          'checkedAt': TODAY, 'covers': []}))
        self.write_docs()

    def write_docs(self):
        c, site = self.c, self.site
        plat = {'youtube': 'YouTube', 'tiktok': 'TikTok'}.get(c.mode)
        links = ', '.join(v['name'] for v in c.socials.values())
        fl = '; '.join(f'{f["platform"]} {f["display"]} ({disp(f["url"])}, checked {f["checked"]})' for f in c.followers) or 'none shown'
        vids = (f'- {len(self.long)} public {plat} videos (native {plat} player + "Open on {plat}" link), covers in `assets/covers/` '
                f'(receipt: `assets/covers/YOUTUBE-PROVENANCE.json`).' if plat else
                '- No embeddable public video: the videos route and Movie Club show an honest "Watch on" panel with official links.')
        wr(site / 'README.md', f"""# {c.name} — private preview concept

PRIVATE PREVIEW made by AMH. {c.name} has **not** been contacted and has not agreed to this site.
It is not {c.poss} official site. Every route is `noindex,nofollow`, `robots.txt` disallows all crawling,
`_headers` sends `X-Robots-Tag: noindex, nofollow`, and no sitemap or llms.txt is published. A small
always-visible banner on every route links to {c.poss} official hub ({c.hub}).

## What is here
{vids}
- Official links only: {links} (`assets/socials.json`). {'Public business email: ' + c.email + '.' if c.email else 'No public email exists, so collab/contact points to the official links.'}
  The newsletter API fails closed (no recipient).
- Follower figures: {fl}.
- Merch: none. Store routes show an honest "Merch coming soon" state. No prices, checkout or payments.
- Avatar = public profile photo ({c.avatar_source}). Wordmark and Movie Club heading are text renders (tools/bubble-letters.py).

Generated by D:/amh-tmp/clone/clone_creator.py. Template provenance: see `artwork/ASSET-PROVENANCE.json`.

## Build and check
```sh
python tools/export-brand.py
npm run build && npm test && python tools/completion-check.py
PREVIEW_PORT=8805 python tools/server.py      # serve public/
PREVIEW_BASE=http://127.0.0.1:8805 python tools/browser-check.py
```
Do not deploy without Austin's OK. Target: `{c.origin}` (separate private preview, never the AMH hub).
""")
        wr(site / 'CREATOR-SETUP.md', f"""# Creator setup status — {c.name} (private preview)

- [x] Identity, social URLs and avatar replaced with verified public data{'' if c.email else ' (no public email exists)'}.
- [x] Base creator media, artwork, wordmark and covers removed (leak check: 0 hits).
- [x] Video catalogs (JSON + JS) rebuilt from the verified pass file; covers + provenance recorded.
- [x] Follower evidence: {fl}.
- [x] Merch: none; honest coming-soon state.
- [x] Bubble heading, wordmark, favicon, app icons and social preview regenerated locally.
- [x] Private preview: noindex,nofollow everywhere, robots Disallow, X-Robots-Tag, banner on every route.
- [ ] Creator contact, consent and any deployment — only with Austin's explicit OK.
""")

    # ---- 8. brand art --------------------------------------------------------------------------------
    def art(self):
        c, site = self.c, self.site
        py = sys.executable
        jobs = [[py, 'tools/bubble-letters.py', c.name, f'assets/{c.slug}-wordmark.webp', '1200'],
                [py, 'tools/bubble-letters.py', f'{c.first}\u2019s Movie Club', f'assets/{c.first_slug}-movie-bubble.webp', '1400']]
        with ThreadPoolExecutor(2) as ex: list(ex.map(lambda j: run(j, site), jobs))
        self.lap('wordmark + bubble')
        run([py, 'tools/export-brand.py'], site)
        ff = shutil.which('ffmpeg')
        if ff:
            run([ff, '-y', '-loglevel', 'error', '-i', 'assets/share-animated.gif', '-movflags', 'faststart', '-pix_fmt', 'yuv420p',
                 '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', 'assets/share-animated.mp4'], site)
        self.lap('icons + social preview')
        # asset provenance
        pp = site / 'artwork/ASSET-PROVENANCE.json'
        prov = json.loads(rd(pp)) if pp.exists() else {}
        keep = [f for f in prov.get('files', []) if f.get('path', '').startswith('assets/social-') and (site / f['path']).exists()]
        for f in keep: f['sha256'] = sha(site / f['path'])
        files = [{'path': self.avatar_rel, 'method': ('AMH concept wordmark, not a creator portrait, ' if self.data.get('avatar_kind')=='concept_wordmark' else 'Public profile avatar, ') + ('cropped to ' + str(self.data['avatar_crop']) if self.data.get('avatar_crop') else 'center-cropped to square')
                  + f', resized to 900x900 and re-encoded as JPEG (original sha256 {self.avatar_orig_sha})', 'source': c.avatar_source, 'sha256': sha(site / self.avatar_rel)},
                 {'path': f'assets/{c.slug}-wordmark.webp', 'method': f'Text wordmark rendered locally: python tools/bubble-letters.py "{c.name}" assets/{c.slug}-wordmark.webp 1200 (bundled Fredoka Bold, OFL). Not an official logo.', 'sha256': sha(site / f'assets/{c.slug}-wordmark.webp')},
                 {'path': f'assets/{c.first_slug}-movie-bubble.webp', 'method': f'Movie Club heading rendered locally: python tools/bubble-letters.py "{c.first}’s Movie Club" assets/{c.first_slug}-movie-bubble.webp 1400', 'sha256': sha(site / f'assets/{c.first_slug}-movie-bubble.webp')}]
        for fp in ('assets/social-preview.png', 'assets/favicon.svg', 'assets/icon-512.png'):
            files.append({'path': fp, 'method': 'python tools/export-brand.py' + (' (avatar + wordmark composition)' if 'preview' in fp else ''), 'sha256': sha(site / fp)})
        wr(pp, jdump({'note': prov.get('note', 'Template code and generic UI assets come from the AMH creator template.'), 'checkedAt': TODAY, 'files': files + keep}))

    # ---- 9. build, test, leak check ------------------------------------------------------------------
    def build_test(self):
        r = run('npm run build', self.site); self.lap('npm run build')
        r = run('npm test', self.site, check=False)
        self.report['npm_test'] = 'pass' if r.returncode == 0 else 'FAIL'
        self.report['npm_test_tail'] = ((r.stdout or '') + (r.stderr or ''))[-1500:]
        self.lap('npm test')
        if r.returncode: raise Fail('npm test failed:\n' + self.report['npm_test_tail'])

    def leak_check(self):
        b, c = self.b, self.c
        blob = c.blob()
        toks = {b.name: re.I, b.slug: re.I, b.slug.split('-')[0] + '-movie': re.I}
        if b.first != b.name and len(b.first) >= 3: toks[b.first] = 0
        if b.last and len(b.last) >= 3: toks[b.last] = 0
        for v in b.socials.values():
            if len(v['handle']) >= 4: toks[v['handle'].lstrip('@')] = re.I
        toks[disp(b.hub)] = re.I
        for e in b.emails: toks[e] = re.I
        if b.channel_id: toks[b.channel_id] = 0; toks['UU' + b.channel_id[2:]] = 0
        for i in b.all_ids: toks[i] = 0
        toks = {t: f for t, f in toks.items() if t and t.lower() not in blob and t.lower() not in c.name.lower()}
        rx = [(t, re.compile(r'(?<![\w])' + re.escape(t) + r'(?![\w])', f)) for t, f in toks.items()]
        hits, prov = [], []
        for f in self.site.rglob('*'):
            if not f.is_file() or 'fonts' in f.parts or 'node_modules' in f.parts: continue
            if f.suffix.lower() not in TEXT_EXT | {'.xml', '.webmanifest', ''}: continue
            try: s = f.read_text(encoding='utf-8')
            except Exception: continue
            if f == self.site / 'tools/check.mjs':
                s = re.sub(r"(?<=if\(/).*?(?=/i\.test\(s\)\)failures\.push\('Old identity)", '', s)
            if getattr(self, 'old_alts', None): s = s.replace('|'.join(self.old_alts), '')  # check.mjs guard list itself
            for t, r in rx:
                for m in r.finditer(s):
                    line = s.count('\n', 0, m.start()) + 1
                    rec = f'{f.relative_to(self.site).as_posix()}:{line}: {t!r} …{s[max(0, m.start() - 40):m.end() + 40]!r}'
                    (prov if 'PROVENANCE' in f.name else hits).append(rec)
        self.report['leak_tokens'] = len(toks); self.report['leak_hits'] = len(hits); self.report['leak_provenance_hits'] = len(prov)
        self.lap('leak check')
        if hits: raise Fail(f'leak check: {len(hits)} base-identity hits\n' + '\n'.join(hits[:40]))

    def git_commit(self):
        c = self.c
        run(['git', 'add', '--', f'sites/{c.slug}'], self.out)
        staged = run(['git', 'diff', '--cached', '--name-only'], self.out).stdout.split()
        bad = [x for x in staged if not x.startswith(f'sites/{c.slug}/')]
        if bad: raise Fail('unexpected staged files: ' + ', '.join(bad[:5]))
        msg = (f'Add {c.name} unlisted preview site (noindex, {c.mode} base {self.b.slug}, not contacted)\n\n'
               f'Cloned with clone_creator.py from the {self.b.slug} preview. {len(self.long)} videos, '
               f'{len(c.socials)} official links, leak check 0 hits. Not deployed.\n\n'
               'Existing Claude cloner with Codex hardening; native playback is checked separately.\n')
        run(['git', 'commit', '-q', '-m', msg], self.out)
        self.report['commit'] = run(['git', 'rev-parse', '--short', 'HEAD'], self.out).stdout.strip()
        self.report['files_committed'] = len(staged)
        self.lap('git commit')

    def browser_check(self):
        port = free_port()
        env = {**os.environ, 'PREVIEW_PORT': str(port)}
        srv = subprocess.Popen([sys.executable, 'tools/server.py'], cwd=str(self.site), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                try: socket.create_connection(('127.0.0.1', port), 0.2).close(); break
                except OSError: time.sleep(0.1)
            r = run([sys.executable, 'tools/browser-check.py'], self.site, env={**os.environ, 'PREVIEW_BASE': f'http://127.0.0.1:{port}'}, check=False, timeout=1200)
            out = r.stdout or ''
            fails = [l for l in out.splitlines() if l.startswith('FAIL')]
            final = next((l for l in out.splitlines() if l.startswith('FINAL')), 'FINAL ?')
            self.report['browser_check'] = {'port': port, 'exit': r.returncode, 'passed': sum(1 for l in out.splitlines() if l.startswith('PASS')),
                                            'failed': len(fails), 'fails': fails[:20], 'final': final, 'stderr_tail': (r.stderr or '')[-800:]}
        finally:
            srv.terminate()
        self.lap('browser-check')

    # ---- main --------------------------------------------------------------------------------------------
    def go(self):
        c = self.c
        print(f'clone {c.slug} ({c.name}) mode={c.mode} base={self.b.slug} -> {self.out}', flush=True)
        self.worktree(); self.lap('worktree + copy')
        self.media(); self.lap(f'media ({len(c.videos)} covers + avatar)')
        self.build_catalog(); self.build_maps()
        for e in self.long:
            if 'desc' in e: e['desc'] = self.swap(e['desc'])
        self.gen_blocks()
        self.patch_index(); self.patch_build(); self.patch_checks(); self.patch_js()
        self.text_pass(); self.write_data(); self.lap('identity rewrite')
        from clone_polish import polish
        polish(self.site)
        self.art()
        self.build_test()
        import subprocess as _sp  # Claude polish pass (Austin 2026-10-24): see README 'READ FIRST'
        _sp.run([sys.executable, str(Path(__file__).with_name('claude_polish.py')), str(self.site)], check=True)
        self.leak_check()
        if self.commit: self.git_commit()
        if self.browser: self.browser_check()
        self.report['seconds'] = round(time.time() - self.t0, 1); self.report['times'] = self.times
        return self.report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('data'); ap.add_argument('out')
    ap.add_argument('--base', choices=list(BASES), help='force a base instead of video_mode')
    ap.add_argument('--no-commit', action='store_true'); ap.add_argument('--browser-check', action='store_true')
    a = ap.parse_args()
    try:
        cl = Clone(a.data, a.out, a.base, not a.no_commit, a.browser_check)
        rep = cl.go()
    except Fail as e:
        print('CLONE FAILED:', e, file=sys.stderr); sys.exit(2)
    rp = Path(a.out).resolve().parent / f'{rep["slug"]}.clone-report.json'
    rp.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in rep.items() if k != 'npm_test_tail'}, indent=2, ensure_ascii=False))
    ok = rep.get('npm_test') == 'pass' and rep.get('leak_hits') == 0 and (not a.browser_check or rep['browser_check']['exit'] == 0)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    if '--base' in sys.argv and sys.argv[sys.argv.index('--base')+1] == 'maria':
        from maria_adapter import main as maria_main
        maria_main()
    else:
        main()
