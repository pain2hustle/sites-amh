#!/usr/bin/env python3
"""Export the exact current directory, then add twenty reviewed business websites."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,os,stat,tempfile,types,zipfile,re
BASE_SHA='d7159117c1995f84cb61b185494dc919a1d721e89e52e915fb9bffc51bd2f05f'
MANIFEST_SHA='4c9095efd0c2944519a9e1cceacfa9123414d658ae43b0deb8c616f2866ddd47'
def need(v,msg):
 if not v:raise ValueError(msg)
def sha(b):return hashlib.sha256(b).hexdigest()
def safe(p):
 p=Path(p).absolute();need('..' not in p.parts,'Parent traversal')
 need(not any(x.is_symlink() for x in (p,*p.parents)),'Symlink input/output')
 return p
def safe_name(n):
 return isinstance(n,str) and n and not n.startswith('/') and '\\' not in n and all(x not in ('','.','..') for x in n.split('/'))
def inventory(root):
 return {p.relative_to(root).as_posix():{'size':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in root.rglob('*') if p.is_file()}
def load_release(repo):
 repo=safe(repo);code=(repo/'build_current20261029.py').read_bytes();need(sha(code)==BASE_SHA,'Pinned current builder mismatch')
 base=types.ModuleType('_current_directory');base.__file__=str(repo/'build_current20261029.py');exec(compile(code,base.__file__,'exec'),base.__dict__)
 folder=safe(repo/'business-twenty-release');raw=(folder/'manifest.json').read_bytes();need(sha(raw)==MANIFEST_SHA,'Pinned twenty manifest mismatch');m=json.loads(raw)
 need(m['format']==2 and m['business_base_commit']=='7ac40216428b73781bbffcbbc1ed6ab852f8fc9d','Exact base identity')
 need(m['origin']=='https://sites-amh.pages.dev' and m['namespace']=='business/batch3/' and m['asset_prefix']=='business/batch3/assets/ga07-ca22-20261029/','Exact host and namespace')
 routes=m['routes'];need(len(routes)==len(set(routes))==20 and all(re.fullmatch('[a-z0-9-]+',r) for r in routes),'Twenty safe unique routes')
 need(m['business_records']==3509 and len(m['baseline_static_files'])==6342,'Exact current counts')
 files=m['files'];need(len(files)==296 and sum(x['size'] for x in files.values())<120_000_000,'Bounded release')
 need(set(files)&set(m['baseline_static_files'])=={'index.html','directory/businesses.json'},'Only directory files may change')
 need(all(safe_name(n) and (n in ('index.html','directory/businesses.json') or n.startswith(m['asset_prefix']) or any(n.startswith(m['namespace']+r+'/') for r in routes)) for n in files),'Public namespace boundary')
 need(all(m['namespace']+r+'/index.html' in files for r in routes),'Every homepage present')
 need({p.name for p in folder.iterdir()}=={'manifest.json',*(p['name'] for p in m['packs'])},'Exact release input membership')
 data={}
 for ix,p in enumerate(m['packs']):
  need(p['name']==f'part-{ix:02d}.zip' and 0<p['size']<8*1024*1024,'Bounded pack')
  path=safe(folder/p['name']);b=path.read_bytes();need(len(b)==p['size'] and sha(b)==p['sha256'],'Pack hash/size')
  seen=set()
  with zipfile.ZipFile(path) as z:
   for i in z.infolist():
    n=i.filename;need(n in p['members'] and n in files and n not in seen and n not in data and safe_name(n),'Unexpected/duplicate member')
    need(not i.is_dir() and stat.S_IFMT(i.external_attr>>16)==stat.S_IFREG and not i.flag_bits&1 and i.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),'Regular unencrypted member')
    r=files[n];need(i.file_size==r['size']<10_000_000,'Member size')
    with z.open(i) as f:b=f.read(r['size']+1)
    need(len(b)==r['size'] and sha(b)==r['sha256'],'Member bytes/hash');data[n]=b;seen.add(n)
  need(seen==set(p['members']),'Complete pack membership')
 need(set(data)==set(files),'Complete release')
 _,cm,cd=base.load_release(repo)
 initial=json.loads(cd['creators/sites.json']);source=safe(repo/'influencer-release/batch800.json').read_bytes()
 recs=json.loads(source)['records']
 need(all(r['id'].startswith('creator-b800-') and r['url'].startswith('https://') and r['url'].endswith('.amh-creator-previews.pages.dev') for r in recs),'Current creator source identity')
 have={r['id'] for r in initial['records']}|{r['url'] for r in initial['records']}
 recs=[r for r in recs if r['id'] not in have and r['url'] not in have]
 need(len({r['id'] for r in recs})==len(recs),'Current creator source duplicate ids')
 current=dict(initial);current['records']=initial['records']+recs
 current['counts']=dict(initial.get('counts',{}),claude_batch800_live_checked=len(recs))
 snapshot={'source_sha256':sha(source),'creator_json':json.dumps(current,ensure_ascii=False,separators=(',',':')).encode('utf-8'),'creator_records':len(current['records'])}
 return base,m,data,snapshot
def verify_current_creators(output,snapshot):
 need((output/'creators/sites.json').read_bytes()==snapshot['creator_json'],'Exact current creator source output required')
 return snapshot['creator_records']

def apply_release(output,m,data,snapshot):
 before=inventory(output)
 need(set(before)==set(m['baseline_static_files'])|{'creators/index.html','creators/sites.json'},'Exact current output membership')
 need(all(before[n]==v for n,v in m['baseline_static_files'].items()),'Exact non-creator baseline output required')
 old=json.loads((output/'directory/businesses.json').read_bytes());new=json.loads(data['directory/businesses.json'])
 need(len(old['records'])==3489 and len(new['records'])==3509 and new['records'][:3489]==old['records'],'All previous business records retained')
 added=new['records'][3489:];need(len({r['id'] for r in new['records']})==3509,'Unique business identities')
 need({r['url'] for r in added}=={m['origin']+'/'+m['namespace']+r+'/' for r in m['routes']},'Exact new URLs')
 need(sum(r['category']=='barbers' for r in added)==11 and sum(r['subcategory']=='cafe' for r in added)==9,'Exact cohorts')
 oldhtml=(output/'index.html').read_text(encoding='utf-8');newhtml=data['index.html'].decode('utf-8')
 for tag in ('script','style'):
  pattern=r'<'+tag+r'\b.*?</'+tag+'>'
  need(re.findall(pattern,oldhtml,re.S)==re.findall(pattern,newhtml,re.S),'Directory interaction/style preservation')
 cards=re.findall(r'<li class="record".*?</li>',oldhtml,re.S)
 need(len(cards)==3489 and all(c in newhtml for c in cards),'All previous directory cards unchanged')
 verify_current_creators(output,snapshot)
 for n,b in data.items():
  p=safe(output/n);p.parent.mkdir(parents=True,exist_ok=True)
  if n in before:p.unlink()
  with os.fdopen(os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644),'wb') as f:f.write(b)
 expected=dict(before);expected.update(m['files']);after=inventory(output)
 need(after==expected,'Exact additive output union')
 need(all(after[n]==v for n,v in before.items() if n not in data),'Every unrelated output byte preserved')
 return {'files':len(after),'prior_files_preserved':len(before)-2,'business_records':3509,'creator_records':snapshot['creator_records'],'new_businesses':20,'new_files':294}
def run_build(repo,output):
 repo=safe(repo);dest=safe(output)
 need(not dest.exists() and dest.parent.is_dir(),'Fresh destination required')
 need(dest!=repo and not repo.is_relative_to(dest),'Output cannot replace source')
 need(not any(dest.is_relative_to(repo/p) or (repo/p).is_relative_to(dest) for p in ('packs','directory-overlay','business-release','creator-release','business-twenty-release')),'Output/input overlap')
 base,m,data,snapshot=load_release(repo)
 with tempfile.TemporaryDirectory(prefix='.twenty-reviewed-',dir=dest.parent) as t:
  staged=Path(t)/'public';base.run_build(repo,staged);result=apply_release(staged,m,data,snapshot);need(load_release(repo)[3]['source_sha256']==snapshot['source_sha256'],'Creator source changed during build')
  need(not dest.exists(),'Destination changed during build');os.rename(staged,dest)
 print(json.dumps(result,sort_keys=True));return result
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='_site');a=p.parse_args()
 try:run_build(Path(__file__).resolve().parent,a.output)
 except (ValueError,OSError,zipfile.BadZipFile) as e:p.exit(1,'Build rejected: '+str(e)+'\n')
if __name__=='__main__':main()
