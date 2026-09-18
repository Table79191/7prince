#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, re, unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"train"))
import train_r012_safe_feed as safe

OUT=ROOT/"data"/"promoted_silver"
DATA=OUT/"promoted.jsonl"
STATE=OUT/"state.json"
MANIFEST=OUT/"manifest.json"
GATE_VERSION="PROMOTED-SILVER-1"
ALLOWED={"CC-BY-2.0-FR","CC-BY-SA-4.0","CC-BY-SA-3.0","CC-BY-4.0"}

def load_json(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return default

def iter_jsonl(path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip(): yield json.loads(line)

def source_specs():
    specs=[("tatoeba",ROOT/"data/external_corpus_bot/tatoeba/shards","tatoeba-*.jsonl"),\n           ("enwiki_bulk",ROOT/"data/external_corpus_bot/enwiki_bulk/shards","enwiki-bulk-*.jsonl")]
    mw=ROOT/"data/external_corpus_bot/mediawiki"
    if mw.exists():
        for d in sorted(x for x in mw.iterdir() if x.is_dir()):
            specs.append((f"mediawiki/{d.name}",d/"shards",f"{d.name}-*.jsonl"))
    return specs

def count_rows(folder,pattern):
    return sum(1 for p in sorted(folder.glob(pattern)) for _ in iter_jsonl(p)) if folder.exists() else 0

def blocked_texts():
    out=set()
    root=ROOT/"data/web_corpus_bot"
    for p in sorted(root.glob("*.jsonl")):
        for r in iter_jsonl(p):
            k=safe.norm_text(r.get("text",""))
            if k: out.add(k)
    return out

def fuzzy_key(text):
    s=unicodedata.normalize("NFKC",str(text)).lower().replace("’","'")
    return " ".join(re.findall(r"[a-z0-9]+(?:'[a-z]+)?",s))

def quality_ok(row):
    text=str(row.get("text",""))
    ana=row.get("analysis",{}); toks=ana.get("tokens",[])
    if len(text)<25 or len(text)>1200:return False,"quality_length"
    lo=text.lower()
    if any(x in lo for x in ("http://","https://","www.","{{","}}","[[","]]","<ref","</ref","{|","|}")):
        return False,"markup"
    if re.search(r"(.)\\1{5,}",text):return False,"repetition"
    if any(ord(ch)<32 and ch not in "\\t\\n\\r" for ch in text):return False,"control"
    ns=[ch for ch in text if not ch.isspace()]
    if not ns:return False,"empty"
    letters=sum(ch.isalpha() for ch in ns);digits=sum(ch.isdigit() for ch in ns)
    punct=len(ns)-letters-digits
    if letters/max(len(ns),1)<0.55:return False,"nonprose"
    if punct/max(len(ns),1)>0.26:return False,"punctuation"
    n=len(toks)
    ids=[int(t.get("id",0) or 0) for t in toks]
    heads=[int(t.get("head",0) or 0) for t in toks]
    if ids!=list(range(1,n+1)) or any(h<0 or h>n for h in heads) or sum(h==0 for h in heads)!=1:
        return False,"parser_integrity"
    return True,""

def basic_ok(row,benchmark_ids,blocked,seen,seen_fuzzy):
    ana=row.get("analysis",{}); toks=ana.get("tokens",[])
    src=row.get("source",{})
    if ana.get("status")!="auto_pass": return False,"status"
    if src.get("license") not in ALLOWED: return False,"license"
    if not (6<=len(toks)<=80): return False,"length"
    k=safe.norm_text(row.get("text",""))
    if not k or k in blocked or k in seen: return False,"duplicate"
    sid=int(src.get("sentence_id",0) or 0)
    if src.get("key")=="tatoeba" and sid in benchmark_ids: return False,"benchmark"
    roles=safe.current_school_roles(toks)
    if "AMBIG" in roles or "V" not in roles or not any(x in {"S","O","C"} for x in roles):
        return False,"structure"
    return True,""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--max-scan-per-source",type=int,default=4000)
    ap.add_argument("--max-accept-per-source",type=int,default=500)
    ap.add_argument("--bootstrap-tail",type=int,default=4000)
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        assert safe.norm_text(" A   B ")=="a b"
        print("promotion self-test: ok"); return

    import spacy
    nlp=spacy.load("en_core_web_sm")
    OUT.mkdir(parents=True,exist_ok=True)
    state=load_json(STATE,{"version":GATE_VERSION,"sources":{},"total_promoted":0})
    existing=list(iter_jsonl(DATA)) if DATA.exists() else []
    seen={safe.norm_text(x.get("text","")) for x in existing}
    blocked=blocked_texts()
    bench=safe.benchmark_ids(ROOT/"data/tatoeba500/TatoebaDaily500_CC0.tsv")
    added=[]; stats={}

    for key,folder,pattern in source_specs():
        total=count_rows(folder,pattern)
        prev=state["sources"].get(key)
        if prev is None:
            processed=max(0,total-a.bootstrap_tail)
        else:
            processed=min(int(prev.get("processed_records",0)),total)
        scanned=accepted=0; counts={}
        index=0
        stop=False
        for p in sorted(folder.glob(pattern)):
            for row in iter_jsonl(p):
                if index<processed:
                    index+=1; continue
                if scanned>=a.max_scan_per_source or accepted>=a.max_accept_per_source:
                    stop=True; break
                index+=1; scanned+=1
                ok,reason=basic_ok(row,bench,blocked,seen,seen_fuzzy)
                if not ok:
                    counts[reason]=counts.get(reason,0)+1; continue
                if not safe.strict_consensus(nlp,row):
                    counts["consensus"]=counts.get("consensus",0)+1; continue
                now=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                out=dict(row)
                out["promotion"]={
                    "status":"auto_promoted_silver",
                    "gate_version":GATE_VERSION,
                    "accepted_at_utc":now,
                    "checks":{
                        "source_auto_pass":True,
                        "spacy_stanza_strict_consensus":True,
                        "no_gold_or_dev_overlap":True,
                        "no_tatoeba500_overlap":True,
                    },
                }
                added.append(out); seen.add(safe.norm_text(out.get("text",""))); seen_fuzzy.add(fuzzy_key(out.get("text",""))); accepted+=1
            if stop: break
        state["sources"][key]={"processed_records":processed+scanned,"source_records_seen":total}
        stats[key]={"source_records":total,"processed_before":processed,"scanned":scanned,"accepted":accepted,"rejected":counts}

    if added:
        with DATA.open("a",encoding="utf-8",newline="\n") as f:
            for row in added:f.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
    state["version"]=GATE_VERSION
    state["total_promoted"]=len(existing)+len(added)
    state["updated_at_utc"]=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    STATE.write_text(json.dumps(state,indent=2)+"\n",encoding="utf-8")
    manifest={"version":GATE_VERSION,"added_this_run":len(added),"total_promoted":state["total_promoted"],"sources":stats,
              "policy":{"label_quality":"promoted_silver_not_gold","raw_external_never_directly_trained":True,
                        "requires_strict_spacy_stanza_consensus":True,"independent_test_excluded":True}}
    MANIFEST.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"added":len(added),"total":state["total_promoted"],"sources":stats},indent=2))

if __name__=="__main__": main()
