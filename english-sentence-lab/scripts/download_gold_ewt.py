#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'gold_external' / 'ewt'
BASE = 'https://raw.githubusercontent.com/UniversalDependencies/UD_English-EWT/master/'
FILES = [
    'en_ewt-ud-train.conllu',
    'en_ewt-ud-dev.conllu',
    'en_ewt-ud-test.conllu',
    'LICENSE.txt',
    'README.md',
]

def fetch(name: str) -> bytes:
    req = urllib.request.Request(BASE + name, headers={'User-Agent':'SentenceLab-Gold-EWT/1.0'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def stats(data: bytes):
    text=data.decode('utf-8')
    s=t=0
    for line in text.splitlines():
        if line.startswith('# text = '): s+=1
        elif line and not line.startswith('#'):
            cols=line.split('\t')
            if cols and cols[0].isdigit(): t+=1
    return s,t

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest={
        'source':'UniversalDependencies/UD_English-EWT',
        'upstream':'https://github.com/UniversalDependencies/UD_English-EWT',
        'license':'CC BY-SA 4.0',
        'gold_dependency_annotations':True,
        'training_policy':'train split only; dev/test remain evaluation-only',
        'files':[],
    }
    for name in FILES:
        data=fetch(name)
        local='UPSTREAM_README.md' if name=='README.md' else name
        (OUT/local).write_bytes(data)
        rec={'name':local,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        if name.endswith('.conllu'):
            s,t=stats(data); rec.update(sentences=s,tokens=t)
            rec['split']='train' if '-train.' in name else ('dev' if '-dev.' in name else 'test')
        manifest['files'].append(rec)
        print(rec)
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__': main()
