#!/usr/bin/env python3
"""Export the exact existing directory, then a reviewed additive business release."""
from pathlib import Path
from html.parser import HTMLParser
import argparse,hashlib,importlib.util,json,os,stat,tempfile,zipfile

FROZEN_BUILDER_SHA256='25d0648d94b07bccbc335543bb74824be0c46b8877346eda58e004e6a8f26a79'
RELEASE_MANIFEST_SHA256='6b9c5a1b2ee4a75e99254890c4918c8084a950b0f1700acb563afd3dc10e0968'
ORIGIN='https://sites-amh.pages.dev'
PREFIX='business/batch3/'
EXPECTED_NEW=290
EXPECTED_BUSINESSES=3489
MAX_PACK_BYTES=8*1024*1024
MAX_FILE_BYTES=10_000_000
MAX_TOTAL_BYTES=900_000_000

def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(b):return hashlib.sha256(b).hexdigest()
def strict(pairs):
 d={}
 for k,v in pairs:
  need(k not in d,'Duplicate JSON key');d[k]=v
 return d
def safe_path(p):
 p=Path(p);need('..'not in p.parts,'Parent traversal');p=p.absolute()
 need(not any(x.is_symlink()for x in(p,*p.parents)),'Symlink input/output path')
 return p.resolve(strict=False)
def pinned(p,h):
 p=safe_path(p);need(p.is_file(),'Regular pinned file required');b=p.read_bytes();need(sha(b)==h,'Exact input pin mismatch: '+str(p));return b
def load_inputs(repo):
 repo=safe_path(repo)
 code=pinned(repo/'build_directory3199.py',FROZEN_BUILDER_SHA256)
 spec=importlib.util.spec_from_file_location('_exact_directory3199',repo/'build_directory3199.py')
 base=importlib.util.module_from_spec(spec);exec(compile(code,str(repo/'build_directory3199.py'),'exec'),base.__dict__)
 old=base.load_inputs(repo);oldfiles=old[6];olddata=old[7]
 raw=pinned(repo/'business-release/manifest.json',RELEASE_MANIFEST_SHA256);m=json.loads(raw,object_pairs_hook=strict)
 need(set(m)=={'format','profile','origin','namespace','base_commit','base_builder_sha256','base_manifest_sha256','new_routes','business_records','creator_records','packs','release_files','files','file_count','total_bytes'},'Exact release manifest schema')
 need(m['format']==1 and type(m['format'])is int and m['profile']=='batch3-remaining290-business3489-v1'and m['origin']==ORIGIN and m['namespace']==PREFIX,'Exact reviewed release profile')
 need(m['base_commit']=='81a1d8a661795db7c1000ccc4454c860307719bc'and m['base_builder_sha256']==FROZEN_BUILDER_SHA256 and m['base_manifest_sha256']==base.OVERLAY_MANIFEST_SHA256,'Exact unchanged directory base')
 need(m['business_records']==EXPECTED_BUSINESSES and m['creator_records']==3386,'Reviewed record counts')
 routes=m['new_routes'];need(type(routes)is list and len(routes)==len(set(routes))==EXPECTED_NEW,'Exact unique route count')
 need(all(type(x)is str and x and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-'for c in x)for x in routes),'Unsafe route')
 release=base.records(m['release_files']);final=base.records(m['files'])
 need(set(release)&set(oldfiles)=={'index.html','directory/businesses.json'},'Only directory HTML/data can replace existing output')
 need(all(x in('index.html','directory/businesses.json')or any(x.startswith(PREFIX+r+'/')for r in routes)for x in release),'Release outside reviewed business routes')
 need(all(PREFIX+r+'/index.html'in release for r in routes),'Missing reviewed homepage')
 combined=dict(oldfiles);combined.update(release)
 need(final==combined and m['file_count']==len(final)<=20000 and sum(x['size']for x in final.values())==m['total_bytes']<=MAX_TOTAL_BYTES,'Exact unchanged base/release union')
 packs=m['packs'];need(type(packs)is list and 0<len(packs)<=20,'Bounded pack list')
 need({p.name for p in(repo/'business-release').iterdir()}=={'manifest.json',*(x['name']for x in packs)},'Exact release input membership')
 data={};seenpacks=set()
 for ix,a in enumerate(packs):
  need(type(a)is dict and set(a)=={'name','size','sha256','members'}and a['name']==f'part-{ix:02d}.zip'and a['name']not in seenpacks,'Exact pack metadata/name')
  seenpacks.add(a['name']);need(type(a['size'])is int and 0<a['size']<MAX_PACK_BYTES,'Pack byte cap')
  need(type(a['members'])is list and len(a['members'])==len(set(a['members']))and all(x in release for x in a['members']),'Pack membership inventory')
  zpath=safe_path(repo/'business-release'/a['name']);need(zpath.stat().st_size==a['size'],'Pack size mismatch');pinned(zpath,a['sha256'])
  got=set()
  with zipfile.ZipFile(zpath)as z:
   for info in z.infolist():
    name=info.filename;need(base.safe_name(name)and name in a['members']and name not in got and name not in data,'Unsafe/duplicate/unexpected ZIP member')
    need(not info.is_dir()and stat.S_IFMT(info.external_attr>>16)==stat.S_IFREG and not info.flag_bits&1 and info.compress_type in(zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),'ZIP member type rejected')
    r=release[name];need(info.file_size==r['size']<=MAX_FILE_BYTES,'ZIP declared size mismatch')
    with z.open(info)as stream:b=stream.read(r['size']+1)
    need(len(b)==r['size']and sha(b)==r['sha256'],'ZIP content mismatch');data[name]=b;got.add(name)
  need(got==set(a['members']),'Incomplete pack')
 need(set(data)==set(release),'Missing release files')
 business=json.loads(data['directory/businesses.json'],object_pairs_hook=strict)
 previous=json.loads(olddata['directory/businesses.json'],object_pairs_hook=strict)
 rows=business['records'];need(len(rows)==EXPECTED_BUSINESSES and rows[:3199]==previous['records'],'Exact3199 prior records/URLs retained')
 new=rows[3199:];need(len(new)==EXPECTED_NEW and len({x['id']for x in rows})==len(rows),'Unique record identities')
 need({x['url']for x in new}=={ORIGIN+'/'+PREFIX+r+'/'for r in routes},'Exact added website URLs')
 need(all(x['id'].startswith('business-')and x['category']in('barbers','restaurants')for x in rows),'Business-only directory')
 text=data['index.html'].decode('utf-8');parser=base.DirectoryHTML();parser.feed(text)
 need(parser.canonical==[ORIGIN+'/']and parser.og==[ORIGIN+'/']and parser.noindex,'Canonical/OG/noindex retained')
 need(len(parser.record_ids)==len(set(parser.record_ids))==EXPECTED_BUSINESSES and set(parser.record_ids)=={r['id']for r in rows},'HTML/data identity equality')
 need(not parser.external_scripts and '/creators/'not in text and 'creators/sites.json'not in text and 'creator-record-'not in text,'Business/creator separation and no new script dependency')
 return repo,base,m,oldfiles,release,final,data

def run_build(repo,output):
 repo=safe_path(repo);destination=safe_path(output)
 need(not destination.exists()and destination.parent.is_dir(),'Fresh output required')
 need(destination!=repo and destination not in repo.parents and not repo.is_relative_to(destination),'Output cannot replace repository')
 for p in(repo/'packs',repo/'directory-overlay',repo/'business-release'):
  need(not destination.is_relative_to(p)and not p.is_relative_to(destination),'Output overlaps input')
 repo,base,m,oldfiles,release,final,data=load_inputs(repo)
 with tempfile.TemporaryDirectory(prefix='.reviewed-business-release-',dir=destination.parent)as t:
  staged=Path(t)/'public';base.run_build(repo,staged);base.inventory(staged,oldfiles)
  for path,b in data.items():
   target=staged/path;target.parent.mkdir(parents=True,exist_ok=True);safe_path(target)
   if path in('index.html','directory/businesses.json'):target.unlink()
   with os.fdopen(os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644),'wb')as f:f.write(b)
  base.inventory(staged,final)
  # Recheck every pinned input after export, including inherited base packs.
  load_inputs(repo)
  frozen=base.load_inputs(repo)
  for pack in frozen[2]['packs']:
   source=safe_path(repo/'packs'/pack['name'])
   need(source.stat().st_size==pack['size'],'Inherited pack changed size')
   pinned(source,pack['sha256'])
  destination=safe_path(destination);destination.mkdir(exist_ok=False);reserved=destination.stat()
  try:
   current=destination.lstat();need(stat.S_ISDIR(current.st_mode)and(current.st_dev,current.st_ino)==(reserved.st_dev,reserved.st_ino),'Output reservation changed')
   os.rename(staged,destination)
  except Exception:
   try:
    current=destination.lstat()
    if stat.S_ISDIR(current.st_mode)and(current.st_dev,current.st_ino)==(reserved.st_dev,reserved.st_ino):destination.rmdir()
   except OSError:pass
   raise
 result={'files':len(final),'bytes':m['total_bytes'],'preserved_previous_non_directory_files':len(oldfiles)-2,'new_businesses':EXPECTED_NEW,'business_directory_records':EXPECTED_BUSINESSES,'creator_records_unchanged':3386,'manifest_sha256':RELEASE_MANIFEST_SHA256}
 print(json.dumps(result,sort_keys=True));return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='_site');a=p.parse_args()
 try:run_build(Path(__file__).resolve().parent,a.output)
 except(ValueError,OSError,zipfile.BadZipFile)as e:p.exit(1,'Build rejected: '+str(e)+'\n')
if __name__=='__main__':main()
