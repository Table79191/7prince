#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html.parser
import json
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'gold_external' / 'masc_conll'
PAGE = 'https://anc.org/data/masc/downloads/data-download/'

class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.hrefs=[]
    def handle_starttag(self, tag, attrs):
        if tag.lower()=='a':
            for k,v in attrs:
                if k.lower()=='href' and v: self.hrefs.append(v)

def fetch(url: str) -> bytes:
    req=urllib.request.Request(url,headers={'User-Agent':'SentenceLab-MASC-inspector/1.0'})
    with urllib.request.urlopen(req,timeout=120) as r: return r.read()

def decode(data: bytes) -> tuple[str,str]:
    for enc in ('utf-8','cp1252','iso-8859-1'):
        try: return data.decode(enc),enc
        except UnicodeDecodeError: pass
    return data.decode('utf-8','replace'),'utf-8-replace'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    page=fetch(PAGE); text,_=decode(page); p=Links(); p.feed(text)
    candidates=[]
    for href in p.hrefs:
        absu=urllib.parse.urljoin(PAGE,href)
        if 'masc-conll' in absu.lower() and absu.lower().endswith('.zip'):
            candidates.append(absu)
    if not candidates:
        raise SystemExit('Could not locate masc-conll.zip link on official ANC download page')
    url=candidates[0]; raw=fetch(url)
    archive=OUT/'masc-conll.zip'; archive.write_bytes(raw)
    extract=OUT/'extracted'; extract.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z: z.extractall(extract)

    report={
        'source_page':PAGE,
        'download_url':url,
        'license':'Creative Commons Attribution 3.0 United States (per MASC official site)',
        'archive_bytes':len(raw),
        'archive_sha256':hashlib.sha256(raw).hexdigest(),
        'files':[],
        'column_count_histogram':{},
        'sample_rows':[],
    }
    hist=Counter()
    samples=[]
    for f in sorted(extract.rglob('*')):
        if not f.is_file(): continue
        data=f.read_bytes(); txt,enc=decode(data)
        info={'path':str(f.relative_to(extract)),'bytes':len(data),'encoding':enc,'sha256':hashlib.sha256(data).hexdigest()}
        nonblank=0
        for line in txt.splitlines():
            if not line.strip() or line.lstrip().startswith(('#','%')): continue
            cols=line.split('\t') if '\t' in line else line.split()
            if len(cols)>=2:
                hist[len(cols)]+=1; nonblank+=1
                if len(samples)<30: samples.append({'file':info['path'],'columns':len(cols),'row':cols[:20]})
        info['data_rows_seen']=nonblank
        report['files'].append(info)
    report['column_count_histogram']={str(k):v for k,v in sorted(hist.items())}
    report['sample_rows']=samples
    (OUT/'format_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'SOURCE.md').write_text(
        '# MASC-CONLL\n\nOfficial source: '+PAGE+'\n\n'+
        'MASC is distributed by the Open American National Corpus. The official MASC page states that it is available under the Creative Commons Attribution 3.0 United States License. '+
        'This directory contains the 40K MASC1 CoNLL package downloaded from the official data-download page.\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
