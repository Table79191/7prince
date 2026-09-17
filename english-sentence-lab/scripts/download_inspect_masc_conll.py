#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html.parser
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'gold_external' / 'masc_conll'
PAGE = 'https://anc.org/data/masc/downloads/data-download/'
EXPECTED_SHA1 = 'd9f53a05c659204a3223e901c450fe8ffa5fa9fa'  # DKPro MASC-CONLL artifact checksum

class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.hrefs=[]
    def handle_starttag(self, tag, attrs):
        if tag.lower()=='a':
            for k,v in attrs:
                if k.lower()=='href' and v: self.hrefs.append(v)

def _open(url: str, *, insecure: bool=False) -> bytes:
    req=urllib.request.Request(url,headers={'User-Agent':'SentenceLab-MASC-inspector/1.1'})
    context = ssl._create_unverified_context() if insecure else None
    with urllib.request.urlopen(req,timeout=120,context=context) as r: return r.read()

def fetch(url: str) -> tuple[bytes,bool]:
    try:
        return _open(url), False
    except urllib.error.URLError as e:
        reason = getattr(e, 'reason', None)
        # anc.org currently presents an expired TLS certificate to GitHub-hosted runners.
        # Fall back ONLY for anc.org; the archive itself is accepted only if its
        # published SHA1 matches EXPECTED_SHA1 exactly.
        host = urllib.parse.urlparse(url).hostname or ''
        if host.endswith('anc.org') and isinstance(reason, ssl.SSLCertVerificationError):
            return _open(url, insecure=True), True
        raise

def decode(data: bytes) -> tuple[str,str]:
    for enc in ('utf-8','cp1252','iso-8859-1'):
        try: return data.decode(enc),enc
        except UnicodeDecodeError: pass
    return data.decode('utf-8','replace'),'utf-8-replace'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    page,page_insecure=fetch(PAGE); text,_=decode(page); p=Links(); p.feed(text)
    candidates=[]
    for href in p.hrefs:
        absu=urllib.parse.urljoin(PAGE,href)
        if 'masc-conll' in absu.lower() and absu.lower().endswith('.zip'):
            candidates.append(absu)
    if not candidates:
        raise SystemExit('Could not locate masc-conll.zip link on official ANC download page')
    url=candidates[0]; raw,archive_insecure=fetch(url)
    sha1=hashlib.sha1(raw).hexdigest()
    if sha1 != EXPECTED_SHA1:
        raise SystemExit(f'MASC-CONLL SHA1 mismatch: {sha1} != {EXPECTED_SHA1}; refusing corpus')
    archive=OUT/'masc-conll.zip'; archive.write_bytes(raw)
    extract=OUT/'extracted'; extract.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z: z.extractall(extract)

    report={
        'source_page':PAGE,
        'download_url':url,
        'license':'MASC official site states distribution without license/restrictions; corpus documentation should be retained',
        'archive_bytes':len(raw),
        'archive_sha1':sha1,
        'expected_sha1':EXPECTED_SHA1,
        'archive_sha256':hashlib.sha256(raw).hexdigest(),
        'tls_fallback_used': bool(page_insecure or archive_insecure),
        'tls_fallback_reason':'anc.org expired certificate; exact published archive checksum required',
        'files':[],
        'column_count_histogram':{},
        'sample_rows':[],
    }
    hist=Counter(); samples=[]
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
        'This directory contains the 40K MASC1 CoNLL package from the Open American National Corpus site. '+
        'Because anc.org currently serves an expired TLS certificate to GitHub runners, the downloader permits an anc.org-only TLS fallback but rejects the archive unless SHA1 '+EXPECTED_SHA1+' matches the published DKPro artifact checksum exactly.\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
