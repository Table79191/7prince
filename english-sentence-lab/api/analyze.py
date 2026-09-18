from http.server import BaseHTTPRequestHandler
import json, math, re
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import onnxruntime as ort
import spacy

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "web" / "r012" / "r012_role.onnx"
MODEL_URL = "https://raw.githubusercontent.com/Table79191/7prince/main/english-sentence-lab/web/r012/r012_role.onnx"

def ensure_model():
    if MODEL_PATH.exists():
        return MODEL_PATH
    cache = Path("/tmp/r012_role.onnx")
    if not cache.exists():
        with urlopen(MODEL_URL, timeout=30) as r:
            cache.write_bytes(r.read())
    return cache

POS_LIST = ['UNK','ADJ','ADP','ADV','AUX','CCONJ','DET','INTJ','NOUN','NUM','PART','PRON','PROPN','PUNCT','SCONJ','SYM','VERB','X']
POS2I = {x:i for i,x in enumerate(POS_LIST)}
I2ROLE = [None,'S','V','O','C','M']
ROLE2I = {'S':1,'V':2,'O':3,'C':4,'M':5}

NLP = spacy.load("en_core_web_sm")
SESSION = ort.InferenceSession(str(ensure_model()), providers=["CPUExecutionProvider"])

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

def normalized_surface_forms(doc):
    """Return token-aligned surfaces matching training-time contraction normalization."""
    forms=[t.text for t in doc]
    for i,t in enumerate(doc):
        lo=t.text.lower().replace("’","'")
        nxt=doc[i+1].text.lower().replace("’","'") if i+1<len(doc) else ""
        if lo=="ca" and nxt=="n't":
            forms[i]="can"
        elif lo=="wo" and nxt=="n't":
            forms[i]="will"
        elif lo=="sha" and nxt=="n't":
            forms[i]="shall"
        elif lo=="n't":
            forms[i]="not"
        elif lo=="'re":
            forms[i]="are"
        elif lo=="'ve":
            forms[i]="have"
        elif lo=="'ll":
            forms[i]="will"
        elif lo=="'m":
            forms[i]="am"
    return forms

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
    surfaces=normalized_surface_forms(doc)
    wid=[]; pre=[]; suf=[]; pos=[]; role=[]; shape=[]
    for t,b,w in zip(toks,weak,surfaces):
        lo=w.lower()
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

def detect_all_clauses(doc, that_clauses):
    """Detect clause spans beyond that: if/whether/WH/relative/adverbial/etc."""
    clauses=list(that_clauses)
    seen={(x["start"],x["end"],x["type"]) for x in clauses}

    def add(ctype, function, start, end, trigger, head, explanation):
        start=max(0,start); end=min(len(doc)-1,end)
        if start>end:
            return
        key=(start,end,ctype)
        if key in seen:
            return
        seen.add(key)
        clauses.append({
            "type":ctype,
            "function":function,
            "start":start,
            "end":end,
            "text":" ".join(x.text for x in doc[start:end+1]),
            "trigger":trigger,
            "head_index":head.i if head is not None else -1,
            "head":head.text if head is not None else "",
            "head_dep":head.dep_ if head is not None else "",
            "explanation":explanation,
        })

    # Explicit subordinating conjunctions / markers.
    adverb_markers={
        "while":"시간·대조 부사절",
        "whilst":"시간·대조 부사절",
        "because":"이유 부사절",
        "although":"양보 부사절",
        "though":"양보 부사절",
        "unless":"조건 부사절",
        "until":"시간 부사절",
        "before":"시간 부사절",
        "after":"시간 부사절",
        "since":"시간·이유 부사절",
        "once":"시간·조건 부사절",
        "whereas":"대조 부사절",
        "as":"시간·이유·방식 부사절",
        "when":"시간 부사절",
        "whenever":"시간 부사절",
    }

    for t in doc:
        w=t.lower_
        if t.dep_=="mark":
            head=t.head
            s,e=subtree_span(head)
            s=min(s,t.i); e=max(e,t.i)

            if w=="if":
                if head.dep_=="advcl":
                    add("조건 부사절 if","부사절",s,e,w,head,
                        "if가 조건을 나타내며 주절 전체를 수식하는 부사절입니다.")
                else:
                    add("명사절 if","명사절",s,e,w,head,
                        "if가 ‘~인지’라는 의미로 명사 역할을 하는 절을 이끕니다.")
            elif w=="whether":
                add("명사절 whether","명사절",s,e,w,head,
                    "whether가 ‘~인지 아닌지’의 의미를 갖는 명사절을 이끕니다.")
            elif w in adverb_markers:
                add(adverb_markers[w],"부사절",s,e,w,head,
                    f"{w}가 이끄는 종속 부사절입니다.")

    # Relative clauses. This also catches which/who/whom/whose/where/when and that.
    relative_words={"that","which","who","whom","whose","where","when"}
    for head in doc:
        if head.dep_!="relcl":
            continue
        s,e=subtree_span(head)
        rel=None
        for x in head.subtree:
            if x.lower_ in relative_words:
                rel=x
                break
        trigger=rel.lower_ if rel is not None else "관계사 생략"
        ctype=f"관계사절 {trigger}" if rel is not None else "관계사 생략절"
        add(ctype,"형용사절",s,e,trigger,head,
            "앞의 선행사를 꾸미는 관계사절입니다.")

    # Embedded WH clauses / indirect questions: what, which, who, when, where, why, how...
    wh_words={"what","which","who","whom","whose","when","where","why","how"}
    clause_deps={"ccomp","xcomp","csubj","advcl"}
    for t in doc:
        if t.lower_ not in wh_words:
            continue
        cur=t
        clause_head=None
        for _ in range(8):
            if cur.dep_ in clause_deps:
                clause_head=cur
                break
            if cur.head is cur:
                break
            cur=cur.head
        if clause_head is None:
            # WH token can be an argument inside a ccomp predicate.
            cur=t.head
            for _ in range(8):
                if cur.dep_ in clause_deps:
                    clause_head=cur
                    break
                if cur.head is cur:
                    break
                cur=cur.head
        if clause_head is None:
            continue
        s,e=subtree_span(clause_head)
        s=min(s,t.i)
        if clause_head.dep_=="advcl" and t.lower_ in {"when","where","how"}:
            ctype=f"{t.lower_} 부사절"
            function="부사절"
            expl=f"{t.text}가 이끄는 부사절입니다."
        else:
            ctype=f"의문사절 {t.lower_}"
            function="명사절"
            expl=f"{t.text}로 시작해 문장 안에서 명사 역할을 하는 간접의문/의문사절입니다."
        add(ctype,function,s,e,t.lower_,clause_head,expl)

    # Clausal complements without an overt marker, e.g. "I think he left."
    for head in doc:
        if head.dep_=="ccomp":
            s,e=subtree_span(head)
            # Don't duplicate an already detected explicit clause with same/near span.
            covered=any(c["start"]<=s and c["end"]>=e and c["function"] in {"명사절","진주어"} for c in clauses)
            if not covered:
                add("접속사 생략 명사절","명사절",s,e,"생략",head,
                    "접속사 that 등이 생략된 것으로 볼 수 있는 명사절입니다.")

    # Subject clauses.
    for head in doc:
        if head.dep_=="csubj":
            s,e=subtree_span(head)
            add("주어절","명사절",s,e,"주어절",head,
                "문장 전체에서 주어 역할을 하는 절입니다.")

    # Sort outer clauses first when they begin at the same token.
    clauses.sort(key=lambda x:(x["start"],-(x["end"]-x["start"]),x["type"]))
    return clauses

def detect_other_grammar(doc):
    items=[]
    for t in doc:
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
    that_clauses=detect_that_clauses(doc)
    clauses=detect_all_clauses(doc, that_clauses)
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
        "engine":"SentenceLab shared spaCy + R012 ONNX",
        "text":text,
        "tokens":tokens,
        "that_clauses":that_clauses,
        "clauses":clauses,
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
        from urllib.parse import urlparse, parse_qs
        qs=parse_qs(urlparse(self.path).query)
        text=(qs.get("text") or [""])[0].strip()
        self._headers(200)
        if text:
            self.wfile.write(json.dumps(analyze(text),ensure_ascii=False).encode("utf-8"))
        else:
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
