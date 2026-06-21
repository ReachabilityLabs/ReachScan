#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=json.load(open(ROOT/'release_assets/release_manifest.json'))
folder=Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd()
fail=[]
for p in manifest['products']:
    f=folder/p['file']
    if not f.exists():
        fail.append((p['file'],'missing')); continue
    h=hashlib.sha256()
    with f.open('rb') as stream:
        for b in iter(lambda:stream.read(1024*1024),b''): h.update(b)
    if h.hexdigest()!=p['sha256']: fail.append((p['file'],'sha256'))
print({'checked':len(manifest['products']),'failures':fail})
raise SystemExit(1 if fail else 0)
