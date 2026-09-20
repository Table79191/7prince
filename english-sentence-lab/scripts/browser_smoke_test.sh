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
const approxSentence="I've only used like 0.001% of my powers so far.";
const approxTokens=r.splitTokens(approxSentence),approxPos=r.inferPos(approxTokens);
const approxFinal=r.postprocessRoles(approxTokens,[...approxPos],r.weakRoles(approxPos));
const approxWant=['S','V','M','V','M','M','O','M','M','M','M','M',null];
if(JSON.stringify(approxFinal)!==JSON.stringify(approxWant)){
  throw new Error('approx percentage regression '+JSON.stringify({approxTokens,approxPos,approxFinal,approxWant}));
}
const np=['my','0.001','%','powers'],pp=['DET','NUM','SYM','NOUN'];
const nf=r.postprocessRoles(np,pp,['O','O','O','O']);
if(JSON.stringify(nf)!==JSON.stringify(['M','M','M','O'])) throw new Error('NP '+JSON.stringify(nf));


const regressionCases=[
  ["Although the engineer whom the manager had praised repaired the device.", "whom", "O"],
  ["The record remained reliable until the lawyer returned.", "reliable", "C"],
  ["The director made the interns rewrite the report.", "interns", "O"],
  ["Only after the auditor had reviewed the ledger did the accountant admit the error.", "accountant", "S"],
  ["What the witness had described was why the detective reopened the case.", "witness", "S"],
  ["When the engineer realized that the committee had rejected the proposal, the director postponed the meeting.", "committee", "S"]
];
for(const [s,word,want] of regressionCases){
  const t=r.splitTokens(s),p=r.inferPos(t),fin=r.postprocessRoles(t,[...p],r.weakRoles(p));
  const i=t.findIndex(x=>x.toLowerCase()===word.toLowerCase());
  if(i<0||fin[i]!==want) throw new Error('regression '+s+' '+word+' expected '+want+' got '+fin[i]+' '+JSON.stringify({t,p,fin}));
}
for(const [s,word,want] of [
  ["The hospital had promoted the doctor.","hospital","NOUN"],
  ["The principal canceled the exam.","principal","NOUN"],
  ["The factory will halt production.","factory","NOUN"],
  ["The report was ready.","report","NOUN"]
]){
  const t=r.splitTokens(s),p=r.inferPos(t),i=t.findIndex(x=>x.toLowerCase()===word.toLowerCase());
  if(i<0||p[i]!==want) throw new Error('POS regression '+s+' '+word+' expected '+want+' got '+p[i]);
}

const inferenceCases=[
  "what the hell was that",
  "I've only used like 0.001% of my powers so far."
].map(sentence=>{
  const tokens=r.splitTokens(sentence);
  const pos=r.inferPos(tokens);
  const weak=r.weakRoles(pos);
  return {sentence,tokens,pos,weak};
});
fs.writeFileSync('/tmp/sentencelab_pre.json',JSON.stringify(inferenceCases));
console.log('browser rules: ok');
JS

python - <<'PY'
import json
import numpy as np
import onnxruntime as ort

rows=json.load(open('/tmp/sentencelab_pre.json'))
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

session=ort.InferenceSession('web/r012/r012_role.onnx',providers=['CPUExecutionProvider'])
raw_rows=[]
for x in rows:
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
    z=session.run(['logits'],feeds)[0][0]
    raw_rows.append([I[int(i)] for i in z.argmax(-1)])
json.dump(raw_rows,open('/tmp/sentencelab_raw.json','w'))
PY

node - <<'JS'
const fs=require('fs');
const r=require('./web/r012/browser_rules.js');
const rows=JSON.parse(fs.readFileSync('/tmp/sentencelab_pre.json'));
const raws=JSON.parse(fs.readFileSync('/tmp/sentencelab_raw.json'));
const wants=[
  ['C','M','M','V','S'],
  ['S','V','M','V','M','M','O','M','M','M','M','M',null]
];
for(let k=0;k<rows.length;k++){
  const x=rows[k],raw=raws[k];
  const final=r.postprocessRoles(x.tokens,[...x.pos],raw);
  const want=wants[k];
  if(JSON.stringify(final)!==JSON.stringify(want)){
    throw new Error(JSON.stringify({sentence:x.sentence,x,raw,final,want}));
  }
  console.log(JSON.stringify({sentence:x.sentence,tokens:x.tokens,raw,final}));
}
JS
