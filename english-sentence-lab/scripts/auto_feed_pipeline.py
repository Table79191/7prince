#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'train')); sys.path.insert(0,str(ROOT/'scripts'))
import train_ud_role as base
from canonical_roles import canonicalize_ud, canonicalize_masc
import train_gold_ewt_masc_replay as masc_legacy

ALLOW_LICENSES={'CC-BY-4.0','CC-BY-SA-4.0','CC-BY-3.0','CC-BY-SA-3.0','CC0-1.0','MIT','PUBLIC-DOMAIN'}

def norm_text(s:str)->str:
    return re.sub(r'\s+',' ',s.strip().lower())

def split_of(text:str)->str:
    h=int(hashlib.sha1(norm_text(text).encode('utf-8')).hexdigest()[:8],16)%100
    return 'train' if h<85 else 'val'

def tree_hash(root:Path, pattern:str)->str:
    h=hashlib.sha256()
    for p in sorted(root.rglob(pattern)):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode()); h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()

def row_from_tokens(tokens, decisions, source, license_id, provenance, text):
    if any(d.role=='AMBIG' for d in decisions): return None
    toks=[]
    for t,d in zip(tokens,decisions):
        toks.append({'text':t.get('text',''),'pos':t.get('pos','UNK'),'role':d.role,'rule_id':d.rule_id})
    return {'text':text,'tokens':toks,'source':source,'license':license_id,'provenance':provenance}

def ingest_ud(path:Path, source, license_id, provenance):
    for f in sorted(path.rglob('*.conllu')):
        for meta,toks in base.parse_conllu(f):
            if not (2<=len(toks)<=160): continue
            text=meta.get('text') or ' '.join(t['text'] for t in toks)
            r=row_from_tokens(toks,canonicalize_ud(toks),source,license_id,provenance,text)
            if r is not None: yield r

def ingest_masc(path:Path, source, license_id, provenance):
    for f in sorted(path.rglob('*.conll')):
        if '__MACOSX' in f.parts: continue
        text=masc_legacy.decode_bytes(f.read_bytes()); lines=[]
        for raw in text.splitlines()+['']:
            if raw.strip(): lines.append(raw.rstrip('\r'))
            elif lines:
                toks,reason=masc_legacy.parse_masc_sentence(lines); lines=[]
                if toks is None: continue
                sent=' '.join(t['text'] for t in toks)
                r=row_from_tokens(toks,canonicalize_masc(toks),source,license_id,provenance,sent)
                if r is not None: yield r

def load_config(path:Path):
    cfg=json.loads(path.read_text(encoding='utf-8'))
    if 'sources' not in cfg or not isinstance(cfg['sources'],list): raise SystemExit('config.sources required')
    return cfg

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',required=True)
    ap.add_argument('--out-dir',default=str(ROOT/'data'/'auto_feed'))
    args=ap.parse_args()
    cfg=load_config(Path(args.config)); out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    stats=Counter(); seen={}; source_meta=[]
    for src in cfg['sources']:
        typ=src['type']; p=(ROOT/src['path']).resolve(); lic=src['license']; name=src['name']; prov=src.get('provenance','')
        if lic not in ALLOW_LICENSES: raise SystemExit(f'license not allowlisted: {name}: {lic}')
        if not p.exists(): raise SystemExit(f'missing source: {p}')
        digest=tree_hash(p,'*.conllu' if typ=='ud' else '*.conll')
        source_meta.append({'name':name,'type':typ,'path':str(p.relative_to(ROOT)),'license':lic,'sha256_tree':digest,'provenance':prov})
        rows=ingest_ud(p,name,lic,prov) if typ=='ud' else ingest_masc(p,name,lic,prov)
        for r in rows:
            stats['accepted_before_dedupe']+=1
            k=hashlib.sha1(norm_text(r['text']).encode('utf-8')).hexdigest()
            if k in seen:
                stats['duplicates_dropped']+=1
                continue
            r['id']=k; r['split']=split_of(r['text']); seen[k]=r; stats[r['split']]+=1
    train=[r for r in seen.values() if r['split']=='train']; val=[r for r in seen.values() if r['split']=='val']
    train.sort(key=lambda r:r['id']); val.sort(key=lambda r:r['id'])
    def write_jsonl(path,rows):
        with path.open('w',encoding='utf-8') as f:
            for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
    write_jsonl(out/'canonical_train.jsonl',train); write_jsonl(out/'canonical_val.jsonl',val)
    manifest={'version':'R012-AUTO-FEED-1','sources':source_meta,'stats':dict(stats),'train_rows':len(train),'val_rows':len(val),'dedupe':'sha1(normalized text)','split':'sha1(normalized text) % 100 < 85 => train','chaos50_used':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2,ensure_ascii=False))
if __name__=='__main__': main()
