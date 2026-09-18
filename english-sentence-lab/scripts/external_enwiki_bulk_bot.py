#!/usr/bin/env python3
"""High-throughput English Wikipedia sentence collector for SentenceLab.

Design goals:
- maximize *new* sentence yield rather than re-scan one sequential page range;
- never write promoted_silver directly;
- write only to data/external_corpus_bot/enwiki_bulk;
- reject obvious markup/noise/broken parses before storing;
- preserve attribution metadata for every sentence;
- let the central promotion gate do global gold/promoted dedupe + spaCy/Stanza consensus.

The collector samples random namespace-0 English Wikipedia pages through MediaWiki
API, parses paragraphs with Stanza, and stores only structurally sane auto-pass
sentences in append-only shards.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import time
import unicodedata
import urllib.parse
import urllib.request

import auto_web_corpus_bot as legacy
from canonical_roles import canonicalize_ud

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"external_corpus_bot"/"enwiki_bulk"
SHARDS=OUT/"shards"
STATE=OUT/"state.json"
MANIFEST=OUT/"manifest.json"
REPORT=OUT/"REPORT.md"

API="https://en.wikipedia.org/w/api.php"
PROJECT="https://en.wikipedia.org/"
PROVIDER="English Wikipedia bulk random sampler"
LICENSE="CC-BY-SA-4.0"
LICENSE_URL="https://creativecommons.org/licenses/by-sa/4.0/"
USER_AGENT="SentenceLab-EnwikiBulkBot/1.0 (+https://github.com/Table79191/7prince)"
SHARD_SIZE=2500
BATCH_PAGES=20

SPACE_RE=re.compile(r"\s+")
WORD_RE=re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)?|\d+")
REPEAT_RE=re.compile(r"(.)\1{5,}")
BAD_FRAGMENTS=(
    "http://","https://","www.","{{","}}","[[","]]","<ref","</ref",
    "<table","</table","{|","|}","isbn ","doi:","category:","file:","image:",
)

def now_pair():
    utc=datetime.now(timezone.utc).replace(microsecond=0)
    kst=utc.astimezone(timezone(timedelta(hours=9)))
    return utc.isoformat(),kst.isoformat()

def load_json(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return dict(default)

def dump_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def request_json(params,retries=7):
    q=dict(params);q["format"]="json";q["formatversion"]="2"
    url=API+"?"+urllib.parse.urlencode(q)
    last=None
    for attempt in range(retries):
        req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:
            last=exc
            if attempt+1>=retries:break
            delay=min(45,2**attempt)
            code=getattr(exc,"code",None)
            if code==429:
                try:delay=max(delay,int(getattr(exc,"headers",{}).get("Retry-After","0") or 0))
                except Exception:pass
            time.sleep(delay)
    raise RuntimeError(f"MediaWiki API failed after retries: {last}")

def fetch_random_pages(limit=BATCH_PAGES):
    data=request_json({
        "action":"query",
        "generator":"random",
        "grnnamespace":0,
        "grnlimit":max(1,min(int(limit),20)),
        "prop":"extracts|info|revisions",
        "explaintext":1,
        "exsectionformat":"plain",
        "inprop":"url",
        "rvprop":"ids|timestamp",
        "rvslots":"main",
    })
    pages=data.get("query",{}).get("pages",[])
    out=[]
    for p in pages:
        if p.get("missing"):continue
        text=str(p.get("extract","") or "").strip()
        if not text:continue
        revs=p.get("revisions",[]) or []
        rev=revs[0] if revs else {}
        out.append({
            "pageid":int(p.get("pageid",0) or 0),
            "title":str(p.get("title","")),
            "url":str(p.get("fullurl","")),
            "revision_id":int(rev.get("revid",0) or 0),
            "revision_timestamp":str(rev.get("timestamp","")),
            "extract":text,
        })
    return out

def norm_text(text):
    text=unicodedata.normalize("NFKC",str(text))
    text=SPACE_RE.sub(" ",text).strip()
    return text

def dedupe_key(text):
    text=norm_text(text).lower().replace("’","'")
    return " ".join(WORD_RE.findall(text))

def rough_quality(text):
    s=norm_text(text)
    if not (25<=len(s)<=900):return False,"char_length"
    lo=s.lower()
    if any(x in lo for x in BAD_FRAGMENTS):return False,"markup"
    if REPEAT_RE.search(s):return False,"repetition"
    if any(ord(ch)<32 and ch not in "\t\n\r" for ch in s):return False,"control"
    nonspace=[c for c in s if not c.isspace()]
    if not nonspace:return False,"empty"
    letters=sum(c.isalpha() for c in nonspace)
    digits=sum(c.isdigit() for c in nonspace)
    punct=len(nonspace)-letters-digits
    if letters/max(len(nonspace),1)<0.58:return False,"nonprose"
    if punct/max(len(nonspace),1)>0.24:return False,"punctuation"
    words=WORD_RE.findall(s)
    if not (6<=len(words)<=100):return False,"word_length"
    if sum(1 for w in words if len(w)>35)>0:return False,"long_token"
    if s.count("|") or s.count("=")>=2:return False,"markup"
    return True,""

def paragraph_ok(text):
    s=norm_text(text)
    if not (40<=len(s)<=5000):return False,"paragraph_length"
    lo=s.lower()
    if any(x in lo for x in ("{{","}}","[[","]]","<ref","</ref","<table","</table","{|","|}")):
        return False,"markup"
    if any(ord(ch)<32 and ch not in "\t\n\r" for ch in s):return False,"control"
    ns=[ch for ch in s if not ch.isspace()]
    if not ns:return False,"empty"
    letters=sum(ch.isalpha() for ch in ns)
    if letters/max(len(ns),1)<0.45:return False,"nonprose"
    return True,""

def stanza_sentence_tokens(sent):
    toks=[]
    for w in sent.words:
        toks.append({
            "id":int(w.id),
            "text":w.text,
            "lemma":w.lemma or "",
            "pos":w.upos or "",
            "xpos":w.xpos or "",
            "feats":w.feats or "",
            "head":int(w.head or 0),
            "deprel":w.deprel or "dep",
            "deps":"",
            "misc":"",
        })
    return toks

def parser_integrity(tokens):
    n=len(tokens)
    if not (6<=n<=100):return False
    ids=[int(t.get("id",0) or 0) for t in tokens]
    if ids!=list(range(1,n+1)):return False
    heads=[int(t.get("head",0) or 0) for t in tokens]
    if any(h<0 or h>n for h in heads):return False
    if sum(h==0 for h in heads)!=1:return False
    if not any(t.get("pos") in {"VERB","AUX"} for t in tokens):return False
    return True

def make_record(page,text,tokens):
    decisions=canonicalize_ud(tokens)
    if any(d.role=="AMBIG" or d.review_status!="auto_pass" for d in decisions):
        return None
    roles=[d.role for d in decisions]
    if "V" not in roles or not any(x in {"S","O","C"} for x in roles):
        return None
    analyzed=[]
    counts=Counter()
    for token,d in zip(tokens,decisions):
        row=dict(token)
        row["role"]=d.role
        row["role_rule"]=d.rule_id
        row["review_status"]=d.review_status
        analyzed.append(row)
        if d.role:counts[d.role]+=1
    basis=f'enwiki_bulk\n{page["pageid"]}\n{page["revision_id"]}\n{dedupe_key(text)}'
    rid=hashlib.sha256(basis.encode()).hexdigest()
    utc,kst=now_pair()
    return {
      "id":rid,
      "text":norm_text(text),
      "analysis":{
        "format":"Stanza-UD + SentenceLab-canonical-roles",
        "label_quality":"weak_parser_generated",
        "status":"auto_pass",
        "role_counts":dict(sorted(counts.items())),
        "grammar_features":legacy.grammar_features(tokens),
        "tokens":analyzed,
      },
      "source":{
        "key":"enwiki_bulk",
        "provider":PROVIDER,
        "pageid":page["pageid"],
        "title":page["title"],
        "revision_id":page["revision_id"],
        "revision_timestamp":page["revision_timestamp"],
        "upstream":page["url"],
        "project_url":PROJECT,
        "api":API,
        "license":LICENSE,
        "license_url":LICENSE_URL,
      },
      "collection":{"first_collected_at_utc":utc,"first_collected_at_kst":kst},
      "content_sha256":hashlib.sha256(norm_text(text).encode()).hexdigest(),
      "dedupe_sha256":hashlib.sha256(dedupe_key(text).encode()).hexdigest(),
    }

class ShardWriter:
    def __init__(self,state):
        SHARDS.mkdir(parents=True,exist_ok=True)
        self.index=max(1,int(state.get("current_shard",1) or 1))
        self.count=max(0,int(state.get("current_shard_records",0) or 0))
        if self.count>SHARD_SIZE:self.count=0
    def path(self):return SHARDS/f"enwiki-bulk-{self.index:06d}.jsonl"
    def write(self,row):
        if self.count>=SHARD_SIZE:
            self.index+=1;self.count=0
        with self.path().open("a",encoding="utf-8",newline="\n") as f:
            f.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
        self.count+=1

def load_recent_dedupe(max_rows=50000):
    seen=set()
    paths=sorted(SHARDS.glob("enwiki-bulk-*.jsonl"),reverse=True)
    n=0
    for p in paths:
        rows=p.read_text(encoding="utf-8").splitlines()
        for line in reversed(rows):
            if not line.strip():continue
            try:r=json.loads(line)
            except Exception:continue
            k=r.get("dedupe_sha256")
            if not k:k=hashlib.sha256(dedupe_key(r.get("text","")).encode()).hexdigest()
            seen.add(k);n+=1
            if n>=max_rows:return seen
    return seen

def iter_paragraphs(text):
    for p in re.split(r"\n\s*\n+",text):
        p=norm_text(p)
        if 40<=len(p)<=5000:
            yield p
        elif len(p)>5000:
            # Avoid giant parser inputs while preserving prose.
            for chunk in re.split(r"(?<=[.!?])\s+",p):
                chunk=norm_text(chunk)
                if 40<=len(chunk)<=1200:yield chunk

def self_test():
    good="The engineer checked the system carefully before the team started the experiment."
    bad="== References == http://example.com"
    assert rough_quality(good)[0]
    assert not rough_quality(bad)[0]
    assert paragraph_ok((good+" ")*20)[0]
    assert dedupe_key("Hello,  WORLD!")=="hello world"
    toks=[
      {"id":1,"text":"Students","lemma":"student","pos":"NOUN","head":2,"deprel":"nsubj"},
      {"id":2,"text":"learn","lemma":"learn","pos":"VERB","head":0,"deprel":"root"},
      {"id":3,"text":"English","lemma":"English","pos":"PROPN","head":2,"deprel":"obj"},
      {"id":4,"text":"very","lemma":"very","pos":"ADV","head":5,"deprel":"advmod"},
      {"id":5,"text":"quickly","lemma":"quickly","pos":"ADV","head":2,"deprel":"advmod"},
      {"id":6,"text":".","lemma":".","pos":"PUNCT","head":2,"deprel":"punct"},
    ]
    assert parser_integrity(toks)
    print("enwiki bulk collector self-test: ok")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--runtime-seconds",type=int,default=1200)
    ap.add_argument("--max-pages",type=int,default=0,help="0 = unlimited until wall clock")
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:self_test();return
    if a.runtime_seconds<0 or a.max_pages<0:raise SystemExit("invalid negative limit")
    try:import stanza
    except ImportError as e:raise SystemExit("stanza required") from e

    OUT.mkdir(parents=True,exist_ok=True)
    state=load_json(STATE,{
      "total_records":0,"pages_sampled":0,"current_shard":1,"current_shard_records":0,
      "rejected":{},
    })
    writer=ShardWriter(state)
    seen=load_recent_dedupe()
    nlp=stanza.Pipeline("en",processors="tokenize,pos,lemma,depparse",use_gpu=False,verbose=False)

    started=time.monotonic();added=0;pages=0
    rej=Counter();page_seen=set()
    while True:
        if a.runtime_seconds and time.monotonic()-started>=a.runtime_seconds:break
        if a.max_pages and pages>=a.max_pages:break
        batch=fetch_random_pages(BATCH_PAGES)
        if not batch:
            time.sleep(2);continue
        for page in batch:
            if a.runtime_seconds and time.monotonic()-started>=a.runtime_seconds:break
            if a.max_pages and pages>=a.max_pages:break
            pid=page["pageid"]
            if not pid or pid in page_seen:
                rej["page_duplicate"]+=1;continue
            page_seen.add(pid);pages+=1
            for para in iter_paragraphs(page["extract"]):
                if a.runtime_seconds and time.monotonic()-started>=a.runtime_seconds:break
                ok,reason=paragraph_ok(para)
                if not ok:
                    rej[reason]+=1;continue
                try:doc=nlp(para)
                except Exception:
                    rej["parser_error"]+=1;continue
                for sent in doc.sentences:
                    text=norm_text(sent.text)
                    ok,reason=rough_quality(text)
                    if not ok:
                        rej[reason]+=1;continue
                    key=hashlib.sha256(dedupe_key(text).encode()).hexdigest()
                    if key in seen:
                        rej["duplicate"]+=1;continue
                    toks=stanza_sentence_tokens(sent)
                    if not parser_integrity(toks):
                        rej["parser_integrity"]+=1;continue
                    row=make_record(page,text,toks)
                    if row is None:
                        rej["canonical"]+=1;continue
                    seen.add(key);writer.write(row);added+=1

    state.update({
      "total_records":int(state.get("total_records",0))+added,
      "pages_sampled":int(state.get("pages_sampled",0))+pages,
      "current_shard":writer.index,
      "current_shard_records":writer.count,
      "last_run_added":added,
      "last_run_pages":pages,
      "updated_at_utc":now_pair()[0],
    })
    cumulative=Counter(state.get("rejected",{}));cumulative.update(rej)
    state["rejected"]=dict(cumulative)
    dump_json(STATE,state)
    manifest={
      "version":"SENTENCELAB-ENWIKI-BULK-1",
      "provider":PROVIDER,"api":API,"license":LICENSE,"license_url":LICENSE_URL,
      "total_records":state["total_records"],"pages_sampled":state["pages_sampled"],
      "added_this_run":added,"pages_this_run":pages,"rejected_this_run":dict(rej),
      "shard_count":writer.index,
      "policy":{
        "total_sentence_limit":0,
        "per_run_sentence_limit":0,
        "runtime_checkpoint_seconds":a.runtime_seconds,
        "writes_promoted_silver":False,
        "isolated_output_directory":True,
        "local_exact_and_punctuation_insensitive_dedupe":True,
        "parser_integrity_required":True,
        "canonical_auto_pass_required":True,
        "central_promotion_gate_required":True,
      },
    }
    dump_json(MANIFEST,manifest)
    REPORT.write_text(
      "# SentenceLab enwiki bulk collector\n\n"
      f"- total accepted local records: {state['total_records']}\n"
      f"- total pages sampled: {state['pages_sampled']}\n"
      f"- added this run: {added}\n"
      f"- rejected this run: {dict(rej)}\n\n"
      "This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.\n",
      encoding="utf-8")
    print(json.dumps({"added":added,"pages":pages,"total":state["total_records"],"rejected":dict(rej)},ensure_ascii=False))

if __name__=="__main__":main()
