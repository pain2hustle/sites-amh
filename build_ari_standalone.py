#!/usr/bin/env python3
"""Export the reviewed Ari release for the explicitly requested ari1of1.pages.dev project."""
from pathlib import Path
import argparse,importlib.util,os,tempfile,json
ORIGIN='https://ari1of1.pages.dev'
PREFIX='creators/ari1of1/'

def run_build(repo,output):
 repo=Path(repo).absolute();output=Path(output).absolute()
 spec=importlib.util.spec_from_file_location('_reviewed_ari',repo/'build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 output=m.safe(output);m.need(not output.exists()and output.parent.is_dir(),'Fresh output required')
 m.need(output!=repo and not repo.is_relative_to(output),'Output cannot replace source')
 m.need(not any(output.is_relative_to(repo/p)or(repo/p).is_relative_to(output)for p in ['packs','directory-overlay','business-release','creator-release']),'Output/input overlap')
 _,manifest,data=m.load_release(repo);selected={n[len(PREFIX):]:b for n,b in data.items()if n.startswith(PREFIX)}
 m.need(len(selected)==manifest['site_files'],'Exact standalone file inventory')
 with tempfile.TemporaryDirectory(prefix='.ari-standalone-',dir=output.parent)as t:
  stage=Path(t)/'public';stage.mkdir()
  for n,b in selected.items():
   if Path(n).suffix in ['.html','.css','.js','.json','.xml','.svg']:
    s=b.decode('utf-8').replace('https://sites-amh.pages.dev/'+PREFIX,ORIGIN+'/').replace('/'+PREFIX,'/')
    s=s.replace('href="/creators/"','href="https://sites-amh.pages.dev/creators/"')
    m.need('/'+PREFIX not in s,'Unconverted base path');b=s.encode('utf-8')
   p=m.safe(stage/n);p.parent.mkdir(parents=True,exist_ok=True)
   with os.fdopen(os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644),'wb')as f:f.write(b)
  m.need(not output.exists(),'Output changed during build');os.rename(stage,output)
 return {'origin':ORIGIN,'files':len(selected),'verified_reels':manifest['verified_reels'],'video_target_met':False}

if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--output',default='_site');args=a.parse_args()
 try:print(json.dumps(run_build(Path(__file__).resolve().parent,args.output)))
 except(ValueError,OSError)as e:a.exit(1,'Build rejected: '+str(e)+'\n')
