#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from canonical_roles import canonicalize_ud, canonicalize_masc

CLAUSE_BOUNDARY = {"acl", "acl:relcl", "advcl", "ccomp", "xcomp", "parataxis"}
MASC_PROPAGATE = {"NMOD", "AMOD", "PMOD", "NAME", "TITLE"}
PTB_TO_UPOS = {
    "CC":"CCONJ","CD":"NUM","DT":"DET","EX":"PRON","FW":"X","IN":"ADP","JJ":"ADJ","JJR":"ADJ","JJS":"ADJ",
    "LS":"X","MD":"AUX","NN":"NOUN","NNS":"NOUN","NNP":"PROPN","NNPS":"PROPN","PDT":"DET","POS":"PART",
    "PRP":"PRON","PRP$":"DET","RB":"ADV","RBR":"ADV","RBS":"ADV","RP":"PART","SYM":"SYM","TO":"PART",
    "UH":"INTJ","WDT":"DET","WP":"PRON","WP$":"DET","WRB":"ADV",
    ".":"PUNCT",",":"PUNCT",":":"PUNCT","``":"PUNCT","''":"PUNCT","-LRB-":"PUNCT","-RRB-":"PUNCT",
}


def parse_conllu(path):
    sent=[]; meta={}
    def flush():
        nonlocal sent,meta
        if not sent: return None
        out=(meta,sent); sent=[]; meta={}; return out
    with open(path,encoding="utf-8") as f:
        for raw in f:
            line=raw.rstrip("\n")
            if not line:
                x=flush()
                if x: yield x
                continue
            if line.startswith("#"):
                if line.startswith("# text = "): meta["text"]=line[9:]
                elif line.startswith("# sent_id = "): meta["sent_id"]=line[12:]
                continue
            c=line.split("\t")
            if len(c)!=10 or "-" in c[0] or "." in c[0]: continue
            try: tid=int(c[0]); head=int(c[6])
            except ValueError: continue
            sent.append({"id":tid,"text":c[1],"lemma":c[2],"pos":c[3],"head":head,"deprel":c[7]})
    x=flush()
    if x: yield x


def legacy_ud_roles(tokens):
    id2i={t["id"]:i for i,t in enumerate(tokens)}; ch=defaultdict(list)
    for i,t in enumerate(tokens):
        if t["head"] in id2i: ch[id2i[t["head"]]].append(i)
    direct={}; cop_parents=set()
    for i,t in enumerate(tokens):
        base=t["deprel"].split(":",1)[0]
        if base in {"nsubj","csubj"}: direct[i]="S"
        elif base in {"obj","iobj"}: direct[i]="O"
        if base=="cop" and t["head"] in id2i: cop_parents.add(id2i[t["head"]])
    for i in cop_parents: direct[i]="C"
    for i,t in enumerate(tokens):
        if t["deprel"].split(":",1)[0]=="xcomp" and t["pos"] in {"ADJ","NOUN","PROPN","PRON","NUM"}: direct[i]="C"
    roles=[None]*len(tokens)
    for root,role in sorted(direct.items(),key=lambda kv:{"S":0,"O":1,"C":2}[kv[1]]):
        stack=[root]; seen=set()
        while stack:
            i=stack.pop()
            if i in seen: continue
            seen.add(i)
            if i!=root and i in direct: continue
            if roles[i] is None: roles[i]=role
            for j in ch.get(i,[]):
                rel=tokens[j]["deprel"]; base=rel.split(":",1)[0]
                if rel in CLAUSE_BOUNDARY or base in {"ccomp","xcomp","advcl","parataxis"}: continue
                stack.append(j)
    for i,t in enumerate(tokens):
        if t["pos"] in {"VERB","AUX"}: roles[i]="V"
    for i in cop_parents:
        if tokens[i]["pos"] not in {"VERB","AUX"}: roles[i]="C"
    for i,r in direct.items():
        if not (r=="C" and tokens[i]["pos"] in {"VERB","AUX"}): roles[i]=r
    for i,t in enumerate(tokens):
        if t["pos"]=="PUNCT": roles[i]=None
        elif roles[i] is None: roles[i]="M"
    return roles


def ptb_to_upos(tag, lemma):
    if tag.startswith("VB"):
        return "AUX" if lemma.lower()=="be" else "VERB"
    return PTB_TO_UPOS.get(tag,"X")


def decode_bytes(data):
    for enc in ("utf-8","cp1252","iso-8859-1"):
        try: return data.decode(enc)
        except UnicodeDecodeError: pass
    return data.decode("utf-8","replace")


def parse_masc_sentence(lines):
    toks=[]
    for line in lines:
        cols=line.split("\t")
        if len(cols)<10: return None
        try: tid=int(cols[0]); head=int(cols[8])
        except ValueError: return None
        form,lemma,gpos,split_form,deprel=cols[1],cols[2],cols[3],cols[5],cols[9]
        if gpos=="_" or form=="_" or split_form=="_" or form!=split_form: return None
        if gpos=="SU" and form=="/": continue
        toks.append({"id":tid,"text":form,"lemma":lemma,"gpos":gpos,"pos":ptb_to_upos(gpos,lemma),"head":head,"deprel":deprel})
    return toks if 2<=len(toks)<=160 else None


def legacy_masc_roles(tokens):
    id2i={t["id"]:i for i,t in enumerate(tokens)}
    children={i:[] for i in range(len(tokens))}
    for i,t in enumerate(tokens):
        if t["head"] in id2i: children[id2i[t["head"]]].append(i)
    direct={}
    for i,t in enumerate(tokens):
        rel=t["deprel"].upper()
        if rel=="SBJ": direct[i]="S"
        elif rel=="OBJ": direct[i]="O"
        elif rel in {"PRD","OPRD"}: direct[i]="C"
    roles=[None]*len(tokens)
    for root,role in direct.items():
        stack=[root]
        while stack:
            i=stack.pop()
            if roles[i] is None: roles[i]=role
            for j in children.get(i,[]):
                if j in direct and j!=root: continue
                if tokens[j]["deprel"].upper() in MASC_PROPAGATE and tokens[j]["pos"] not in {"VERB","AUX"}:
                    stack.append(j)
    for i,t in enumerate(tokens):
        if t["pos"] in {"VERB","AUX"}: roles[i]="V"
    for i,role in direct.items():
        if tokens[i]["pos"] not in {"VERB","AUX"}: roles[i]=role
    for i,t in enumerate(tokens):
        if t["pos"]=="PUNCT": roles[i]=None
        elif roles[i] is None: roles[i]="M"
    return roles


def compare_roles(tokens, legacy_roles, decisions, source, stats, examples, sent_name):
    for i,(tok,legacy,decision) in enumerate(zip(tokens,legacy_roles,decisions)):
        canon=decision.role
        stats["tokens"]+=1; stats["legacy"][str(legacy)]+=1; stats["canonical"][str(canon)]+=1
        stats["rules"][decision.rule_id]+=1; stats["review"][decision.review_status]+=1
        if canon=="AMBIG": stats["ambig"]+=1
        if legacy!=canon:
            stats["disagreements"]+=1; stats["matrix"][f"{legacy}->{canon}"]+=1
            if len(examples)<200:
                examples.append({"source":source,"sentence":sent_name,"index":i,"token":tok.get("text"),"pos":tok.get("pos"),"relation":tok.get("deprel"),"legacy":legacy,"canonical":canon,"rule_id":decision.rule_id,"review_status":decision.review_status})


def audit_ud(root,limit,stats,examples):
    seen=0
    for path in sorted(root.rglob("*.conllu")):
        for meta,toks in parse_conllu(path):
            if not 2<=len(toks)<=160: continue
            compare_roles(toks,legacy_ud_roles(toks),canonicalize_ud(toks),"ud",stats,examples,meta.get("sent_id") or meta.get("text") or path.name)
            seen+=1
            if limit and seen>=limit: return seen
    return seen


def iter_masc_sentences(root):
    for path in sorted(root.rglob("*.conll")):
        if "__MACOSX" in path.parts: continue
        text=decode_bytes(path.read_bytes()); lines=[]
        for raw in text.splitlines()+[""]:
            if raw.strip(): lines.append(raw.rstrip("\r"))
            elif lines:
                toks=parse_masc_sentence(lines); lines=[]
                if toks is not None: yield path,toks


def audit_masc(root,limit,stats,examples):
    seen=0
    for path,toks in iter_masc_sentences(root):
        compare_roles(toks,legacy_masc_roles(toks),canonicalize_masc(toks),"masc",stats,examples,path.name)
        seen+=1
        if limit and seen>=limit: break
    return seen


def empty_stats():
    return {"tokens":0,"disagreements":0,"ambig":0,"legacy":Counter(),"canonical":Counter(),"matrix":Counter(),"rules":Counter(),"review":Counter()}


def jsonable(s):
    return {"tokens":s["tokens"],"disagreements":s["disagreements"],"disagreement_rate":s["disagreements"]/s["tokens"] if s["tokens"] else 0.0,"ambig":s["ambig"],"ambig_rate":s["ambig"]/s["tokens"] if s["tokens"] else 0.0,"legacy":dict(s["legacy"]),"canonical":dict(s["canonical"]),"matrix":dict(s["matrix"].most_common()),"rules":dict(s["rules"].most_common()),"review":dict(s["review"].most_common())}


def main():
    ap=argparse.ArgumentParser(description="Audit legacy vs canonical S/V/O/C/M label alignment without ML dependencies.")
    ap.add_argument("--ud",default=str(ROOT/"data"/"ud")); ap.add_argument("--masc",default=str(ROOT/"data"/"gold_external"/"masc_conll"/"extracted"/"masc-conll"/"data"))
    ap.add_argument("--limit-per-source",type=int,default=0); ap.add_argument("--out",default=str(ROOT/"artifacts"/"label_alignment_audit.json")); args=ap.parse_args()
    us=empty_stats(); ms=empty_stats(); examples=[]
    un=audit_ud(Path(args.ud),args.limit_per_source,us,examples) if Path(args.ud).exists() else 0
    mn=audit_masc(Path(args.masc),args.limit_per_source,ms,examples) if Path(args.masc).exists() else 0
    payload={"spec":"docs/role_label_spec_v1.md","training_changed":False,"purpose":"diagnose label convention drift before canonical labels are allowed into training","sources":{"ud":{"sentences":un,**jsonable(us)},"masc":{"sentences":mn,**jsonable(ms)}},"sample_disagreements":examples}
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"ud_sentences":un,"ud_disagreement_rate":payload["sources"]["ud"]["disagreement_rate"],"masc_sentences":mn,"masc_disagreement_rate":payload["sources"]["masc"]["disagreement_rate"],"out":str(out)},indent=2))


if __name__=="__main__": main()
