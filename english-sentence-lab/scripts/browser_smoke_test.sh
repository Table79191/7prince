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


# ### FRESH_COMPLEX50_PROBE_20260918
node - <<'JS'
const fs=require('fs');
const r=require('./web/r012/browser_rules.js');
const cases=[
["N50-001","Although the engineer whom the manager had praised repaired the device that the interns had damaged, the director approved the report before the auditors arrived.",[["whom","O"],["manager","S"],["praised","V"],["director","S"],["report","O"]]],
["N50-002","Although the scientist whom the reviewer had questioned revised the paper that the editors had rejected, the chair accepted the manuscript before the reporters arrived.",[["whom","O"],["reviewer","S"],["questioned","V"],["chair","S"],["manuscript","O"]]],
["N50-003","Although the analyst whom the supervisor had trusted corrected the forecast that the traders had ignored, the president released the statement before the markets opened.",[["whom","O"],["supervisor","S"],["trusted","V"],["president","S"],["statement","O"]]],
["N50-004","Although the architect whom the client had hired redesigned the building that the inspectors had criticized, the council approved the permit before construction started.",[["whom","O"],["client","S"],["hired","V"],["council","S"],["permit","O"]]],
["N50-005","Although the doctor whom the hospital had promoted reviewed the treatment that the nurses had documented, the committee endorsed the protocol before the patients arrived.",[["whom","O"],["hospital","S"],["promoted","V"],["committee","S"],["protocol","O"]]],

["N50-006","The device that the engineer repaired was unstable because the technician who calibrated the sensor had ignored the warning.",[["device","S"],["engineer","S"],["repaired","V"],["unstable","C"],["technician","S"]]],
["N50-007","The model that the team trained was unreliable because the analyst who checked the output had missed the anomaly.",[["model","S"],["team","S"],["trained","V"],["unreliable","C"],["analyst","S"]]],
["N50-008","The bridge that the contractors rebuilt was dangerous because the inspector who examined the support had overlooked the crack.",[["bridge","S"],["contractors","S"],["rebuilt","V"],["dangerous","C"],["inspector","S"]]],
["N50-009","The schedule that the planners proposed was unrealistic because the adviser who reviewed the budget had underestimated the delay.",[["schedule","S"],["planners","S"],["proposed","V"],["unrealistic","C"],["adviser","S"]]],
["N50-010","The estimate that the consultant prepared was impossible because the accountant who checked the figures had omitted the tax.",[["estimate","S"],["consultant","S"],["prepared","V"],["impossible","C"],["accountant","S"]]],

["N50-011","When the engineer realized that the committee had rejected the proposal that the adviser needed, the director postponed the meeting.",[["engineer","S"],["committee","S"],["rejected","V"],["proposal","O"],["director","S"]]],
["N50-012","When the teacher discovered that the student had copied the solution that the examiner required, the principal canceled the exam.",[["teacher","S"],["student","S"],["copied","V"],["solution","O"],["principal","S"]]],
["N50-013","When the lawyer learned that the client had hidden the document that the court requested, the judge delayed the hearing.",[["lawyer","S"],["client","S"],["hidden","V"],["document","O"],["judge","S"]]],
["N50-014","When the pilot noticed that the controller had changed the route that the crew expected, the captain revised the plan.",[["pilot","S"],["controller","S"],["changed","V"],["route","O"],["captain","S"]]],
["N50-015","When the researcher found that the assistant had altered the sample that the laboratory required, the supervisor repeated the experiment.",[["researcher","S"],["assistant","S"],["altered","V"],["sample","O"],["supervisor","S"]]],

["N50-016","The director, who had warned that the schedule was unrealistic, made the interns rewrite the report before the auditors could discover the errors.",[["director","S"],["schedule","S"],["unrealistic","C"],["interns","O"],["report","O"]]],
["N50-017","The manager, who had warned that the deadline was impossible, made the engineers revise the design before the inspectors could detect the flaws.",[["manager","S"],["deadline","S"],["impossible","C"],["engineers","O"],["design","O"]]],
["N50-018","The professor, who had warned that the argument was unreliable, made the students redo the calculation before the reviewers could challenge the result.",[["professor","S"],["argument","S"],["unreliable","C"],["students","O"],["calculation","O"]]],
["N50-019","The coach, who had warned that the strategy was ineffective, made the players repeat the drill before the scouts could evaluate the performance.",[["coach","S"],["strategy","S"],["ineffective","C"],["players","O"],["drill","O"]]],
["N50-020","The editor, who had warned that the draft was unacceptable, made the writers revise the article before the publisher could notice the mistakes.",[["editor","S"],["draft","S"],["unacceptable","C"],["writers","O"],["article","O"]]],

["N50-021","Although the sample was contaminated by the technician, the measurement remained reliable until the scientist had repeated the test.",[["sample","S"],["contaminated","V"],["measurement","S"],["reliable","C"],["scientist","S"]]],
["N50-022","Although the document was misplaced by the clerk, the record remained available until the lawyer had recovered the file.",[["document","S"],["misplaced","V"],["record","S"],["available","C"],["lawyer","S"]]],
["N50-023","Although the engine was damaged by the mechanic, the vehicle remained operational until the inspector had completed the review.",[["engine","S"],["damaged","V"],["vehicle","S"],["operational","C"],["inspector","S"]]],
["N50-024","Although the server was restarted by the administrator, the service remained stable until the engineer had checked the logs.",[["server","S"],["restarted","V"],["service","S"],["stable","C"],["engineer","S"]]],
["N50-025","Although the contract was amended by the lawyer, the agreement remained enforceable until the judge had reviewed the clause.",[["contract","S"],["amended","V"],["agreement","S"],["enforceable","C"],["judge","S"]]],

["N50-026","Only after the auditor had reviewed the ledger did the accountant admit that the clerk had altered the entries.",[["auditor","S"],["ledger","O"],["accountant","S"],["admit","V"],["entries","O"]]],
["N50-027","Only after the researcher had measured the sample did the scientist realize that the assistant had mislabeled the tubes.",[["researcher","S"],["sample","O"],["scientist","S"],["realize","V"],["tubes","O"]]],
["N50-028","Only after the detective had examined the footage did the witness confess that the driver had ignored the signal.",[["detective","S"],["footage","O"],["witness","S"],["confess","V"],["signal","O"]]],
["N50-029","Only after the editor had compared the drafts did the author acknowledge that the translator had omitted the phrase.",[["editor","S"],["drafts","O"],["author","S"],["acknowledge","V"],["phrase","O"]]],
["N50-030","Only after the engineer had tested the circuit did the technician discover that the sensor had reversed the polarity.",[["engineer","S"],["circuit","O"],["technician","S"],["discover","V"],["polarity","O"]]],

["N50-031","What the witness had described was why the detective reopened the case after the prosecutor had objected.",[["witness","S"],["described","V"],["detective","S"],["case","O"],["prosecutor","S"]]],
["N50-032","What the analyst had predicted was why the investor sold the shares after the adviser had warned.",[["analyst","S"],["predicted","V"],["investor","S"],["shares","O"],["adviser","S"]]],
["N50-033","What the student had written was why the professor revised the grade after the examiner had complained.",[["student","S"],["written","V"],["professor","S"],["grade","O"],["examiner","S"]]],
["N50-034","What the sensor had recorded was why the engineer stopped the machine after the operator had reported the noise.",[["sensor","S"],["recorded","V"],["engineer","S"],["machine","O"],["operator","S"]]],
["N50-035","What the doctor had observed was why the surgeon delayed the operation after the nurse had called.",[["doctor","S"],["observed","V"],["surgeon","S"],["operation","O"],["nurse","S"]]],

["N50-036","If the auditor discovers that the clerk had altered the ledger, the manager will suspend the account unless the explanation is convincing.",[["auditor","S"],["clerk","S"],["ledger","O"],["manager","S"],["convincing","C"]]],
["N50-037","If the scientist proves that the assistant had contaminated the sample, the director will repeat the experiment unless the evidence is conclusive.",[["scientist","S"],["assistant","S"],["sample","O"],["director","S"],["conclusive","C"]]],
["N50-038","If the teacher learns that the student had copied the essay, the principal will cancel the grade unless the excuse is acceptable.",[["teacher","S"],["student","S"],["essay","O"],["principal","S"],["acceptable","C"]]],
["N50-039","If the engineer confirms that the vendor had replaced the component, the factory will halt production unless the backup is reliable.",[["engineer","S"],["vendor","S"],["component","O"],["factory","S"],["reliable","C"]]],
["N50-040","If the lawyer shows that the company had violated the contract, the judge will reopen the case unless the settlement is reasonable.",[["lawyer","S"],["company","S"],["contract","O"],["judge","S"],["reasonable","C"]]],

["N50-041","The proposal that the committee had rejected and that the director later revised became acceptable after the lawyers reviewed it.",[["proposal","S"],["committee","S"],["director","S"],["acceptable","C"],["lawyers","S"]]],
["N50-042","The device that the engineer had designed and that the technician later repaired became reliable after the inspectors tested it.",[["device","S"],["engineer","S"],["technician","S"],["reliable","C"],["inspectors","S"]]],
["N50-043","The manuscript that the editors had criticized and that the author later rewrote became publishable after the reviewers approved it.",[["manuscript","S"],["editors","S"],["author","S"],["publishable","C"],["reviewers","S"]]],
["N50-044","The policy that the council had proposed and that the mayor later modified became enforceable after the court upheld it.",[["policy","S"],["council","S"],["mayor","S"],["enforceable","C"],["court","S"]]],
["N50-045","The model that the analysts had built and that the researchers later adjusted became usable after the testers validated it.",[["model","S"],["analysts","S"],["researchers","S"],["usable","C"],["testers","S"]]],

["N50-046","The manager said that the engineer who had repaired the server would update the software before the clients returned.",[["manager","S"],["engineer","S"],["server","O"],["software","O"],["clients","S"]]],
["N50-047","The professor said that the student who had solved the problem would present the proof before the judges arrived.",[["professor","S"],["student","S"],["problem","O"],["proof","O"],["judges","S"]]],
["N50-048","The doctor said that the nurse who had monitored the patient would record the symptoms before the surgeon returned.",[["doctor","S"],["nurse","S"],["patient","O"],["symptoms","O"],["surgeon","S"]]],
["N50-049","The captain said that the pilot who had checked the engine would revise the route before the passengers boarded.",[["captain","S"],["pilot","S"],["engine","O"],["route","O"],["passengers","S"]]],
["N50-050","The editor said that the writer who had revised the chapter would submit the manuscript before the publisher called.",[["editor","S"],["writer","S"],["chapter","O"],["manuscript","O"],["publisher","S"]]]
];
const pre=cases.map(function(row){
  const id=row[0],sentence=row[1],focus=row[2];
  const tokens=r.splitTokens(sentence),pos=r.inferPos(tokens),weak=r.weakRoles(pos);
  return {id:id,sentence:sentence,focus:focus,tokens:tokens,pos:pos,weak:weak};
});
fs.writeFileSync('/tmp/fresh50_pre.json',JSON.stringify(pre));
console.log('FRESH50_PREPARED='+pre.length);
JS

python - <<'PY'
import json, numpy as np, onnxruntime as ort
cases=json.load(open('/tmp/fresh50_pre.json'))
POS=['UNK','ADJ','ADP','ADV','AUX','CCONJ','DET','INTJ','NOUN','NUM','PART','PRON','PROPN','PUNCT','SCONJ','SYM','VERB','X']
P={v:i for i,v in enumerate(POS)}
R={'S':1,'V':2,'O':3,'C':4,'M':5}
I=[None,'S','V','O','C','M']
def h(s):
    v=2166136261
    for b in s.encode(): v=((v^b)*16777619)&0xffffffff
    return v
def sh(w):
    lo=w.lower()
    return [float(w[:1].isupper()),float(w.isupper() and any(c.isalpha() for c in w)),float(any(c.isdigit() for c in w)),float('-' in w),float(lo.endswith('ing')),float(lo.endswith('ed')),float(lo.endswith('ly')),min(len(w),20)/20]
sess=ort.InferenceSession('web/r012/r012_role.onnx',providers=['CPUExecutionProvider'])
all_raw=[]
for x in cases:
    t=x['tokens']
    feeds={
      'wid':np.array([[h(w.lower())%8192 for w in t]],np.int64),
      'pre':np.array([[h(w.lower()[:3])%1024 for w in t]],np.int64),
      'suf':np.array([[h(w.lower()[-3:])%1024 for w in t]],np.int64),
      'pos':np.array([[P.get(p,0) for p in x['pos']]],np.int64),
      'role':np.array([[0 if rr is None else R.get(rr,0) for rr in x['weak']]],np.int64),
      'shape':np.array([[sh(w) for w in t]],np.float32),
      'mask':np.ones((1,len(t)),np.bool_),
    }
    z=sess.run(['logits'],feeds)[0][0]
    all_raw.append([I[int(i)] for i in z.argmax(-1)])
json.dump(all_raw,open('/tmp/fresh50_raw.json','w'))
PY

node - <<'JS'
const fs=require('fs');
const r=require('./web/r012/browser_rules.js');
const cases=JSON.parse(fs.readFileSync('/tmp/fresh50_pre.json'));
const raws=JSON.parse(fs.readFileSync('/tmp/fresh50_raw.json'));
let correct=0, exact=0, errors=[], conf={};
for(let k=0;k<cases.length;k++){
  const x=cases[k],final=r.postprocessRoles(x.tokens,[...x.pos],raws[k]);
  let ok=true;
  for(const f of x.focus){
    const word=f[0],gold=f[1];
    const idx=x.tokens.findIndex(function(t){return t.toLowerCase()===word.toLowerCase();});
    if(idx<0) throw new Error(x.id+': focus token not found '+word);
    const pred=final[idx];
    if(pred===gold) correct++;
    else{
      ok=false;
      const key=gold+'->'+pred;
      conf[key]=(conf[key]||0)+1;
      errors.push({id:x.id,token:x.tokens[idx],gold:gold,pred:pred,pos:x.pos[idx],sentence:x.sentence});
    }
  }
  if(ok) exact++;
}
const summary={sentences:50,focus_checks:250,correct:correct,accuracy:correct/250,exact_sentences:exact,exact_accuracy:exact/50,confusions:Object.entries(conf).sort(function(a,b){return b[1]-a[1];}),error_count:errors.length};
console.log('FRESH50_SUMMARY='+JSON.stringify(summary));
console.log('FRESH50_ERRORS='+JSON.stringify(errors));
JS
