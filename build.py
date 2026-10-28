#!/usr/bin/env python3
"""Export the pinned 3,489-business directory, then add Ari's reviewed creator site."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,stat,tempfile,zipfile
BASE_SHA='f68462be31b9da370c040e00784eeafffe6e5857f0309692324b4dc1ca384a88'
MANIFEST_SHA='a6e12526ee9ac270e5771b564a230cba7f78730a0c6e3039a4d482528148e153'
NAMESPACE='creators/ari1of1/'

def need(v,msg):
 if not v:raise ValueError(msg)
def sha(b):return hashlib.sha256(b).hexdigest()
def safe(p):
 p=Path(p).absolute();need('..'not in p.parts,'Parent traversal');need(not any(q.is_symlink()for q in(p,*p.parents)),'Symlink input/output');return p

def load_release(repo):
 repo=safe(repo);code=(repo/'build_business3489.py').read_bytes();need(sha(code)==BASE_SHA,'Pinned base builder mismatch')
 spec=importlib.util.spec_from_file_location('_business3489',repo/'build_business3489.py');base=importlib.util.module_from_spec(spec);exec(compile(code,str(repo/'build_business3489.py'),'exec'),base.__dict__)
 raw=(repo/'creator-release/manifest.json').read_bytes();need(sha(raw)==MANIFEST_SHA,'Pinned creator manifest mismatch');m=json.loads(raw)
 need(m['format']==1 and m['origin']=='https://sites-amh.pages.dev'and m['namespace']==NAMESPACE,'Creator identity/origin')
 need(m['base_commit']=='73432bb2374697b75e6bd3b9495430607d0807a1'and m['base_builder_sha256']==BASE_SHA,'Base identity')
 need(m['business_records']==3489 and m['previous_creator_records']==3386 and m['creator_records']==3387 and m['verified_reels']==4,'Honest release counts')
 files=m['files'];need(len(files)==51 and all(n in('creators/index.html','creators/sites.json')or n.startswith(NAMESPACE)for n in files),'Exact creator-only scope')
 need(all('..'not in Path(n).parts and not n.startswith('/')and '\\'not in n for n in files),'Safe release paths')
 archive=m['archive'];need(archive['name']=='ari1of1.zip'and 0<archive['size']<8*1024*1024,'Bounded archive');p=safe(repo/'creator-release'/archive['name']);need(p.stat().st_size==archive['size'],'Archive size');b=p.read_bytes();need(sha(b)==archive['sha256'],'Archive hash')
 data={}
 with zipfile.ZipFile(p)as z:
  for i in z.infolist():
   n=i.filename;need(n in files and n not in data,'Unexpected/duplicate ZIP path');need(stat.S_IFMT(i.external_attr>>16)==stat.S_IFREG and not i.is_dir()and not i.flag_bits&1,'ZIP regular files only');r=files[n];need(i.file_size==r['size']<8*1024*1024,'ZIP size')
   with z.open(i)as s:b=s.read(r['size']+1)
   need(len(b)==r['size']and sha(b)==r['sha256'],'ZIP content');data[n]=b
 need(set(data)==set(files),'Complete creator archive');return base,m,data

def apply_release(output,m,data):
 output=safe(output);old_html=(output/'creators/index.html').read_bytes();old_json=(output/'creators/sites.json').read_bytes()
 need(sha(old_html)==m['base_directory_sha256']and sha(old_json)==m['base_creator_json_sha256'],'Exact previous creator directory')
 old=json.loads(old_json);new=json.loads(data['creators/sites.json']);need(new['records'][:-1]==old['records'],'All previous creator records unchanged');need(len(old['records'])==3386 and len(new['records'])==3387,'One added record')
 r=new['records'][-1];need(r['id']=='creator-ari1of1'and r['url']=='https://sites-amh.pages.dev/creators/ari1of1/','Exact new creator')
 before={p.relative_to(output).as_posix():sha(p.read_bytes())for p in output.rglob('*')if p.is_file()};need(len(before)==6289,'Exact previous exported file count')
 need(len(json.loads((output/'directory/businesses.json').read_bytes())['records'])==3489,'Business count preserved')
 need(set(before)&set(data)=={'creators/index.html','creators/sites.json'},'No old website overwrites')
 for n,b in data.items():
  p=safe(output/n);p.parent.mkdir(parents=True,exist_ok=True)
  if n in before:p.unlink()
  with os.fdopen(os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644),'wb')as f:f.write(b)
 after={p.relative_to(output).as_posix():sha(p.read_bytes())for p in output.rglob('*')if p.is_file()}
 need(len(after)==6338 and all(after[n]==h for n,h in before.items()if n not in data),'Every prior website retained byte-for-byte')
 need(all(after[n]==m['files'][n]['sha256']for n in data),'Every creator output hash')
 return {'files':len(after),'prior_files_preserved':6287,'business_records_unchanged':3489,'creator_records':3387,'verified_reels':4,'requested_video_target_met':False}

def run_build(repo,output):
 repo=safe(repo);dest=safe(output);need(not dest.exists()and dest.parent.is_dir(),'Fresh destination required');need(dest!=repo and not repo.is_relative_to(dest),'Output cannot replace source')
 need(not any(dest.is_relative_to(repo/p)or(repo/p).is_relative_to(dest)for p in['packs','directory-overlay','business-release','creator-release']),'Output/input overlap')
 base,m,data=load_release(repo)
 with tempfile.TemporaryDirectory(prefix='.ari-reviewed-',dir=dest.parent)as t:
  staged=Path(t)/'public';base.run_build(repo,staged);result=apply_release(staged,m,data);load_release(repo)
  need(not dest.exists(),'Destination changed during build');os.rename(staged,dest)
 print(json.dumps(result,sort_keys=True));return result

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--output',default='_site');args=a.parse_args()
 try:run_build(Path(__file__).resolve().parent,args.output)
 except(ValueError,OSError,zipfile.BadZipFile)as e:a.exit(1,'Build rejected: '+str(e)+'\n')
if __name__=='__main__':main()
