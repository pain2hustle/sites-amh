"""Actual-Maria frontend adapter for the existing creator cloner.
Preserves complete creator payloads and scripts; imports the pinned Maria layout.
No network, Git writes, backend provisioning, publishing, or account copying.
"""
import argparse, copy, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path
from urllib.parse import urlsplit, unquote
from bs4 import BeautifulSoup
from clone_creator import Fail, wr, sha, jdump
HERE=Path(__file__).resolve().parent

def soup(text): return BeautifulSoup(text,'html.parser')
def node(x): return copy.deepcopy(x) if x else None

def header(doc, ref):
    old=doc.find('header')
    if not old:return
    brand=old.select_one('.release-brand') or old.select_one('a')
    links=old.select_one('.release-nav');socials=old.select_one('.release-socials')
    actions=old.select_one('.release-actions')
    if not all([brand,links,actions]):raise Fail('Missing reviewed header content')
    new=node(ref.find(id='bar'));new['class']=['bar','solid','maria-clone-header']
    new.find('a',class_='logo').replace_with(node(brand))
    new.find('a')['class']=['logo','maria-brand']
    right=new.select_one('.right');right.clear()
    nav=node(links);nav['class']=['maria-primary-nav'];right.append(nav)
    sc=node(socials) if socials else doc.new_tag('div');sc['class']=['soc','maria-socials'];sc['id']='navSoc'
    for a in sc.select('a'):
        label=a.get('aria-label') or a.get_text(' ',strip=True)
        a['aria-label']=label
        img=a.find('img')
        if img:
            img.extract();img['alt']='';a.clear();a.append(img)
            span=doc.new_tag('span');span['class']='sr-only';span.string=label;a.append(span)
    right.append(sc)
    for x in list(actions.contents):right.append(node(x))
    old.replace_with(new)

def menu(doc, ref):
    old=doc.find(id='menu')
    if old:
        # Reuse the actual Maria mgrid/mside hierarchy; retain every verified link/card.
        new=node(ref.find(id='menu'));new['inert']='';new['aria-hidden']='true'
        oldlinks=old.select_one('.mlinks');side=old.select_one('.mside')
        if oldlinks:new.select_one('.mlinks').replace_with(node(oldlinks))
        else:raise Fail('Creator menu has no links')
        if side:new.select_one('.mside').replace_with(node(side))
        else:new.select_one('.mside').clear()
        foot=new.select_one('.mfoot');foot.decompose()
        new['data-maria-source']='menu';old.replace_with(new)

def home(doc,ref):
    # The full established creator content remains, within Maria's exact section hierarchy.
    profile=doc.select_one('#about .profile')
    if profile:
        section=node(ref.find(id='links'));section['id']='about';section['data-maria-source']='profile'
        donor=section.select_one('.profile');donor.replace_with(node(profile))
        original_asides=doc.select('#about aside')
        for i,aside in enumerate(section.select('.profile-videos')):
            aside.clear();aside.attrs.pop('aria-label',None)
            if i<len(original_asides):
                for child in original_asides[i].contents:aside.append(node(child))
        doc.find(id='about').replace_with(section)
    film=doc.select_one('.film')
    if film:
        new=node(ref.find(id='top'));new['aria-label']=film.get('aria-label','Introduction');new['data-maria-source']='intro'
        stage=new.select_one('.stage');stage.clear()
        tag=film.select_one('.shot-tag')
        if tag:stage.append(node(tag))
        for shot in film.select('.shot'):stage.append(node(shot))
        prog=film.select_one('.prog')
        if prog:stage.append(node(prog))
        controls=film.select_one('.cinema-controls')
        if controls:stage.append(node(controls))
        film.replace_with(new)
    club=doc.find(id='movieClub')
    if club:
        # Preserve the complete original movie UI and its exact runtime IDs.
        club['data-maria-source']='movie-club'
        layout=club.select_one('.movie-layout')
        if layout:layout['class']=[x for x in layout.get('class',[]) if x!='movie-layout']+['club-layout','movie-layout']
    doc.body['data-maria-adapter']='2026-10-28'

def audit(out, original):
    failures=[];htmls=list(out.rglob('*.html'));headers=0
    for p in htmls:
        s=soup(p.read_text(encoding='utf8'));rel=p.relative_to(out).as_posix()
        ids=[x['id'] for x in s.select('[id]')]
        if len(ids)!=len(set(ids)):failures.append(rel+': duplicate DOM id')
        if s.find('header'):
            headers+=1
            if not s.select_one('.maria-clone-header'):failures.append(rel+': wrong header')
            if len(s.select('.maria-primary-nav a'))<3:failures.append(rel+': missing navigation')
            if not (s.find(id='burger') or s.find(id='menuOpen')):failures.append(rel+': missing menu control')
        for x in s.select('[src],a[href],link[href]'):
            val=x.get('src') or x.get('href','');u=urlsplit(val)
            if u.scheme or u.netloc or not u.path:continue
            target=out/unquote(u.path.lstrip('/')) if u.path.startswith('/') else p.parent/unquote(u.path)
            if not target.exists():failures.append(rel+': missing '+val)
        # Donor identities and payments must never appear in generated HTML.
        if re.search(r'marialatinax|mariaalatinaax|marialatinaaxx|p8W2j9qcRDs|DeS5oekubwF',str(s),re.I):failures.append(rel+': donor identity')
        orig=original/p.relative_to(out)
        if orig.exists():
            os=soup(orig.read_text(encoding='utf8'))
            if [x.get('src') for x in s.select('script[src]')]!=[x.get('src') for x in os.select('script[src]')]:failures.append(rel+': runtime changed')
            for x in os.select('a[href]'):
                href=x['href']
                if href.startswith(('https:','mailto:')) and not s.find('a',href=href):failures.append(rel+': lost creator URL '+href)
    # Retain every original file; JS and binary contents are byte-identical.
    for p in original.rglob('*'):
        if not p.is_file():continue
        q=out/p.relative_to(original)
        if not q.exists():failures.append('Lost original file '+str(p.relative_to(original)))
        elif p.suffix not in ('.html','.css') and sha(p)!=sha(q):failures.append('Changed payload '+str(p.relative_to(original)))
    return {'html_routes':len(htmls),'headers':headers,'failures':failures}

def build(data,out):
    cfg=json.loads(Path(data).read_text(encoding='utf8'))
    original=(HERE/cfg['source']).resolve();out=Path(out).resolve();refdir=HERE/'reference'
    if out.exists():raise Fail('Output must be new; existing sites are never overwritten')
    if not (original/'index.html').is_file():raise Fail('Missing complete source site')
    ref=soup((refdir/'index.html').read_text(encoding='utf8'))
    shutil.copytree(original,out)
    assets=out/'assets/maria-reference';assets.mkdir(parents=True)
    wr(assets/'layout.css','\n'.join(t.get_text() for t in ref.find_all('style')))
    for name in ['brand.css','cinema.css','extensions.css','fix-1012.css']:shutil.copy2(refdir/'assets'/name,assets/name)
    shutil.copy2(HERE/'integration.css',assets/'integration.css')
    wordmark='/assets/maria-reference/creator-wordmark.webp'
    movieart='/assets/maria-reference/movie-club.webp'
    for label,target in [(cfg['name'],wordmark),(cfg['name'].split()[0]+'’s Movie Club',movieart)]:
        subprocess.run([sys.executable,str(HERE/'art/bubble-letters.py'),label,str(out/target.lstrip('/')),'1200'],check=True,capture_output=True)
    first=soup((original/'index.html').read_text(encoding='utf8'))
    portrait=(first.select_one('.film .media img') or first.select_one('main img'))['src']
    for css in assets.glob('*.css'):
        text=css.read_text(encoding='utf-8-sig')
        for donor in ['/assets/maria-brand-4k.jpg','/assets/maria-brand.webp','/assets/maria-name-bubble.webp?v=3']:text=text.replace(donor,wordmark)
        text=text.replace('/img/8.jpg',portrait)
        wr(css,text)
    for p in out.rglob('*.html'):
        s=soup(p.read_text(encoding='utf8'))
        if not s.find('header'):continue
        header(s,ref);menu(s,ref)
        if p==out/'index.html':home(s,ref)
        for l in s.select('link[rel=stylesheet]'):
            if l.get('href')=='/assets/release-layout.css':l.decompose()
        for name in ['layout.css','cinema.css','brand.css','extensions.css','fix-1012.css','integration.css']:
            l=s.new_tag('link',rel='stylesheet',href='/assets/maria-reference/'+name);s.head.append(l)
        for img in s.select('img'):
            if img.get('src')==cfg['wordmark']:img['src']=wordmark
        title=s.select_one('#movieClub h2')
        if title:
            title.clear();art=s.new_tag('img',src=movieart,alt=cfg['name'].split()[0]+'’s Movie Club');art['class']='movie-title-art';title.append(art)
        s.body['data-maria-slug']=cfg['slug']
        wr(p,str(s))
    result=audit(out,original);result.update(slug=cfg['slug'],source=str(original),output=str(out),reference_sha256=sha(refdir/'index.html'),complete_payload=True,visual_status='pending',backend='Creator runtime retained; donor backend not copied')
    wr(out.parent/(cfg['slug']+'.maria-report.json'),jdump(result))
    if result['failures']:raise Fail(jdump(result['failures'][:20]))
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('data');ap.add_argument('out');ap.add_argument('--base',choices=['maria'],required=True);ap.add_argument('--no-commit',action='store_true');a=ap.parse_args()
    print(jdump(build(a.data,a.out)))
if __name__=='__main__':main()
