from flask import Flask, request, jsonify
import re

app = Flask(__name__)

CLAUSE_STARTERS = {
    "that":"that절","if":"if절","whether":"whether절",
    "what":"what절","which":"which절","who":"who절","whom":"whom절","whose":"whose절",
    "when":"when절","where":"where절","why":"why절","how":"how절",
    "while":"while절","whilst":"whilst절","because":"because절",
    "although":"although절","though":"though절","unless":"unless절",
    "until":"until절","before":"before절","after":"after절","since":"since절",
    "once":"once절","whereas":"whereas절","as":"as절"
}
END_PUNCT = {".","?","!",";"}

def tokenize(text):
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+(?:[.,]\d+)?|[^\sA-Za-z0-9]", text)

def classify(tokens, i):
    w = tokens[i].lower()
    prev = tokens[i-1].lower() if i else ""
    if w == "if":
        return "명사절 if" if prev in {"ask","asked","know","knew","wonder","wondered","see","check","decide","tell"} else "조건 부사절 if"
    if w == "whether":
        return "명사절 whether"
    if w == "that":
        return "동격 that절" if prev in {"fact","idea","news","belief","claim","hope","possibility","evidence","thought","suggestion","proposal","assumption","conclusion"} else "that절"
    if w in {"what","which","who","whom","whose","why","how"}:
        if i == 0 and tokens and tokens[-1] == "?":
            return "직접 의문문"
        return f"의문사절 {w}"
    if w in {"while","whilst","because","although","though","unless","until","before","after","since","once","whereas","as","when","where"}:
        return f"{w} 부사절"
    return CLAUSE_STARTERS.get(w, w+"절")

def clause_end(tokens, start):
    for j in range(start+1, len(tokens)):
        if tokens[j] in END_PUNCT:
            return j-1
        if tokens[j] == ",":
            return j-1
    return len(tokens)-1

def detect_clauses(tokens):
    out = []
    for i,t in enumerate(tokens):
        w=t.lower()
        if w not in CLAUSE_STARTERS:
            continue
        if w=="that" and i+1<len(tokens) and tokens[i+1].lower() in {"book","car","man","woman","thing","idea","day","time","way","place"}:
            continue
        end=clause_end(tokens,i)
        typ=classify(tokens,i)
        fn="절"
        if typ=="직접 의문문":
            fn="주절"
        elif "명사절" in typ or "의문사절" in typ or typ=="that절":
            fn="명사절"
        elif "부사절" in typ or typ.startswith("조건 "):
            fn="부사절"
        elif "동격" in typ:
            fn="동격절"
        out.append({
            "type":typ,"function":fn,"start":i,"end":end,"trigger":t,
            "text":" ".join(tokens[i:end+1]),
            "explanation":("문장 전체가 직접 의문문인 주절입니다." if typ=="직접 의문문" else f"{t}로 시작하는 {fn}입니다.")
        })
    return out

def bracketed(tokens, clauses):
    opens={}; closes={}
    for c in clauses:
        opens.setdefault(c["start"],[]).append(c)
        closes.setdefault(c["end"],[]).append(c)
    parts=[]
    for i,t in enumerate(tokens):
        for c in opens.get(i,[]): parts.append(f"[{c['type']}](")
        parts.append(t)
        for _ in closes.get(i,[]): parts.append(")")
        if i<len(tokens)-1 and tokens[i+1] not in {".",",","?","!",";",":",")"}:
            parts.append(" ")
    return "".join(parts)

@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"]="*"
    resp.headers["Access-Control-Allow-Headers"]="Content-Type"
    resp.headers["Access-Control-Allow-Methods"]="GET,POST,OPTIONS"
    return resp

@app.route("/", methods=["GET"])
def health():
    return jsonify(ok=True, service="SentenceLab clause API", version="render-v1")

@app.route("/api/analyze", methods=["GET","POST","OPTIONS"])
def analyze():
    if request.method=="OPTIONS":
        return ("",204)
    text = (request.get_json(silent=True) or {}).get("text","") if request.method=="POST" else request.args.get("text","")
    text = str(text).strip()
    if not text:
        if request.method=="GET":
            return jsonify(ok=True, service="SentenceLab clause API", version="render-v1")
        return jsonify(ok=False,error="text is required"),400
    tokens=tokenize(text)
    clauses=detect_clauses(tokens)
    return jsonify(
        ok=True,engine="SentenceLab Render clause API",text=text,
        tokens=[{"i":i,"text":t} for i,t in enumerate(tokens)],
        clauses=clauses,bracketed=bracketed(tokens,clauses)
    )
