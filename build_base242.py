#!/usr/bin/env python3
"""Exact separate242-business static export. No rebasing, network, or deploy.
Pinned to one reviewed source profile; no generic manifests or pack sets accepted.
"""
from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
from dataclasses import dataclass
import argparse, hashlib, json, os, re, shutil, stat, tempfile, types, zipfile

ORIGIN = 'https://sites-amh.pages.dev'
PROFILE_MANIFEST_SHA256 = '29239835f2f409c7d5da0de342d9df0c5226228d87629b8da0ced35af0864b7e'
EXACT_PACK_NAMES = ('part-001.zip', 'part-002.zip', 'part-003.zip', 'part-004.zip', 'part-005.zip', 'part-006.zip', 'part-007.zip', 'part-008.zip', 'part-009.zip', 'part-010.zip', 'part-011.zip', 'part-012.zip', 'part-013.zip', 'part-014.zip')
EXPECTED_FILE_COUNT = 3037
EXPECTED_HOMEPAGES = 242
EXPECTED_NEW_ROUTES = 242
CLOUDFLARE_FREE_FILE_CAP = 20000
EXACT_GUIDE_RECORDS = ()
GUIDE_PATHS = frozenset(r[0] for r in EXACT_GUIDE_RECORDS)
REVIEWED_VALIDATOR_SHA256 = '5f35966be7eb3d34f684a04563e82b9a65918f7df33139cfbcc325c1785b9620'
REVIEWED_VALIDATOR_SOURCE = '"""Restrictive policy shared by the local packer and the deployment validator."""\nimport re\nfrom pathlib import PurePosixPath\n\nEXTENSIONS = {\'.html\', \'.css\', \'.js\', \'.svg\', \'.png\', \'.jpg\', \'.jpeg\', \'.webp\', \'.ico\', \'.ttf\', \'.woff\', \'.woff2\', \'.webmanifest\', \'.mp4\'}\nROOT_FILES = {\'index.html\', \'404.html\', \'robots.txt\', \'.nojekyll\'}\nSITE_FILES = {\'index.html\', \'404.html\', \'favicon.ico\', \'robots.txt\', \'site.webmanifest\', \'sw.js\'}\nSUBPAGES = {\'faq\', \'menu\', \'privacy\', \'terms\'}\nBAD_COMPONENTS = {\'node_modules\', \'private\', \'credentials\', \'secrets\', \'src\', \'source\', \'qa\', \'leads\', \'__pycache__\'}\nAPPROVED_MP4 = {\n \'f669f1e75c7498e69cacac58bcff156cd2419e3d51e1d6108bf5c4d8d5a187eb\',\n \'63c28b0b833d8b4b99d6ef1e02dfeb34d6c5acd3745d9e993c6bf84ec86ebcda\',\n \'5df38d6223b0b5d6851b433ab71e27a2fb79005b4932b7bfb9850171f563b608\',\n \'a96d6031e9af134fae64ec65921fdb9a832746dbf50cd4940232f6f65af6c752\',\n \'f6903f735fb8a2223ab800f786572c22ca3709410c2ba8584f4b2142a74ba410\',\n \'7c15b8aaac6a299db4c536a5881d4c0a3a93fa6f21633abd2dca507112e24345\',\n \'7cc6598e5c43c74443264fbde8a524c8c62760f3ce45e91460fce7a9526f8546\',\n \'c3b838769cc93dc8f2f57f57bfe7e898985f3c9e722a3241b11ae804afde1ddc\',\n \'26a8e7e00bec5499f17b38ba50dd88ace06e7f5bb0b0b238a79758da368437e0\',\n \'0acf5959ba6219f3e9c8782db180fc831837f8a0dbe0c202341a670b26c71582\',\n \'017ebb76ae5a4dfbf932cfb864553bc8c74cbea4f91f2b0f830511f5a17df015\',\n\n \'c8d48e1e03b9b812ab9e3faaccdcb9c3cb4b4ae8129d17d3f2dfa83b0b8d53d7\',\n \'5638aef456dee6808d134d167900bdc0f4b5cb531e9a28713be3815756345a37\',\n \'f514d51c243cbee88eff16422c48a7484a3a08ac3a3f5033c9f7a59f1d91f605\',\n}\nMAX_MP4_BYTES = 2_000_000\n# Exact current live enhanced dye asset; no generic size-cap expansion.\nAPPROVED_MP4_SIZE_EXCEPTIONS = {\'c3b838769cc93dc8f2f57f57bfe7e898985f3c9e722a3241b11ae804afde1ddc\': 6_000_000}\nMAX_TOTAL_BYTES = 900_000_000\nMAX_FILE_BYTES = 10_000_000\nMAX_FILES = 30000\nMAX_PACK_BYTES = 25 * 1024 * 1024\n\ndef allowed_path(name):\n    if not isinstance(name, str) or not name or len(name) > 240:\n        return False\n    if \'\\\\\' in name or \'\\x00\' in name or name.startswith(\'/\') or name.endswith(\'/\'):\n        return False\n    p = PurePosixPath(name)\n    if p.as_posix() != name or any(x in {\'\', \'.\', \'..\'} for x in name.split(\'/\')):\n        return False\n    if name in ROOT_FILES:\n        return True\n    if not re.fullmatch(r\'[A-Za-z0-9_./-]+\', name):\n        return False\n    if any(x.startswith(\'.\') or x.lower() in BAD_COMPONENTS for x in p.parts):\n        return False\n    if p.suffix.lower() not in EXTENSIONS and p.name != \'robots.txt\':\n        return False\n    if p.suffix.lower() == \'.mp4\':\n        return len(p.parts) == 2 and p.parts[0] == \'assets\' and p.suffix == \'.mp4\' and p.stem in APPROVED_MP4\n    if p.parts[0] == \'assets\':\n        return len(p.parts) == 2 and bool(re.fullmatch(r\'[0-9a-f]{40,64}\\.[a-z0-9]+\', p.name)) and p.suffix.lower() in EXTENSIONS\n    if len(p.parts) < 3 or p.parts[0] not in {\'barbers\', \'restaurants\'}:\n        return False\n    if not re.fullmatch(r\'[a-z0-9][a-z0-9-]{0,119}\', p.parts[1]):\n        return False\n    tail = p.parts[2:]\n    if len(tail) == 1:\n        return tail[0] in SITE_FILES\n    if len(tail) == 2 and tail[0] in SUBPAGES and tail[1] == \'index.html\':\n        return True\n    if tail[0] == \'assets\':\n        return len(tail) >= 2 and p.suffix.lower() in EXTENSIONS\n    return False\n\n"""Validate the exact public pack manifest, then extract static files safely."""\nimport argparse, hashlib, json, re, shutil, stat, zipfile\nfrom pathlib import Path\n\n\ndef strict_object(pairs):\n    result={}\n    for key,value in pairs:\n        if key in result: raise ValueError(\'Duplicate JSON key\')\n        result[key]=value\n    return result\n\ndef integer(n):\n    return type(n) is int and n >= 0\n\ndef sha(s):\n    return isinstance(s,str) and bool(re.fullmatch(r\'[0-9a-f]{64}\',s))\n\ndef digest_file(path):\n    with path.open(\'rb\') as f:\n        return hashlib.file_digest(f,\'sha256\').hexdigest()\n\ndef extract(pack_dir, destination):\n    pack_dir=Path(pack_dir).resolve(strict=True)\n    destination=Path(destination).absolute()\n    if destination.exists() or destination.is_symlink():\n        raise ValueError(\'Extraction destination must not exist\')\n    mf=pack_dir/\'packs.json\'\n    if mf.is_symlink() or not mf.is_file() or mf.stat().st_size > 16_000_000:\n        raise ValueError(\'Invalid manifest file\')\n    manifest=json.loads(mf.read_text(),object_pairs_hook=strict_object)\n    if set(manifest)!={\'format\',\'file_count\',\'total_bytes\',\'packs\',\'files\'} or manifest[\'format\']!=1:\n        raise ValueError(\'Invalid manifest schema\')\n    if not integer(manifest[\'file_count\']) or not 0<manifest[\'file_count\']<=MAX_FILES:\n        raise ValueError(\'Invalid static file count\')\n    if not integer(manifest[\'total_bytes\']) or manifest[\'total_bytes\']>MAX_TOTAL_BYTES:\n        raise ValueError(\'Published site exceeds size policy\')\n    if not isinstance(manifest[\'files\'],list) or len(manifest[\'files\'])!=manifest[\'file_count\']:\n        raise ValueError(\'Invalid static file list\')\n    expected={}\n    for r in manifest[\'files\']:\n        if not isinstance(r,dict) or set(r)!={\'path\',\'sha256\',\'size\'}:\n            raise ValueError(\'Invalid static record\')\n        if not allowed_path(r[\'path\']) or r[\'path\'] in expected:\n            raise ValueError(\'Unsafe or duplicate static path\')\n        if not integer(r[\'size\']) or r[\'size\']>MAX_FILE_BYTES or not sha(r[\'sha256\']):\n            raise ValueError(\'Invalid static size/hash\')\n        expected[r[\'path\']]=r\n    if sum(r[\'size\'] for r in expected.values())!=manifest[\'total_bytes\']:\n        raise ValueError(\'Uncompressed size mismatch\')\n    if not ROOT_FILES<=expected.keys():\n        raise ValueError(\'Required root files missing\')\n    if len([p for p in expected if p.count(\'/\')==2 and p.endswith(\'/index.html\')])!=270:\n        raise ValueError(\'Expected exactly 270 homepages\')\n    if not isinstance(manifest[\'packs\'],list) or not 1<=len(manifest[\'packs\'])<=20:\n        raise ValueError(\'Invalid pack count\')\n    pack_names=set(); verified=[]; seen=set()\n    for pack in manifest[\'packs\']:\n        if not isinstance(pack,dict) or set(pack)!={\'name\',\'size\',\'sha256\'}:\n            raise ValueError(\'Invalid pack record\')\n        name=pack[\'name\']\n        if not isinstance(name,str) or not re.fullmatch(r\'part-[0-9]{3}\\.zip\',name) or name in pack_names:\n            raise ValueError(\'Invalid or duplicate pack filename\')\n        if not integer(pack[\'size\']) or not 0<pack[\'size\']<MAX_PACK_BYTES or not sha(pack[\'sha256\']):\n            raise ValueError(\'Invalid pack size/hash\')\n        pack_names.add(name); path=pack_dir/name\n        if path.is_symlink() or not path.is_file() or path.stat().st_size!=pack[\'size\']:\n            raise ValueError(\'Pack absent or wrong size\')\n        if digest_file(path)!=pack[\'sha256\']:\n            raise ValueError(\'Pack integrity mismatch\')\n        with zipfile.ZipFile(path) as archive:\n            for info in archive.infolist():\n                mode=info.external_attr>>16\n                if info.is_dir() or not stat.S_ISREG(mode) or info.flag_bits&1:\n                    raise ValueError(\'Directory, symlink, special, or encrypted entry rejected\')\n                if info.compress_type not in {zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED}:\n                    raise ValueError(\'Unsupported archive compression\')\n                if info.filename in seen or not allowed_path(info.filename) or info.filename not in expected:\n                    raise ValueError(\'Duplicate, unsafe, or unexpected archive path\')\n                record=expected[info.filename]\n                if info.file_size!=record[\'size\'] or info.file_size>MAX_FILE_BYTES:\n                    raise ValueError(\'Archive entry size mismatch\')\n                with archive.open(info) as stream:\n                    h=hashlib.sha256(); size=0\n                    while chunk:=stream.read(1024*1024):\n                        size+=len(chunk)\n                        if size>record[\'size\']: raise ValueError(\'Archive entry expansion exceeds manifest\')\n                        h.update(chunk)\n                if size!=record[\'size\'] or h.hexdigest()!=record[\'sha256\']:\n                    raise ValueError(\'Static content integrity mismatch\')\n                if info.filename.lower().endswith(\'.mp4\'):\n                    if record[\'sha256\'] not in APPROVED_MP4 or Path(info.filename).stem != record[\'sha256\'] or size > APPROVED_MP4_SIZE_EXCEPTIONS.get(record[\'sha256\'], MAX_MP4_BYTES):\n                        raise ValueError(\'Unapproved or oversized MP4\')\n                    with archive.open(info) as stream:\n                        header = stream.read(32)\n                    if header[4:8] != b\'ftyp\' or header[8:12] != b\'isom\' or b\'avc1\' not in header:\n                        raise ValueError(\'MP4 MIME/codec signature mismatch\')\n                seen.add(info.filename)\n        verified.append(path)\n    if seen!=set(expected):\n        raise ValueError(\'Static files missing from packs\')\n    if {p.name for p in pack_dir.glob(\'part-*.zip\')}!=pack_names:\n        raise ValueError(\'Unexpected ZIP packs present\')\n    # Every path, type, count, length and digest has now passed before writes begin.\n    destination.mkdir(parents=True,exist_ok=False)\n    try:\n        for path in verified:\n            with zipfile.ZipFile(path) as archive:\n                for info in archive.infolist():\n                    target=destination/info.filename\n                    target.parent.mkdir(parents=True,exist_ok=True)\n                    with archive.open(info) as src, target.open(\'xb\') as dst:\n                        shutil.copyfileobj(src,dst,1024*1024)\n                    if digest_file(target)!=expected[info.filename][\'sha256\']:\n                        raise ValueError(\'Post-extraction integrity mismatch\')\n        for name in [\'index.html\']+[p for p in expected if p.count(\'/\')==2 and p.endswith(\'/index.html\')]:\n            if \'noindex\' not in (destination/name).read_text().lower():\n                raise ValueError(\'Preview homepage lacks noindex\')\n        if \'Disallow: /\' not in (destination/\'robots.txt\').read_text():\n            raise ValueError(\'Root robots exclusion missing\')\n    except Exception:\n        shutil.rmtree(destination)\n        raise\n    print(f\'Validated {len(expected)} static files ({manifest["total_bytes"]:,} bytes) in {len(verified)} packs.\')\n\nif __name__==\'__main__\':\n    parser=argparse.ArgumentParser()\n    parser.add_argument(\'pack_dir\',nargs=\'?\',default=\'packs\')\n    parser.add_argument(\'destination\',nargs=\'?\',default=\'_site\')\n    args=parser.parse_args()\n    extract(args.pack_dir,args.destination)\n'
HOMEPAGE_PATHS_SHA256 = '4566a20159f12b697c41a9ecd50ad35d1ed8b225459177f0636a4b0d60942a4f'
NEW_FLAT_ROUTES_SHA256 = 'd1b188d6cbaa5d7a6368352414c7a33c7d24fbe9edceae8b8f44615122e4899d'
EXACT_MP4_RECORDS = (('assets/017ebb76ae5a4dfbf932cfb864553bc8c74cbea4f91f2b0f830511f5a17df015.mp4', 634774, '017ebb76ae5a4dfbf932cfb864553bc8c74cbea4f91f2b0f830511f5a17df015'), ('assets/0acf5959ba6219f3e9c8782db180fc831837f8a0dbe0c202341a670b26c71582.mp4', 1104222, '0acf5959ba6219f3e9c8782db180fc831837f8a0dbe0c202341a670b26c71582'), ('assets/26a8e7e00bec5499f17b38ba50dd88ace06e7f5bb0b0b238a79758da368437e0.mp4', 1960401, '26a8e7e00bec5499f17b38ba50dd88ace06e7f5bb0b0b238a79758da368437e0'), ('assets/5df38d6223b0b5d6851b433ab71e27a2fb79005b4932b7bfb9850171f563b608.mp4', 1342966, '5df38d6223b0b5d6851b433ab71e27a2fb79005b4932b7bfb9850171f563b608'), ('assets/63c28b0b833d8b4b99d6ef1e02dfeb34d6c5acd3745d9e993c6bf84ec86ebcda.mp4', 595817, '63c28b0b833d8b4b99d6ef1e02dfeb34d6c5acd3745d9e993c6bf84ec86ebcda'), ('assets/7c15b8aaac6a299db4c536a5881d4c0a3a93fa6f21633abd2dca507112e24345.mp4', 1088771, '7c15b8aaac6a299db4c536a5881d4c0a3a93fa6f21633abd2dca507112e24345'), ('assets/7cc6598e5c43c74443264fbde8a524c8c62760f3ce45e91460fce7a9526f8546.mp4', 1406287, '7cc6598e5c43c74443264fbde8a524c8c62760f3ce45e91460fce7a9526f8546'), ('assets/a96d6031e9af134fae64ec65921fdb9a832746dbf50cd4940232f6f65af6c752.mp4', 708507, 'a96d6031e9af134fae64ec65921fdb9a832746dbf50cd4940232f6f65af6c752'), ('assets/c3b838769cc93dc8f2f57f57bfe7e898985f3c9e722a3241b11ae804afde1ddc.mp4', 5837556, 'c3b838769cc93dc8f2f57f57bfe7e898985f3c9e722a3241b11ae804afde1ddc'), ('assets/f669f1e75c7498e69cacac58bcff156cd2419e3d51e1d6108bf5c4d8d5a187eb.mp4', 1307185, 'f669f1e75c7498e69cacac58bcff156cd2419e3d51e1d6108bf5c4d8d5a187eb'), ('assets/f6903f735fb8a2223ab800f786572c22ca3709410c2ba8584f4b2142a74ba410.mp4', 992053, 'f6903f735fb8a2223ab800f786572c22ca3709410c2ba8584f4b2142a74ba410'))

def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity_list(values):
    return digest(json.dumps(sorted(values),separators=(',',':')).encode())


@dataclass(frozen=True)
class Profile:
    manifest_sha256: str
    exact_pack_names: tuple
    file_count: int
    homepage_paths_sha256: str
    new_flat_routes_sha256: str
    exact_mp4_records: tuple


def frozen_profile():
    if not re.fullmatch(r'[0-9a-f]{64}',PROFILE_MANIFEST_SHA256):
        raise ValueError('UNFROZEN standalone242 profile: exact host/pack manifest require review; no files were read or extracted')
    if not EXACT_PACK_NAMES or any(not re.fullmatch(r'part-[0-9]{3}\.zip',n) for n in EXACT_PACK_NAMES) or len(set(EXACT_PACK_NAMES))!=len(EXACT_PACK_NAMES):
        raise ValueError('UNFROZEN exact pack names/count')
    if not 0<EXPECTED_FILE_COUNT<=CLOUDFLARE_FREE_FILE_CAP:
        raise ValueError('Invalid reviewed profile file count')
    return Profile(PROFILE_MANIFEST_SHA256,EXACT_PACK_NAMES,EXPECTED_FILE_COUNT,HOMEPAGE_PATHS_SHA256,NEW_FLAT_ROUTES_SHA256,EXACT_MP4_RECORDS)


def strict_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate JSON key')
        result[key]=value
    return result


def manifest_file(packs,profile):
    mf=packs/'packs.json'
    if mf.is_symlink() or not mf.is_file() or mf.stat().st_size>16_000_000:
        raise ValueError('Invalid manifest file')
    data=mf.read_bytes()
    if digest(data)!=profile.manifest_sha256:raise ValueError('Exact reviewed manifest hash mismatch')
    manifest=json.loads(data,object_pairs_hook=strict_object)
    if not isinstance(manifest,dict) or set(manifest)!={'format','file_count','total_bytes','packs','files'}:
        raise ValueError('Invalid manifest schema')
    if type(manifest['format']) is not int or manifest['format']!=1:raise ValueError('Invalid manifest format version')
    if type(manifest['file_count']) is not int or manifest['file_count']!=profile.file_count or manifest['file_count']>CLOUDFLARE_FREE_FILE_CAP:
        raise ValueError('Exact file count / 20,000-file cap mismatch')
    if not isinstance(manifest['files'],list) or any(not isinstance(r,dict) or set(r)!={'path','sha256','size'} or not isinstance(r['path'],str) for r in manifest['files']):
        raise ValueError('Invalid file record schema')
    paths=[r['path'] for r in manifest['files']]
    if len({p.casefold() for p in paths})!=len(paths):raise ValueError('Case-fold duplicate static path')
    homes=sorted(p for p in paths if p not in GUIDE_PATHS and p.endswith('/index.html') and (p.count('/')==1 or (p.count('/')==2 and p.split('/')[0] in {'barbers','restaurants'})))
    if len(homes)!=EXPECTED_HOMEPAGES or len(set(homes))!=EXPECTED_HOMEPAGES or identity_list(homes)!=profile.homepage_paths_sha256:
        raise ValueError('Exact reviewed242 homepage set mismatch')
    flats=sorted(p.split('/')[0] for p in homes if p.count('/')==1)
    if len(flats)!=EXPECTED_NEW_ROUTES or len(set(flats))!=EXPECTED_NEW_ROUTES or identity_list(flats)!=profile.new_flat_routes_sha256:
        raise ValueError('Exact reviewed242 route set mismatch')
    if not isinstance(manifest['packs'],list) or any(not isinstance(r,dict) or set(r)!={'name','size','sha256'} for r in manifest['packs']):
        raise ValueError('Invalid pack record schema')
    if tuple(p['name'] for p in manifest['packs'])!=profile.exact_pack_names:
        raise ValueError('Exact pack names/count/order mismatch')
    mp4=tuple(sorted((r['path'],r['size'],r['sha256']) for r in manifest['files'] if r['path'].lower().endswith('.mp4')))
    if mp4!=profile.exact_mp4_records:raise ValueError('Exact existing MP4 paths/sizes/hash set mismatch')
    guide_records=tuple(sorted((r['path'],r['size'],r['sha256']) for r in manifest['files'] if r['path'].startswith('hair-guides/')))
    if guide_records!=EXACT_GUIDE_RECORDS:raise ValueError('Exact approved8 guide paths/sizes/hash set mismatch')
    return manifest,set(homes),set(flats)


def reviewed_policy(profile,flat_routes):
    if digest(REVIEWED_VALIDATOR_SOURCE.encode())!=REVIEWED_VALIDATOR_SHA256:
        raise ValueError('Embedded unchanged reviewed validator pin mismatch')
    # Three narrow runtime adaptations; the embedded historical source stays byte-identical.
    source=REVIEWED_VALIDATOR_SOURCE
    replacements=[('MAX_FILES = 30000','MAX_FILES = 20000'),
                  ('MAX_PACK_BYTES = 25 * 1024 * 1024','MAX_PACK_BYTES = 8 * 1024 * 1024'),
                  ("if len([p for p in expected if p.count('/')==2 and p.endswith('/index.html')])!=270:","if len([p for p in expected if p.count('/')==1 and p.endswith('/index.html')])!=242:"),
                  ('def extract(pack_dir, destination):','def validate(pack_dir, destination):'),
                  ("if not isinstance(manifest['packs'],list) or not 1<=len(manifest['packs'])<=20:","if not isinstance(manifest['packs'],list) or len(manifest['packs'])!=len(EXACT_PACK_NAMES):")]
    for before,after in replacements:
        if source.count(before)!=1:raise ValueError('Reviewed validator adaptation anchor drift')
        source=source.replace(before,after)
    marker='    # Every path, type, count, length and digest has now passed before writes begin.'
    if source.count(marker)!=1:raise ValueError('Reviewed validation boundary drift')
    source=source.split(marker)[0]+'    return manifest,expected,verified\n'
    ns={'__name__':'reviewed1870_policy','EXACT_PACK_NAMES':profile.exact_pack_names}
    exec(compile(source,'reviewed1870_policy','exec'),ns)
    old_allowed=ns['allowed_path']
    def allowed_path(path):
        if path in GUIDE_PATHS:return True
        if old_allowed(path) and (path in ns['ROOT_FILES'] or path.startswith('assets/')):return True
        if not isinstance(path,str) or len(path)>240 or not re.fullmatch(r'[A-Za-z0-9_./-]+',path):return False
        parts=PurePosixPath(path).parts
        if PurePosixPath(path).as_posix()!=path or any(x in {'','.','..'} for x in path.split('/')):return False
        if any(x.lower() in ns['BAD_COMPONENTS'] or x.startswith('.') for x in parts):return False
        if len(parts)<2 or parts[0] not in flat_routes:return False
        tail=parts[1:]
        if len(tail)==1:return tail[0] in ns['SITE_FILES']
        if len(tail)==2 and tail[0] in ns['SUBPAGES'] and tail[1]=='index.html':return True
        return tail[0]=='assets' and PurePosixPath(path).suffix.lower() in ns['EXTENSIONS'] and PurePosixPath(path).suffix.lower()!='.mp4'
    ns['allowed_path']=allowed_path
    return types.SimpleNamespace(**ns)


def exact_pack_directory(packs,profile):
    if packs.is_symlink() or not packs.is_dir():raise ValueError('Invalid/symlink pack directory')
    wanted={'packs.json',*profile.exact_pack_names}
    actual=set()
    for p in packs.iterdir():
        if p.is_symlink() or not p.is_file():raise ValueError('Unexpected nonregular pack input')
        actual.add(p.name)
    if actual!=wanted:raise ValueError('Extra/missing pack input files')


class HostMetadata(HTMLParser):
    def __init__(self):super().__init__();self.canonicals=[];self.og_urls=[];self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='link' and d.get('rel','').lower()=='canonical':self.canonicals.append(d.get('href'))
        if tag=='meta' and d.get('property','').lower()=='og:url':self.og_urls.append(d.get('content'))
        if tag=='a' and 'href' in d:self.hrefs.append(d['href'])


class NoIndex(HTMLParser):
    def __init__(self):super().__init__();self.present=False
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='meta' and d.get('name','').lower()=='robots' and 'noindex' in [x.strip().lower() for x in d.get('content','').split(',')]:self.present=True


def validate_homepage_robots(verified,homes,expected):
    wanted={'index.html',*homes};seen=set();root_robots=False
    for path in verified:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.filename in wanted or info.filename=='robots.txt':
                    record=expected[info.filename]
                    if info.file_size!=record['size']:raise ValueError('Metadata member size changed after validation')
                    with archive.open(info) as stream:data=stream.read(record['size']+1)
                    if len(data)!=record['size'] or digest(data)!=record['sha256']:raise ValueError('Metadata content changed after validation')
                if info.filename in wanted:
                    parser=NoIndex();parser.feed(data.decode())
                    if not parser.present:raise ValueError('Preview homepage lacks actual robots noindex metadata')
                    metadata=HostMetadata();metadata.feed(data.decode())
                    wanted_url=ORIGIN+'/' if info.filename=='index.html' else ORIGIN+'/'+info.filename.removesuffix('index.html')
                    if metadata.canonicals!=[wanted_url] or metadata.og_urls!=[wanted_url]:raise ValueError('Exact own-host canonical/og:url required')
                    if info.filename=='index.html':
                        expected_links={'/'+p.removesuffix('index.html') for p in homes}
                        links=[x for x in metadata.hrefs if x.startswith('/')]
                        if len(links)!=242 or set(links)!=expected_links:raise ValueError('Root directory must link exactly242 own routes once')
                    seen.add(info.filename)
                elif info.filename=='robots.txt':
                    text=data.decode()
                    if not re.search(r'^\s*Disallow:\s*/\s*$',text,re.M):raise ValueError('Root robots exclusion missing')
                    root_robots=True
    if seen!=wanted or not root_robots:raise ValueError('Noindex/root robots validation incomplete')


def recheck_inputs(packs,profile,manifest):
    exact_pack_directory(packs,profile)
    if digest((packs/'packs.json').read_bytes())!=profile.manifest_sha256:raise ValueError('Manifest changed during build')
    for record in manifest['packs']:
        p=packs/record['name']
        with p.open('rb') as stream:current_hash=hashlib.file_digest(stream,'sha256').hexdigest()
        if p.stat().st_size!=record['size'] or current_hash!=record['sha256']:
            raise ValueError('Pack changed during build')


def extract_validated(verified,expected,policy,staged):
    # Reopened archive metadata is checked again. No extractall or broad unzip is used.
    staged.mkdir();seen=set()
    for path in verified:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                mode=info.external_attr>>16;name=info.filename
                if info.is_dir() or not stat.S_ISREG(mode) or info.flag_bits&1 or info.compress_type not in {zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED}:
                    raise ValueError('Archive metadata changed after validation')
                if name in seen or name not in expected or not policy.allowed_path(name) or info.file_size!=expected[name]['size']:
                    raise ValueError('Archive path/size changed after validation')
                target=staged/name;target.parent.mkdir(parents=True,exist_ok=True)
                if not target.resolve().is_relative_to(staged.resolve()):raise ValueError('Extraction escaped isolated staging')
                with archive.open(info) as source,target.open('xb') as dest:
                    count=0;hasher=hashlib.sha256()
                    while chunk:=source.read(1024*1024):
                        count+=len(chunk)
                        if count>expected[name]['size'] or count>policy.MAX_FILE_BYTES:raise ValueError('Extraction expansion exceeds exact bounds')
                        hasher.update(chunk);dest.write(chunk)
                if count!=expected[name]['size'] or hasher.hexdigest()!=expected[name]['sha256']:raise ValueError('Post-extraction identity mismatch')
                seen.add(name)
    if seen!=set(expected):raise ValueError('Post-extraction exact file set mismatch')


def run_build(packs_dir,output):
    profile=frozen_profile()  # Always first; production skeleton reads/writes nothing until frozen.
    packs=Path(packs_dir)
    exact_pack_directory(packs,profile);packs=packs.resolve(strict=True)
    destination=Path(output).absolute()
    if any(p.is_symlink() for p in (destination,*destination.parents)):raise ValueError('Symlink output ancestor rejected')
    if destination.exists() or destination.is_symlink():raise ValueError('Fresh output required; existing output is never overwritten')
    parent=destination.parent.resolve(strict=True);destination=parent/destination.name
    if destination==packs or destination in packs.parents or packs in destination.parents:raise ValueError('Output overlaps pack inputs')
    if destination.name in {'.git','.github','packs','cloudflare-packs'}:raise ValueError('Unsafe output directory')
    manifest,homes,flats=manifest_file(packs,profile)
    policy=reviewed_policy(profile,flats)
    with tempfile.TemporaryDirectory(prefix='.cf242-build-',dir=parent) as td:
        staged=Path(td)/'output'
        checked,expected,verified=policy.validate(packs,staged)
        if checked!=manifest:raise ValueError('Manifest changed during validation')
        validate_homepage_robots(verified,homes,expected)
        recheck_inputs(packs,profile,manifest)
        # All archive/path/type/count/size/hash/MP4/noindex checks precede any extraction.
        extract_validated(verified,expected,policy,staged)
        recheck_inputs(packs,profile,manifest)  # Final source checks precede atomic rename.
        if destination.exists() or destination.is_symlink():raise ValueError('Output appeared during build; no overwrite')
        os.rename(staged,destination)
    result={'files':len(expected),'bytes':manifest['total_bytes'],'homepages':EXPECTED_HOMEPAGES,'packs':len(profile.exact_pack_names),'url_rewrites':0,'manifest_sha256':profile.manifest_sha256}
    print(json.dumps(result,sort_keys=True))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packs-dir',default='packs')
    parser.add_argument('--output',default='_site')
    args=parser.parse_args()
    try:run_build(args.packs_dir,args.output)
    except (ValueError,OSError,zipfile.BadZipFile) as error:
        parser.exit(1,'Build rejected: '+str(error)+'\n')


if __name__=='__main__':main()
