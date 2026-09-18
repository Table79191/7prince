#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

node - <<'JS'
const fs=require('fs');
const r=require('./web/r012/browser_rules.js');

const checks=[
  ["They lead the team.",1,"VERB"],
  ["We practice every day.",1,"VERB"],
  ["They improve quickly.",1,"VERB"],
  ["We rely on data.",1,"VERB"],
  ["They perform well.",1,"VERB"],
  ["I focus on grammar.",1,"VERB"],
  ["He is talented.",2,"ADJ"],
  ["She is gifted.",2,"ADJ"],
  ["He's ready.",1,"AUX"],
  ["I'd go.",1,"AUX"]
];
for(const [s,i,want] of checks){
  const t=r.splitTokens(s),p=r.inferPos(t);
  if(p[i]!==want) throw new Error(s+' expected '+want+' got '+p[i]);
}
for(const [s,want] of [
  ["He is talented.",["S","V","C",null]],
  ["She is gifted.",["S","V","C",null]],
  ["We rely on data.",["S","V","M","M",null]]
]){
  const t=r.splitTokens(s),p=r.inferPos(t),fin=r.postprocessRoles(t,[...p],r.weakRoles(p));
  if(JSON.stringify(fin)!==JSON.stringify(want)) throw new Error(s+' '+JSON.stringify(fin));
}
for(const s of ["What on earth was that?","Who in the world was that?","what the hell was that?"]){
  const t=r.splitTokens(s),p=r.inferPos(t),fin=r.postprocessRoles(t,[...p],r.weakRoles(p));
  const cop=p.findIndex(x=>x==='AUX');
  if(fin[0]!=='C'||fin[cop]!=='V'||fin[cop+1]!=='S') throw new Error(s+' '+JSON.stringify(fin));
  for(let i=1;i<cop;i++) if(fin[i]!=='M') throw new Error(s+' filler '+JSON.stringify(fin));
}
const np=['my','0.001','%','powers'],pp=['DET','NUM','SYM','NOUN'];
const nf=r.postprocessRoles(np,pp,['O','O','O','O']);
if(JSON.stringify(nf)!==JSON.stringify(['M','M','M','O'])) throw new Error('NP '+JSON.stringify(nf));

const tokens=r.splitTokens("what the hell was that");
const pos=r.inferPos(tokens);
const weak=r.weakRoles(pos);
fs.writeFileSync('/tmp/sentencelab_pre.json',JSON.stringify({tokens,pos,weak}));
console.log('browser rules: ok');
JS

python - <<'PY'
import json
import numpy as np
import onnxruntime as ort

x=json.load(open('/tmp/sentencelab_pre.json'))
POS=['UNK','ADJ','ADP','ADV','AUX','CCONJ','DET','INTJ','NOUN','NUM','PART','PRON','PROPN','PUNCT','SCONJ','SYM','VERB','X']
P={v:i for i,v in enumerate(POS)}
R={'S':1,'V':2,'O':3,'C':4,'M':5}
I=[None,'S','V','O','C','M']

def h(s):
    v=2166136261
    for b in s.encode():
        v=((v^b)*16777619)&0xffffffff
    return v

def sh(w):
    lo=w.lower()
    return [
        float(w[:1].isupper()),
        float(w.isupper() and any(c.isalpha() for c in w)),
        float(any(c.isdigit() for c in w)),
        float('-' in w),
        float(lo.endswith('ing')),
        float(lo.endswith('ed')),
        float(lo.endswith('ly')),
        min(len(w),20)/20,
    ]

t=x['tokens']
feeds={
    'wid':np.array([[h(w.lower())%8192 for w in t]],np.int64),
    'pre':np.array([[h(w.lower()[:3])%1024 for w in t]],np.int64),
    'suf':np.array([[h(w.lower()[-3:])%1024 for w in t]],np.int64),
    'pos':np.array([[P.get(p,0) for p in x['pos']]],np.int64),
    'role':np.array([[0 if r is None else R.get(r,0) for r in x['weak']]],np.int64),
    'shape':np.array([[sh(w) for w in t]],np.float32),
    'mask':np.ones((1,len(t)),np.bool_),
}
z=ort.InferenceSession('web/r012/r012_role.onnx',providers=['CPUExecutionProvider']).run(['logits'],feeds)[0][0]
json.dump([I[int(i)] for i in z.argmax(-1)],open('/tmp/sentencelab_raw.json','w'))
PY

node - <<'JS'
const fs=require('fs');
const r=require('./web/r012/browser_rules.js');
const x=JSON.parse(fs.readFileSync('/tmp/sentencelab_pre.json'));
const raw=JSON.parse(fs.readFileSync('/tmp/sentencelab_raw.json'));
const final=r.postprocessRoles(x.tokens,[...x.pos],raw);
const want=['C','M','M','V','S'];
if(JSON.stringify(final)!==JSON.stringify(want)){
  throw new Error(JSON.stringify({x,raw,final,want}));
}
console.log(JSON.stringify({tokens:x.tokens,raw,final}));
JS


# ### COMPLEX_PROBE_20260918
node - <<'JS'
const fs=require('fs');
const r=require('./web/r012/browser_rules.js');
const sentence="Although the researcher whom the committee had expected to resign after the data that she collected were questioned insisted that the model which the interns had trained was still reliable, the director, who had already warned everyone that the deadline was unrealistic, made the exhausted team rewrite the report before anyone could discover how many assumptions had been left unexplained.";
const tokens=r.splitTokens(sentence);
const pos=r.inferPos(tokens);
const weak=r.weakRoles(pos);
fs.writeFileSync('/tmp/complex_probe_pre.json',JSON.stringify({sentence,tokens,pos,weak}));
console.log('COMPLEX_PROBE_PRE='+JSON.stringify({tokens,pos,weak}));
JS

python - <<'PY'
import json, numpy as np, onnxruntime as ort
x=json.load(open('/tmp/complex_probe_pre.json'))
POS=['UNK','ADJ','ADP','ADV','AUX','CCONJ','DET','INTJ','NOUN','NUM','PART','PRON','PROPN','PUNCT','SCONJ','SYM','VERB','X']
P={v:i for i,v in enumerate(POS)}
R={'S':1,'V':2,'O':3,'C':4,'M':5}
I=[None,'S','V','O','C','M']
def h(s):
    v=2166136261
    for b in s.encode():
        v=((v^b)*16777619)&0xffffffff
    return v
def sh(w):
    lo=w.lower()
    return [float(w[:1].isupper()),float(w.isupper() and any(c.isalpha() for c in w)),float(any(c.isdigit() for c in w)),float('-' in w),float(lo.endswith('ing')),float(lo.endswith('ed')),float(lo.endswith('ly')),min(len(w),20)/20]
t=x['tokens']
feeds={
 'wid':np.array([[h(w.lower())%8192 for w in t]],np.int64),
 'pre':np.array([[h(w.lower()[:3])%1024 for w in t]],np.int64),
 'suf':np.array([[h(w.lower()[-3:])%1024 for w in t]],np.int64),
 'pos':np.array([[P.get(p,0) for p in x['pos']]],np.int64),
 'role':np.array([[0 if r is None else R.get(r,0) for r in x['weak']]],np.int64),
 'shape':np.array([[sh(w) for w in t]],np.float32),
 'mask':np.ones((1,len(t)),np.bool_),
}
z=ort.InferenceSession('web/r012/r012_role.onnx',providers=['CPUExecutionProvider']).run(['logits'],feeds)[0][0]
raw=[I[int(i)] for i in z.argmax(-1)]
json.dump(raw,open('/tmp/complex_probe_raw.json','w'))
PY

node - <<'JS'
const fs=require('fs');
const r=require('./web/r012/browser_rules.js');
const x=JSON.parse(fs.readFileSync('/tmp/complex_probe_pre.json'));
const raw=JSON.parse(fs.readFileSync('/tmp/complex_probe_raw.json'));
const final=r.postprocessRoles(x.tokens,[...x.pos],raw);
console.log('COMPLEX_PROBE_RESULT='+JSON.stringify({sentence:x.sentence,tokens:x.tokens,pos:x.pos,raw,final}));
JS
