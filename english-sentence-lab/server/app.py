from pathlib import Path
import sys

from flask import Flask, request, jsonify

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.analyze import analyze

app = Flask(__name__)

@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"]="*"
    resp.headers["Access-Control-Allow-Headers"]="Content-Type"
    resp.headers["Access-Control-Allow-Methods"]="GET,POST,OPTIONS"
    return resp

@app.route("/", methods=["GET"])
def health():
    return jsonify(ok=True, service="SentenceLab shared analyzer", version="shared-r012")

@app.route("/api/analyze", methods=["GET","POST","OPTIONS"])
def analyze_route():
    if request.method=="OPTIONS":
        return ("",204)
    text=(request.get_json(silent=True) or {}).get("text","") if request.method=="POST" else request.args.get("text","")
    text=str(text).strip()
    if not text:
        if request.method=="GET":
            return jsonify(ok=True, service="SentenceLab shared analyzer", version="shared-r012")
        return jsonify(ok=False,error="text is required"),400
    if len(text)>8000:
        return jsonify(ok=False,error="text too long"),400
    try:
        return jsonify(analyze(text))
    except Exception as exc:
        return jsonify(ok=False,error=str(exc)),400
