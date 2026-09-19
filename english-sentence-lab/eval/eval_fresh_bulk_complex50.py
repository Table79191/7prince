#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, re, sys, unicodedata
from collections import Counter
from pathlib import Path
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"arena"))
sys.path.insert(0,str(ROOT/"train"))
sys.path.insert(0,str(ROOT/"experiments/clause_anchor_graph_v1_01"))

import run_model_arena as arena
import train_ud_role as rbase
import model as cmodel
sys.path.insert(0,str(ROOT/"scripts"))
from promoted_shards import iter_promoted

TEST_VERSION="FRESH-BULK-COMPLEX50-20260919-V2"
CLAUSE_DEPS={"acl","acl:relcl","advcl","ccomp","xcomp","parataxis"}
REL_WORDS={"who","whom","whose","which","that","where","when"}
SUB_WORDS={"although","though","because","while","whilst","when","if","unless","before","after","until","since","whereas","once","whether"}
WH_WORDS={"what","which","who","whom","whose","where","when","why","how"}
CORE={"S","V","O","C"}

def iter_jsonl(path):
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def norm(text):
    return re.sub(r"\s+"," ",str(text).strip().lower())

def fuzzy(text):
    s=unicodedata.normalize("NFKC",str(text)).lower().replace("’","'")
    return " ".join(re.findall(r"[a-z0-9]+(?:'[a-z]+)?",s))

def promoted_block():
    p=ROOT/"data/promoted_silver/promoted.jsonl"
    exact=set(); fuzz=set(); norm_sha1=set()
    if p.exists():
        for row in iter_promoted(p):
            e=norm(row.get("text","")); f=fuzzy(row.get("text",""))
            if e:
                exact.add(e)
                import hashlib
                norm_sha1.add(hashlib.sha1(e.encode("utf-8")).hexdigest())
            if f: fuzz.add(f)
    else:
        # Sparse eval checkout deliberately avoids the >200 MB promoted.jsonl.
        # Arena feed_state contains SHA1(norm(text)) for promoted rows already seen
        # by the battle loop and provides an additional cross-source overlap block.
        fp=ROOT/"artifacts/arena_hotfeed/feed_state.json"
        if fp.exists():
            try:
                state=json.loads(fp.read_text(encoding="utf-8"))
                norm_sha1.update(state.get("consumed_promoted_keys",[]))
            except Exception:
                pass
    return exact,fuzz,norm_sha1

def max_dep_depth(tokens):
    heads={int(t.get("id",0) or 0):int(t.get("head",0) or 0) for t in tokens}
    best=0
    for start in heads:
        seen=set(); cur=start; depth=0
        while cur and cur in heads and cur not in seen and depth<200:
            seen.add(cur);cur=heads[cur];depth+=1
        best=max(best,depth)
    return best

def complexity(row):
    toks=row.get("analysis",{}).get("tokens",[])
    n=len(toks)
    deps=[str(t.get("deprel","")) for t in toks]
    words=[str(t.get("text","")).lower() for t in toks]
    pos=[str(t.get("pos","")) for t in toks]
    base_clauses=sum(d in CLAUSE_DEPS or d.startswith("acl:") for d in deps)
    verbal_conj=sum(d=="conj" and p in {"VERB","AUX"} for d,p in zip(deps,pos))
    nominal_conj=sum(d=="conj" and p in {"NOUN","PROPN","ADJ","NUM"} for d,p in zip(deps,pos))
    clauses=base_clauses+verbal_conj
    rel=sum(d=="acl:relcl" for d in deps)+sum(w in REL_WORDS for w in words)
    comps=sum(d in {"ccomp","xcomp"} for d in deps)
    advcl=sum(d=="advcl" for d in deps)
    verbs=sum(p in {"VERB","AUX"} for p in pos)
    conjs=verbal_conj
    subs=sum(w in SUB_WORDS for w in words)
    wh=sum(w in WH_WORDS for w in words)
    punct=sum(w in {",",";",":","—","-"} for w in words)
    depth=max_dep_depth(toks)
    # Structural-only ranking. No model prediction is consulted.
    score=(0.060*min(n,100)+3.0*clauses+1.5*rel+1.45*comps+1.25*advcl+
           0.65*max(0,verbs-2)+0.85*conjs+0.65*subs+0.40*wh+
           0.15*min(punct,6)+0.60*max(0,depth-5)-0.90*nominal_conj-
           0.35*max(0,punct-8))
    return {
      "score":score,"tokens":n,"clauses":clauses,"relative":rel,"complements":comps,
      "advcl":advcl,"verbs":verbs,"verbal_conj":verbal_conj,
      "nominal_conj":nominal_conj,"subordinators":subs,
      "wh":wh,"punct":punct,"dep_depth":depth,
    }

def natural_complex_prose(row,comp):
    text=str(row.get("text","")).strip()
    toks=row.get("analysis",{}).get("tokens",[])
    words=[str(t.get("text","")) for t in toks]
    pos=[str(t.get("pos","")) for t in toks]
    deps=[str(t.get("deprel","")) for t in toks]
    if not text:
        return False
    # reject catalogues, credits, headings, metadata-like prose
    comma_count=text.count(",")
    colon_count=text.count(":")
    dash_count=text.count(" – ")+text.count(" — ")
    semis=text.count(";")
    if comma_count>10 or colon_count>3 or dash_count>5:
        return False
    if comma_count/max(len(toks),1) > 0.16:
        return False
    if text.count(" – ")>=3:
        return False
    if re.search(r"\b(songwriting|production|engineering|mastering|programming|vocals)\b",text,re.I) and comma_count>=5:
        return False
    if re.search(r"offers the following|the following .*:",text,re.I) and comma_count>=5:
        return False
    # Require real clausal complexity, not coordination of list items.
    if comp["clauses"]<3:
        return False
    if comp["verbs"]<4:
        return False
    if comp["complements"]+comp["advcl"]+comp["relative"] < 2:
        return False
    if sum(d in {"nsubj","csubj","nsubj:pass"} for d in deps) < 2:
        return False
    if sum(p in {"NOUN","PROPN","PRON"} for p in pos) < 4:
        return False
    # A complex sentence should have a finite-looking sentence ending.
    if text[-1] not in ".!?\"'”’":
        return False
    return True

def candidate_rows(max_scan):
    state=json.loads((ROOT/"data/promoted_silver/state.json").read_text(encoding="utf-8"))
    processed=int(state.get("sources",{}).get("enwiki_bulk",{}).get("processed_records",0))
    exact,fuzz,norm_sha1=promoted_block()
    rows=[]; index=0; scanned=0
    shards=sorted((ROOT/"data/external_corpus_bot/enwiki_bulk/shards").glob("enwiki-bulk-*.jsonl"))
    # In a tail-only sparse checkout, every included shard is far beyond the
    # source's promoted processed frontier, so source-local skip must be zero.
    sparse_tail=bool(shards and not shards[0].name.endswith("000001.jsonl"))
    source_skip=0 if sparse_tail else processed
    for p in shards:
        for row in iter_jsonl(p):
            if index<source_skip:
                index+=1;continue
            index+=1
            if scanned>=max_scan:
                return processed,index-processed,rows
            scanned+=1
            if row.get("analysis",{}).get("status")!="auto_pass":
                continue
            text=row.get("text","")
            e=norm(text); f=fuzzy(text)
            import hashlib
            h=hashlib.sha1(e.encode("utf-8")).hexdigest() if e else ""
            if not e or e in exact or (f and f in fuzz) or (h and h in norm_sha1):
                continue
            toks=row.get("analysis",{}).get("tokens",[])
            if not (24<=len(toks)<=100):
                continue
            comp=complexity(row)
            # Require genuinely multi-clausal structure.
            if comp["clauses"]<3 or comp["verbs"]<4 or comp["dep_depth"]<6:
                continue
            if comp["nominal_conj"]>=5 and comp["clauses"]<5:
                continue
            roles=arena.canonical_roles(row)
            if roles is None or not all(r in {None,"S","V","O","C","M"} for r in roles):
                continue
            rows.append((comp["score"],comp,row))
    return processed,scanned,rows

def score_predictions(recs,preds):
    full=core=full_ok=core_ok=exact=0
    per=Counter()
    for rec,pred in zip(recs,preds):
        gold=arena.canonical_roles(rec["row"])
        sent_ok=True
        for g,q in zip(gold,pred):
            full+=1;full_ok+=int(g==q);sent_ok &= (g==q)
            per[(g,"n")]+=1;per[(g,"ok")]+=int(g==q)
            if g in CORE:
                core+=1;core_ok+=int(g==q)
        exact+=int(sent_ok)
    return {
      "sentences":len(recs),
      "tokens":full,
      "full_role_accuracy":full_ok/max(full,1),
      "core_role_accuracy":core_ok/max(core,1),
      "sentence_exact":exact,
      "sentence_exact_rate":exact/max(len(recs),1),
      "per_gold_role_accuracy":{
        str(k):per[(k,"ok")]/max(per[(k,"n")],1)
        for k in [None,"S","V","O","C","M"]
      },
      "per_gold_role_count":{str(k):per[(k,"n")] for k in [None,"S","V","O","C","M"]},
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--role-model",default="artifacts/arena_hotfeed/role_arena_latest.pt")
    ap.add_argument("--clause-model",default="artifacts/arena_hotfeed/clause_arena_latest.pt")
    ap.add_argument("--count",type=int,default=50)
    ap.add_argument("--max-scan",type=int,default=30000)
    ap.add_argument("--dataset-out",default="data/eval/fresh_bulk_complex50_20260919.json")
    ap.add_argument("--result-out",default="artifacts/fresh_bulk_complex50_20260919_results.json")
    a=ap.parse_args()
    torch.set_num_threads(4)
    device=torch.device("cpu")

    processed,scanned,cands=candidate_rows(a.max_scan)
    cands.sort(key=lambda x:(x[0],x[2].get("id","")),reverse=True)
    chosen=cands[:a.count]
    if len(chosen)<a.count:
        raise SystemExit(f"only {len(chosen)} qualifying unseen complex rows found")

    recs=[{"row":row,"kind":"eval","weight":1.0} for _,_,row in chosen]
    dataset={
      "version":TEST_VERSION,
      "training_allowed":False,
      "selection_uses_model_predictions":False,
      "source":"enwiki_bulk rows strictly after current promoted processed_records",
      "promoted_processed_records_at_selection":processed,
      "candidate_rows_scanned":scanned,
      "selected_count":len(chosen),
      "cases":[
        {
          "id":row.get("id"),"text":row.get("text"),
          "source":{"pageid":row.get("source",{}).get("pageid"),"title":row.get("source",{}).get("title")},
          "complexity":comp,
          "tokens":[t.get("text") for t in row.get("analysis",{}).get("tokens",[])],
          "pos":[t.get("pos") for t in row.get("analysis",{}).get("tokens",[])],
          "gold_roles":arena.canonical_roles(row),
        }
        for _,comp,row in chosen
      ],
    }

    rck=torch.load(ROOT/a.role_model,map_location="cpu",weights_only=False)
    cck=torch.load(ROOT/a.clause_model,map_location="cpu",weights_only=False)
    role=rbase.RoleNet().to(device);role.load_state_dict(rck["model"],strict=True)
    clause=cmodel.ClauseAnchorGraph().to(device);clause.load_state_dict(cck["model"],strict=True)

    rp=arena.role_predict(role,recs,device)
    cp=arena.clause_predict(clause,recs,device)
    rm=score_predictions(recs,rp);cm=score_predictions(recs,cp)

    wins=Counter();cases=[]
    for (_,comp,row),pr,pc in zip(chosen,rp,cp):
        gold=arena.canonical_roles(row)
        er,_=arena.weighted_errors(gold,pr);ec,_=arena.weighted_errors(gold,pc)
        if er<ec:w="role";wins["role"]+=1
        elif ec<er:w="clause";wins["clause"]+=1
        else:w="tie";wins["tie"]+=1
        cases.append({
          "id":row.get("id"),"text":row.get("text"),"complexity":comp,
          "winner":w,"role_weighted_error":er,"clause_weighted_error":ec,
          "gold":gold,"role_pred":pr,"clause_pred":pc,
        })

    result={
      "version":TEST_VERSION,
      "training_allowed":False,
      "models":{
        "role_checkpoint":a.role_model,
        "role_version":rck.get("config",{}).get("version",rck.get("metrics",{}).get("version","unknown")),
        "clause_checkpoint":a.clause_model,
        "clause_version":cck.get("config",{}).get("version",cck.get("metrics",{}).get("version","unknown")),
      },
      "selection":{
        "promoted_processed_records_at_selection":processed,
        "candidate_rows_scanned":scanned,"qualifying_candidates":len(cands),
        "selected":len(chosen),"model_blind":True,
      },
      "role":rm,"clause":cm,
      "sentence_wins":dict(wins),
      "cases":cases,
    }
    d=ROOT/a.dataset_out;r=ROOT/a.result_out
    d.parent.mkdir(parents=True,exist_ok=True);r.parent.mkdir(parents=True,exist_ok=True)
    d.write_text(json.dumps(dataset,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    r.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
      "version":TEST_VERSION,
      "selection":result["selection"],
      "role":rm,
      "clause":cm,
      "sentence_wins":dict(wins),
      "top5":[{"text":x[2].get("text"),"complexity":x[1]["score"]} for x in chosen[:5]],
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
