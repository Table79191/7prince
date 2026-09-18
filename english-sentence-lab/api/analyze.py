from http.server import BaseHTTPRequestHandler
import json, math, re
from pathlib import Path

import numpy as np
import onnxruntime as ort
import spacy

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "web" / "r012" / "r012_role.onnx"

POS_LIST = ['UNK','ADJ','ADP','ADV','AUX','CCONJ','DET','INTJ','NOUN','NUM','PART','PRON','PROPN','PUNCT','SCONJ','SYM','VERB','X']
POS2I = {x:i for i,x in enumerate(POS_LIST)}
I2ROLE = [None,'S','V','O','C','M']
ROLE2I = {'S':1,'V':2,'O':3,'C':4,'M':5}

NLP = spacy.load("en_core_web_sm")
SESSION = ort.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])

def fnv1a(s: str) -> int:
    h = 2166136261
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 16777619) & 0xffffffff
    return h

def weak_roles(tokens):
    out=[]; seen_pred=False
    for t in tokens:
        p=t.pos_
        if p in {"VERB","AUX"}:
            out.append("V"); seen_pred=True
        elif p=="PUNCT":
            out.append(None)
        elif p in {"NOUN","PROPN","PRON"}:
            out.append("S" if not seen_pred else "O")
        else:
            out.append("M")
    return out

def shape_feat(w: str):
    lo=w.lower()
    return [
        float(bool(w[:1].isupper())),
        float(w.isupper() and any(c.isalpha() for c in w)),
        float(any(c.isdigit() for c in w)),
        float("-" in w),
        float(lo.endswith("ing")),
        float(lo.endswith("ed")),
        float(lo.endswith("ly")),
        min(len(w),20)/20.0,
    ]

def model_roles(doc):
    toks=list(doc)
    weak=weak_roles(toks)
    wid=[]; pre=[]; suf=[]; pos=[]; role=[]; shape=[]
    for t,b in zip(toks,weak):
        w=t.text; lo=w.lower()
        wid.append(fnv1a(lo)%8192)
        pre.append(fnv1a(lo[:3])%1024)
        suf.append(fnv1a(lo[-3:])%1024)
        pos.append(POS2I.get(t.pos_,0))
        role.append(0 if b is None else ROLE2I.get(b,0))
        shape.append(shape_feat(w))
    L=len(toks)
    feeds={
        "wid":np.asarray([wid],dtype=np.int64),
        "pre":np.asarray([pre],dtype=np.int64),
        "suf":np.asarray([suf],dtype=np.int64),
        "pos":np.asarray([pos],dtype=np.int64),
        "role":np.asarray([role],dtype=np.int64),
        "shape":np.asarray([shape],dtype=np.float32),
        "mask":np.ones((1,L),dtype=np.bool_),
    }
    logits=SESSION.run(["logits"],feeds)[0][0]
    result=[]
    for z in logits:
        z=z.astype(np.float64)
        p=np.exp(z-z.max()); p/=p.sum()
        idx=int(np.argmax(p))
        result.append({"role":I2ROLE[idx],"confidence":float(p[idx]),"probs":[float(x) for x in p]})
    return result, weak

def subtree_span(tok):
    ids=[t.i for t in tok.subtree]
    return min(ids), max(ids)

def nearest_clause_head(tok):
    # For complementizer "that", spaCy normally attaches it as mark to the clause predicate.
    if tok.dep_=="mark":
        return tok.head
    # Relative "that" is often an argument of a relcl predicate.
    cur=tok
    for _ in range(5):
        if cur.dep_ in {"relcl","acl","ccomp","xcomp","advcl"}:
            return cur
        if cur.head is cur:
            break
        cur=cur.head
    return tok.head

def detect_that_clauses(doc):
    clauses=[]
    appositive_nouns={"fact","idea","news","belief","claim","hope","possibility","evidence","rumor","rumour","thought","suggestion","proposal","assumption","conclusion","argument","notion"}

    for t in doc:
        if t.lower_!="that":
            continue

        # Plain demonstrative/determiner "that book" is not a clause marker.
        if t.pos_=="DET" and t.dep_ in {"det","predet"}:
            continue

        head=nearest_clause_head(t)
        start,end=subtree_span(head)
        start=min(start,t.i)
        end=max(end,t.i)

        ctype="that절"
        function="절"
        explanation="that이 이끄는 절입니다."

        rel_ancestor=None
        cur=t
        for _ in range(6):
            if cur.dep_=="relcl":
                rel_ancestor=cur; break
            if cur.head is cur: break
            cur=cur.head

        if rel_ancestor is not None:
            start,end=subtree_span(rel_ancestor)
            start=min(start,t.i); end=max(end,t.i)
            ctype="관계대명사 that절"
            function="형용사절"
            antecedent=rel_ancestor.head.text if rel_ancestor.head is not rel_ancestor else ""
            explanation=f"앞의 선행사 {antecedent!r}를 꾸미는 관계사절입니다."
        elif head.dep_ in {"acl","appos"} or (head.head.pos_ in {"NOUN","PROPN"} and head.head.lemma_.lower() in appositive_nouns):
            ctype="동격 that절"
            function="동격절"
            explanation="앞 명사의 내용을 풀어 설명하는 동격 that절입니다."
        else:
            ctype="명사절 that절"
            function="명사절"
            if head.dep_ in {"ccomp","xcomp"}:
                explanation="동사·형용사의 내용을 받는 명사절 that절입니다."
            else:
                explanation="문장 안에서 명사 역할을 하는 that절입니다."

        clauses.append({
            "type":ctype,
            "function":function,
            "start":start,
            "end":end,
            "text":" ".join(x.text for x in doc[start:end+1]),
            "that_index":t.i,
            "head_index":head.i,
            "head":head.text,
            "head_dep":head.dep_,
            "explanation":explanation,
        })

    # Dummy it + that real subject.
    for c in clauses:
        if c["type"]!="명사절 that절":
            continue
        start=c["start"]
        if any(t.lower_=="it" and t.dep_ in {"nsubj","expl"} and t.i < start for t in doc):
            pred=doc[c["head_index"]].head if doc[c["head_index"]].head is not doc[c["head_index"]] else doc[c["head_index"]]
            if pred.pos_ in {"ADJ","VERB","AUX"} or pred.lemma_=="be":
                c["type"]="진주어 that절"
                c["function"]="진주어"
                c["explanation"]="앞의 가주어 it이 대신하고 있는 실제 주어 역할의 that절입니다."
    return clauses

def detect_other_grammar(doc):
    items=[]
    lo=[t.lower_ for t in doc]
    for t in doc:
        if t.lower_ in {"if","whether"} and t.dep_=="mark":
            h=t.head; s,e=subtree_span(h); s=min(s,t.i)
            typ="조건 부사절 if" if t.lower_=="if" and h.dep_=="advcl" else ("명사절 if" if t.lower_=="if" else "명사절 whether")
            items.append({"type":typ,"start":s,"end":e,"text":" ".join(x.text for x in doc[s:e+1])})
        if t.lower_=="to" and t.dep_=="aux" and t.head.pos_=="VERB":
            s,e=subtree_span(t.head); s=min(s,t.i)
            items.append({"type":"to부정사","start":s,"end":e,"text":" ".join(x.text for x in doc[s:e+1])})
    for t in doc:
        if t.lower_=="it" and t.dep_ in {"nsubj","expl"}:
            items.append({"type":"가주어 it","start":t.i,"end":t.i,"text":t.text})
    return items

def bracket_text(doc, clauses):
    opens={}; closes={}
    # inner/outer both supported
    for c in sorted(clauses,key=lambda x:(x["start"],-(x["end"]-x["start"]))):
        opens.setdefault(c["start"],[]).append(c["type"])
        closes.setdefault(c["end"],0)
        closes[c["end"]]+=1
    parts=[]
    for i,t in enumerate(doc):
        if i in opens:
            for typ in opens[i]:
                parts.append(f"[{typ}](")
        parts.append(t.text)
        if i in closes:
            parts.append(")"*closes[i])
        if i < len(doc)-1 and not doc[i+1].is_punct:
            parts.append(" ")
    return "".join(parts)

def analyze(text):
    doc=NLP(text)
    model,weak=model_roles(doc)
    clauses=detect_that_clauses(doc)
    grammar=detect_other_grammar(doc)

    tokens=[]
    for t,m,w in zip(doc,model,weak):
        tokens.append({
            "i":t.i,"text":t.text,"lemma":t.lemma_,"pos":t.pos_,"tag":t.tag_,
            "dep":t.dep_,"head":t.head.i,"head_text":t.head.text,
            "weak_role":w,"r012_role":m["role"],"confidence":m["confidence"],
        })

    return {
        "ok":True,
        "engine":"spaCy en_core_web_sm + R012 ONNX",
        "text":text,
        "tokens":tokens,
        "that_clauses":clauses,
        "grammar":grammar,
        "bracketed":bracket_text(doc,clauses),
    }

class handler(BaseHTTPRequestHandler):
    def _headers(self,status=200):
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.send_header("Access-Control-Allow-Methods","POST,OPTIONS,GET")
        self.end_headers()

    def do_OPTIONS(self):
        self._headers(204)

    def do_GET(self):
        self._headers(200)
        self.wfile.write(json.dumps({"ok":True,"service":"SentenceLab analyzer","model":"R012"}).encode())

    def do_POST(self):
        try:
            n=int(self.headers.get("Content-Length","0"))
            body=json.loads(self.rfile.read(n) or b"{}")
            text=str(body.get("text","")).strip()
            if not text:
                raise ValueError("text is required")
            if len(text)>8000:
                raise ValueError("text too long")
            result=analyze(text)
            self._headers(200)
            self.wfile.write(json.dumps(result,ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self._headers(400)
            self.wfile.write(json.dumps({"ok":False,"error":str(e)},ensure_ascii=False).encode("utf-8"))
