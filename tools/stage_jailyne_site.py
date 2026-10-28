#!/usr/bin/env python3
"""Validate and stage only Jailyne's reviewed plain static files; no network/build deps."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import shutil
import stat
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'creator-sites/jailyneojeda/site'
MANIFEST = ROOT / 'creator-sites/jailyneojeda/manifest.json'
OUTPUT = ROOT / '_jailyne_site'
MANIFEST_SHA256 = '0a58d6e47ef6f1db7d32d155e2563dc7c285417827e508287c885fb1f47d8433'
EXPECTED_FILES = 143
EXPECTED_HTML = 56
HOST = 'https://jailyneojeda.pages.dev'

class InvalidRelease(Exception):
    pass

def check_path(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise InvalidRelease('Invalid release path.')
    p = PurePosixPath(value)
    if p.is_absolute() or p.as_posix() != value or any(x in ('', '.', '..') or x.startswith('.') for x in p.parts):
        raise InvalidRelease('Unsafe release path.')
    if p.name in ('_worker.js', '_routes.json') or 'functions' in p.parts:
        raise InvalidRelease('Server execution is not authorized in this static release.')
    return p

def validate(source, manifest):
    if source.is_symlink() or not source.is_dir() or manifest.is_symlink():
        raise InvalidRelease('Source/manifest must be ordinary checked-in files.')
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise InvalidRelease('Release manifest differs from the reviewed pin.')
    data = json.loads(raw)
    if data.get('requestedHost') != HOST or data.get('published') is not False:
        raise InvalidRelease('Unexpected release identity.')
    records = data.get('files')
    if not isinstance(records, list) or len(records) != EXPECTED_FILES:
        raise InvalidRelease('Unexpected release file count.')
    expected = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != {'path', 'bytes', 'sha256'}:
            raise InvalidRelease('Invalid release record.')
        key = check_path(record['path']).as_posix()
        if key in expected or type(record['bytes']) is not int or not 0 < record['bytes'] < 25_000_000:
            raise InvalidRelease('Duplicate path or invalid byte count.')
        if not isinstance(record['sha256'], str) or len(record['sha256']) != 64:
            raise InvalidRelease('Invalid SHA-256 record.')
        expected[key] = record
    if sum(n.endswith('.html') for n in expected) != EXPECTED_HTML:
        raise InvalidRelease('Unexpected route count.')
    actual = {}
    for directory, dirs, files in os.walk(source, followlinks=False):
        for name in dirs + files:
            p = Path(directory) / name
            if p.is_symlink():
                raise InvalidRelease('Symlinks are not permitted.')
            if not (p.is_dir() or stat.S_ISREG(p.lstat().st_mode)):
                raise InvalidRelease('Only ordinary static files are permitted.')
        for name in files:
            p = Path(directory) / name
            actual[p.relative_to(source).as_posix()] = p
    if set(actual) != set(expected):
        raise InvalidRelease('Missing or unreviewed source files.')
    for name, path in actual.items():
        raw = path.read_bytes()
        if len(raw) != expected[name]['bytes'] or hashlib.sha256(raw).hexdigest() != expected[name]['sha256']:
            raise InvalidRelease('Static-file bytes differ from the reviewed manifest: ' + name)
    return expected

def stage(source, manifest, output):
    records = validate(source, manifest)
    if output.exists() or output.is_symlink():
        raise InvalidRelease('Output already exists; refusing to overwrite it.')
    temp = Path(tempfile.mkdtemp(prefix='_jailyne_stage_', dir=output.parent))
    try:
        for name, record in records.items():
            target = temp / name
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = (source / name).read_bytes()
            if len(raw) != record['bytes'] or hashlib.sha256(raw).hexdigest() != record['sha256']:
                raise InvalidRelease('Source changed during staging.')
            target.write_bytes(raw)
        if output.exists() or output.is_symlink():
            raise InvalidRelease('Output appeared during staging; stopped.')
        temp.rename(output)
    except BaseException:
        # Remove only this helper's own new temporary output, never source or
        # another creator's directory.
        shutil.rmtree(temp)
        raise
    print(f'Validated and staged {len(records)} static files, {EXPECTED_HTML} HTML routes for {HOST}.')

if __name__ == '__main__':
    try:
        stage(SOURCE, MANIFEST, OUTPUT)
    except (InvalidRelease, OSError, ValueError, TypeError) as exc:
        raise SystemExit('Jailyne staging stopped: ' + str(exc)) from None
