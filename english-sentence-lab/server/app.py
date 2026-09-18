from flask import Flask, jsonify, request
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "api" / "analyze.py"

spec = importlib.util.spec_from_file_location("sentencelab_backend", BACKEND_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load analyzer backend: {BACKEND_PATH}")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

app = Flask(__name__)

@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return resp

@app.route("/", methods=["GET"])
def health():
    return jsonify(
        ok=True,
        service="SentenceLab analyzer",
        engine="shared api/analyze.py backend",
        model="R012",
    )

@app.route("/api/analyze", methods=["GET","POST","OPTIONS"])
def analyze_route():
    if request.method == "OPTIONS":
        return ("", 204)

    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        text = str(body.get("text", "")).strip()
    else:
        text = str(request.args.get("text", "")).strip()

    if not text:
        if request.method == "GET":
            return health()
        return jsonify(ok=False, error="text is required"), 400
    if len(text) > 8000:
        return jsonify(ok=False, error="text too long"), 400

    try:
        return jsonify(backend.analyze(text))
    except Exception as exc:
        return jsonify(ok=False, error=str(exc)), 400
