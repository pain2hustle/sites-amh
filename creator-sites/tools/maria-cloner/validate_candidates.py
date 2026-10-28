"""Validate complete Maria candidates; browser inspection is a separate release gate."""
import argparse,json,re
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from maria_adapter import HERE,audit

def main():
 ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);a=ap.parse_args();reports=[]
 for recipe in sorted((HERE/'recipes').glob('*.json')):
  c=json.loads(recipe.read_text(encoding='utf8'));out=a.root/c['slug'];original=(HERE/c['source']).resolve()
  if not (out/'index.html').exists():raise AssertionError('Missing complete candidate: '+c['slug'])
  rep=audit(out,original);rep.update(slug=c['slug'],files=sum(p.is_file() for p in out.rglob('*')),indexing_preserved=True,css_missing=[])
  for p in out.rglob('*.html'):
   def robots(f):return str(BeautifulSoup(f.read_text(encoding='utf8'),'html.parser').find('meta',attrs={'name':'robots'}))
   if robots(p)!=robots(original/p.relative_to(out)):rep['indexing_preserved']=False
  for css in (out/'assets/maria-reference').glob('*.css'):
   for raw in re.findall(r'url\(([^)]+)\)',css.read_text(encoding='utf8')):
    u=raw.strip('\"\' ')
    if u.startswith('/') and not (out/urlsplit(u).path.lstrip('/')).exists():rep['css_missing'].append(u)
  assert not rep['failures'] and not rep['css_missing'] and rep['indexing_preserved'],rep
  reports.append(rep)
 assert len(reports)==12
 print(json.dumps({'sites':12,'routes':sum(x['html_routes'] for x in reports),'files':sum(x['files'] for x in reports),'failures':0,'visual_acceptance':'separate and still required'},indent=2))
if __name__=='__main__':main()
