#!/usr/bin/env python3
"""Validate the exact current242 base, then add the reviewed isolated directories.
No networking or deployment. Never deletes or rebases an existing business file.
"""
from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
import argparse, hashlib, json, os, stat, sys, tempfile, types, zipfile
BASE_BUILDER_SHA256 = '48b61557356fc64cc3d8fd11822953ec0962855aec2d236a056d7dda9aad9cf1'
BASE_MANIFEST_SHA256 = '29239835f2f409c7d5da0de342d9df0c5226228d87629b8da0ced35af0864b7e'
OVERLAY_MANIFEST_SHA256 = 'f3f81030df989ee50a344fbc75732e7c90b12280d06b89406e8da2ccb26d128c'
PUBLIC_PATHS = ('creators/index.html','creators/sites.json','directory/businesses.json','index.html')
FINAL_FILE_COUNT = 3040
MAX_ARCHIVE_BYTES = 8*1024*1024
MAX_FILE_BYTES = 10_000_000
MAX_TOTAL_BYTES = 900_000_000
ORIGIN = 'https://sites-amh.pages.dev'

def need(ok, message):
    if not ok:raise ValueError(message)
def digest(data):return hashlib.sha256(data).hexdigest()
def strict_object(pairs):
    d={}
    for k,v in pairs:
        need(k not in d,'Duplicate JSON key');d[k]=v
    return d
def integer(n):return type(n)is int and n>=0
def safe_path(value):
    p=Path(value)
    need('..'not in p.parts,'Parent traversal filesystem path rejected')
    p=p.absolute();need(not any(x.is_symlink()for x in (p,*p.parents)),'Symlink path/ancestor rejected')
    return p.resolve(strict=False)
def regular(path):
    p=safe_path(path);need(p.is_file(),'Regular file required: '+str(path));return p
def read_pinned(path, expected):
    b=regular(path).read_bytes();need(digest(b)==expected,'Exact input pin mismatch: '+str(path));return b
def safe_name(name):
    return type(name)is str and bool(name) and '\\'not in name and ':'not in name and not name.startswith('/')and PurePosixPath(name).as_posix()==name and all(x not in ('','.','..')for x in name.split('/'))
def records(rows):
    need(type(rows)is list,'File inventory must be a list');out={}
    for r in rows:
        need(type(r)is dict and set(r)=={'path','size','sha256'},'Exact file record schema')
        p=r['path'];h=r['sha256'];need(safe_name(p)and p not in out,'Unsafe/duplicate file path')
        need(integer(r['size'])and r['size']<=MAX_FILE_BYTES and type(h)is str and len(h)==64 and all(c in '0123456789abcdef'for c in h),'Invalid file size/hash')
        out[p]=r
    return out

def load_inputs(repo):
    repo=safe_path(repo);overlay=safe_path(repo/'directory-overlay');need(overlay.is_dir(),'Overlay folder missing')
    need({p.name for p in overlay.iterdir()}=={'manifest.json','directory.zip'},'Exact overlay input membership')
    basecode=read_pinned(repo/'build_base242.py',BASE_BUILDER_SHA256)
    baseraw=read_pinned(repo/'packs/packs.json',BASE_MANIFEST_SHA256);base=json.loads(baseraw,object_pairs_hook=strict_object)
    raw=read_pinned(overlay/'manifest.json',OVERLAY_MANIFEST_SHA256);m=json.loads(raw,object_pairs_hook=strict_object)
    need(type(m)is dict and set(m)=={'format','profile','origin','base','archive','overlay_files','file_count','total_bytes','files','business_records','creator_records'},'Overlay manifest schema')
    need(type(m['format'])is int and m['format']==1 and m['profile']=='master-directory-business3180-creator3384-v2'and m['origin']==ORIGIN,'Exact directory profile')
    need(m['base']=={'source_commit':'d7e7938d68ddce8dcddcc86590d42f8cce27fc39','builder_sha256':BASE_BUILDER_SHA256,'manifest_sha256':BASE_MANIFEST_SHA256,'file_count':3037,'total_bytes':90281874,'root_index_sha256':'0df4125f86f0c0298d70994676cadb5db00222efdb8cbccf8a8cd011c717afdb'},'Exact current still-fixed base required')
    need(type(m['file_count'])is int and m['file_count']==FINAL_FILE_COUNT and FINAL_FILE_COUNT<=20000,'Exact combined file count/cap')
    need(integer(m['total_bytes'])and m['total_bytes']<=MAX_TOTAL_BYTES,'Combined byte cap')
    need(type(m['business_records'])is int and m['business_records']==3180 and type(m['creator_records'])is int and m['creator_records']==3384,'Exact reviewed directory counts')
    bf=records(base['files']);of=records(m['overlay_files']);final=records(m['files'])
    need(base['file_count']==3037 and len(bf)==3037 and base['total_bytes']==90281874,'Exact base inventory')
    need(tuple(sorted(of))==PUBLIC_PATHS and set(of)&set(bf)=={'index.html'},'Only root index replacement and three new paths')
    combined=dict(bf);combined.update(of);need(final==combined and len(final)==FINAL_FILE_COUNT and sum(r['size']for r in final.values())==m['total_bytes'],'Exact unchanged-base plus four-file union')
    a=m['archive'];need(type(a)is dict and set(a)=={'name','size','sha256'}and a['name']=='directory.zip'and integer(a['size'])and 0<a['size']<MAX_ARCHIVE_BYTES,'Exact archive metadata')
    zpath=regular(overlay/a['name']);need(zpath.stat().st_size==a['size'],'Archive byte size');read_pinned(zpath,a['sha256'])
    data={}
    with zipfile.ZipFile(zpath)as z:
        for info in z.infolist():
            name=info.filename;need(name in of and name not in data and safe_name(name),'Unexpected/duplicate ZIP member')
            need(not info.is_dir()and stat.S_IFMT(info.external_attr>>16)==stat.S_IFREG and not info.flag_bits&1 and info.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),'ZIP path/type/encryption/compression rejected')
            r=of[name];need(info.file_size==r['size'],'ZIP declared size mismatch')
            with z.open(info)as stream:b=stream.read(r['size']+1)
            need(len(b)==r['size']and digest(b)==r['sha256'],'ZIP content mismatch');data[name]=b
    need(set(data)==set(PUBLIC_PATHS),'Four overlay members required')
    validate_directory_data(data)
    return repo,basecode,base,m,bf,of,final,data

class DirectoryHTML(HTMLParser):
    def __init__(self):super().__init__();self.canonical=[];self.og=[];self.noindex=False;self.record_ids=[];self.external_scripts=[];self.external_resources=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='link'and a.get('rel')=='canonical':self.canonical.append(a.get('href'))
        if tag=='meta'and a.get('property')=='og:url':self.og.append(a.get('content'))
        if tag=='meta'and a.get('name','').lower()=='robots'and 'noindex'in a.get('content','').lower():self.noindex=True
        if 'data-directory-record'in a:self.record_ids.append(a['data-directory-record'])
        if tag=='script'and a.get('src'):self.external_scripts.append(a['src'])
        for k in ('src','data-src','poster'):
            if k in a:self.external_resources.append(a[k])
def validate_directory_data(data):
    business=json.loads(data['directory/businesses.json'],object_pairs_hook=strict_object)
    creator=json.loads(data['creators/sites.json'],object_pairs_hook=strict_object)
    need(len(business['records'])==3180 and len(creator['records'])==3384,'Data record count mismatch')
    need(all(r['id'].startswith('business-')and r['category']in ('barbers','restaurants')for r in business['records']),'Business-only data required')
    need(all(r['id'].startswith('creator-')for r in creator['records']),'Creator-only data required')
    for path,db,count in [('index.html',business,3180),('creators/index.html',creator,3384)]:
        text=data[path].decode('utf-8');p=DirectoryHTML();p.feed(text)
        url=ORIGIN+'/'if path=='index.html'else ORIGIN+'/creators/'
        need(p.canonical==[url]and p.og==[url]and p.noindex,'Exact canonical/og/noindex required')
        need(len(p.record_ids)==len(set(p.record_ids))==count and set(p.record_ids)=={r['id']for r in db['records']},'HTML/data record identity mismatch')
        need(not p.external_scripts,'No external script dependencies')
        if path=='index.html':
            need('/creators/'not in text and 'creators/sites.json'not in text and 'creator-record-'not in text,'Business root must not import/link/embed creator directory')
            need(not any('/creators/'in x for x in p.external_resources),'No creator resources on business root')

def inventory(root, expected):
    found={};root=safe_path(root)
    for p in root.rglob('*'):
        safe_path(p)
        if p.is_dir():continue
        need(p.is_file(),'Nonregular output');name=p.relative_to(root).as_posix();need(name in expected,'Unexpected output file')
        b=p.read_bytes();r=expected[name];need(len(b)==r['size']and digest(b)==r['sha256'],'Output byte mismatch: '+name);found[name]=r
    need(set(found)==set(expected),'Output missing files');return found

def run_build(repo, output):
    repo=safe_path(repo);destination=safe_path(output)
    need(not destination.exists()and destination.parent.is_dir(),'Fresh output with existing parent required')
    need(destination!=repo and destination not in repo.parents and not repo.is_relative_to(destination),'Output cannot replace repository')
    for protected in (repo/'packs',repo/'directory-overlay'):
        need(not destination.is_relative_to(protected)and not protected.is_relative_to(destination),'Output overlaps inputs')
    repo,basecode,base,m,bf,of,final,data=load_inputs(repo)
    name='_reviewed_base242_for_directory';need(name not in sys.modules,'Base module name already in use')
    module=types.ModuleType(name);module.__file__=str(repo/'build_base242.py');sys.modules[name]=module
    try:
        exec(compile(basecode,str(repo/'build_base242.py'),'exec'),module.__dict__)
        with tempfile.TemporaryDirectory(prefix='.master-directory-build-',dir=destination.parent)as temp:
            staged=Path(temp)/'public'
            module.run_build(repo/'packs',staged) # Existing exact242 validator and exporter unchanged.
            inventory(staged,bf)
            for path,b in data.items():
                target=staged/path;target.parent.mkdir(parents=True,exist_ok=True);safe_path(target)
                if path=='index.html':target.unlink() # Only the reviewed staged root; original inputs untouched.
                with os.fdopen(os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644),'wb')as f:f.write(b)
            inventory(staged,final)
            module.recheck_inputs((repo/'packs').resolve(),module.frozen_profile(),base)
            read_pinned(repo/'build_base242.py',BASE_BUILDER_SHA256);read_pinned(repo/'directory-overlay/manifest.json',OVERLAY_MANIFEST_SHA256);read_pinned(repo/'directory-overlay/directory.zip',m['archive']['sha256'])
            destination=safe_path(destination)
            destination.mkdir(exist_ok=False) # Atomic no-overwrite reservation, even for an empty competing directory.
            reserved=destination.stat()
            try:
                current=destination.lstat();need(stat.S_ISDIR(current.st_mode)and(current.st_dev,current.st_ino)==(reserved.st_dev,reserved.st_ino),'Output reservation changed')
                os.rename(staged,destination) # Replaces only our own empty reserved directory.
            except Exception:
                try:
                    current=destination.lstat()
                    if stat.S_ISDIR(current.st_mode)and(current.st_dev,current.st_ino)==(reserved.st_dev,reserved.st_ino):destination.rmdir()
                except OSError:pass # Never delete any competing nonempty output.
                raise
    finally:sys.modules.pop(name,None)
    result={'files':len(final),'bytes':m['total_bytes'],'preserved_base_non_index_files':3036,'replaced_files':['index.html'],'added_files':['creators/index.html','creators/sites.json','directory/businesses.json'],'business_directory_records':3180,'separate_creator_records':3384,'base_business_homepages':242,'overlay_manifest_sha256':OVERLAY_MANIFEST_SHA256}
    print(json.dumps(result,sort_keys=True));return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='_site');a=p.parse_args()
    try:run_build(Path(__file__).resolve().parent,a.output)
    except (ValueError,OSError,zipfile.BadZipFile)as e:p.exit(1,'Build rejected: '+str(e)+'\n')
if __name__=='__main__':main()
