#!/usr/bin/env python3
"""Validate and copy one independent creator source root; no network or deployment."""
from pathlib import Path
import argparse,hashlib,json,shutil

def stage(repo,slug,output=None,check_only=False):
 repo=Path(repo).resolve();manifest=repo/'creator-sites/release-eleven-20261028.manifest.json'
 data=json.loads(manifest.read_text());site=next((x for x in data['sites']if x['slug']==slug),None)
 if not site:raise ValueError('Unknown creator slug')
 source=(repo/site['directory']).resolve()
 if not source.is_relative_to(repo):raise ValueError('Invalid source root')
 entries=[x for x in data['files']if x['path'].startswith(site['directory']+'/')]
 if not entries:raise ValueError('Empty source manifest')
 total=0
 for entry in entries:
  path=repo/entry['path']
  if path.is_symlink() or not path.is_file():raise ValueError('Missing or symbolic-link source: '+entry['path'])
  if not path.resolve().is_relative_to(source):raise ValueError('Source escapes creator root')
  content=path.read_bytes()
  if len(content)!=entry['bytes']or hashlib.sha256(content).hexdigest()!=entry['sha256']:raise ValueError('Source hash mismatch: '+entry['path'])
  total+=len(content)
 if not check_only:
  if output is None:raise ValueError('An output directory is required unless --check-only is used')
  dest=Path(output).resolve()
  if dest==repo or dest.is_relative_to(repo):raise ValueError('Output must be outside the repository')
  if dest.exists():raise ValueError('Output already exists; choose a new empty staging path')
  dest.mkdir(parents=True)
  for entry in entries:
   src=repo/entry['path'];target=dest/src.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
  for entry in entries:
   src=repo/entry['path'];target=dest/src.relative_to(source)
   if hashlib.sha256(target.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Copied file verification failed')
 return {'creator':slug,'files':len(entries),'bytes':total,'mode':'checked-only'if check_only else'staged','noindex':'preserved','deployed':False}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('slug');parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[2]);parser.add_argument('--output',type=Path);parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
 try:print(json.dumps(stage(args.repo_root,args.slug,args.output,args.check_only),indent=2))
 except (ValueError,OSError,KeyError)as e:parser.exit(1,str(e)+'\n')
