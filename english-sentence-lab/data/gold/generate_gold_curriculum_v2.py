#!/usr/bin/env python3
from __future__ import annotations
import json, random
from pathlib import Path

OUT=Path(__file__).resolve().parent
R=random.Random(79191)
SUBJ=['manager','engineer','teacher','researcher','analyst','doctor','designer','supervisor','editor','reviewer']
PEOPLE=['interns','students','workers','researchers','reviewers','engineers','editors','assistants']
OBJ=['report','proposal','prototype','design','system','device','experiment','project','plan','document','model','sensor']
ADJ=['useful','reliable','unsafe','effective','unrealistic','confusing','stable','ready','necessary','incorrect','harmless','slippery']
ADV=['carefully','quietly','quickly','eventually','probably','clearly','surprisingly','deliberately']
PAST=['reviewed','tested','revised','checked','approved','rejected','explained','reported','noticed','questioned']
BASE=['review','test','rewrite','check','approve','finish','explain','repair','compare','publish']
ABSTRACT=['empathy','pressure','noise','uncertainty','confusion','stress','fatigue','delay']
PLURAL=['conflicts','errors','delays','failures','problems','mistakes','disputes','risks']


def T(w,p,r): return {'text':w,'pos':p,'role':r}
def P(ch='.'): return T(ch,'PUNCT',None)
def NP(noun,role,adj=None):
    xs=[T('the','DET',role)]
    if adj: xs.append(T(adj,'ADJ',role))
    xs.append(T(noun,'NOUN',role)); return xs

def text(ts):
    s=''
    for t in ts:
        w=t['text']
        if w in '.,?!;:': s=s.rstrip()+w
        else: s+=('' if not s else ' ')+w
    return s

def rec(ts,f): return {'text':text(ts),'family':f,'tokens':ts}

def one(i):
    s=R.choice(SUBJ); s2=R.choice([x for x in SUBJ if x!=s]); ppl=R.choice(PEOPLE); o=R.choice(OBJ); o2=R.choice([x for x in OBJ if x!=o]); a=R.choice(ADJ); ad=R.choice(ADV); pv=R.choice(PAST); bv=R.choice(BASE)
    f=i%16
    if f==0:
        x=NP(s,'S')+[T('made','VERB','V')]+NP(ppl,'O','exhausted')+[T(bv,'VERB','V')]+NP(o,'O')+[T('before','SCONJ','M')]+NP(s2,'S')+[T('arrived','VERB','V'),P()]
    elif f==1:
        x=NP(s,'S')+[T('let','VERB','V')]+NP(ppl,'O')+[T(bv,'VERB','V')]+NP(o,'O')+[T('after','SCONJ','M')]+NP(s2,'S')+[T('left','VERB','V'),P()]
    elif f==2:
        x=NP(s,'S')+[T('found','VERB','V')]+NP(o,'O')+[T(ad,'ADV','C'),T(a,'ADJ','C')]+[T('after','SCONJ','M')]+NP(s2,'S')+[T('reviewed','VERB','V')]+NP(o2,'O')+[P()]
    elif f==3:
        x=NP(s,'S')+[T('considered','VERB','V')]+NP(o,'O')+[T('too','ADV','C'),T(a,'ADJ','C'),T('to','PART','M'),T(bv,'VERB','V'),T('immediately','ADV','M'),P()]
    elif f==4:
        x=[T('Which','DET','O'),T(o,'NOUN','O'),T('did','AUX','V')]+NP(s,'S')+[T('who','PRON','S'),T(pv,'VERB','V')]+NP(o2,'O')+[T('say','VERB','V')]+NP(s2,'S')+[T('should','AUX','V'),T(bv,'VERB','V'),T('first','ADV','M'),P('?')]
    elif f==5:
        x=[T('I','PRON','S'),T('wonder','VERB','V'),T('which','DET','O'),T(o,'NOUN','O')]+NP(s,'S')+[T('that','PRON','S'),T('met','VERB','V'),T('yesterday','ADV','M'),T('will','AUX','V'),T(bv,'VERB','V'),T('tomorrow','ADV','M'),P()]
    elif f==6:
        x=NP(o,'S')+[T('that','PRON','O')]+NP(ppl,'S')+[T(pv,'VERB','V'),T('was','AUX','V'),T('approved','VERB','V'),T('after','SCONJ','M')]+NP(s,'S')+[T('checked','VERB','V')]+NP(o2,'O')+[P()]
    elif f==7:
        x=[T('It','PRON','S'),T('is','AUX','V'),T(a,'ADJ','C'),T('that','SCONJ','M')]+NP(s,'S')+[T(pv,'VERB','V')]+NP(o,'O')+[T('after','SCONJ','M')]+NP(ppl,'S')+[T('warned','VERB','V'),T('them','PRON','O'),P()]
    elif f==8:
        x=[T('It','PRON','S'),T('seems','VERB','V'),T('that','SCONJ','M')]+NP(ppl,'S')+[T('who','PRON','S'),T(pv,'VERB','V'),T(ad,'ADV','M'),T('will','AUX','V'),T(bv,'VERB','V')]+NP(o,'O')+[T('on','ADP','M'),T('time','NOUN','M'),P()]
    elif f==9:
        x=[T('Having','AUX','V'),T('finished','VERB','V')]+NP(o,'O')+[P(',')]+NP(ppl,'S')+[T(ad,'ADV','M'),T('recorded','VERB','V')]+NP(o2,'O')+[T('that','PRON','O')]+NP(s,'S')+[T('produced','VERB','V'),P()]
    elif f==10:
        x=[T('Although','SCONJ','M')]+NP(s,'S')+[T('who','PRON','S'),T('joined','VERB','V'),T('recently','ADV','M'),T('doubted','VERB','V'),T('whether','SCONJ','M')]+NP(o,'S')+[T('would','AUX','V'),T('work','VERB','V'),P(',')]+NP(s2,'S')+[T('approved','VERB','V')]+NP(o2,'O')+[T('because','SCONJ','M'),T('the','DET','S'),T('tests','NOUN','S'),T('had','AUX','V'),T('succeeded','VERB','V'),P()]
    elif f==11:
        ab=R.choice(ABSTRACT); pl=R.choice(PLURAL)
        x=[T('In','ADP','M'),T('fact','NOUN','M'),P(','),T('they','PRON','S'),T('argue','VERB','V'),P(','),T(ab,'NOUN','S'),T('makes','VERB','V'),T('such','DET','O'),T(pl,'NOUN','O'),T(a,'ADJ','C'),P()]
    elif f==12:
        x=[T('Can','AUX','V')]+NP(s,'S')+[T('who','PRON','S'),T(pv,'VERB','V')]+NP(o,'O')+[T('explain','VERB','V'),T('why','ADV','M')]+NP(o2,'S')+[T('stopped','VERB','V'),T('working','VERB','V'),P('?')]
    elif f==13:
        x=NP(s,'S')+[T('gave','VERB','V')]+NP(ppl,'O')+NP(o,'O','difficult')+[T('before','SCONJ','M')]+NP(s2,'S')+[T('left','VERB','V'),P()]
    elif f==14:
        x=[T('How','ADV','M'),T(a,'ADJ','C'),T('is','AUX','V')]+NP(o,'S')+[T('when','SCONJ','M')]+NP(s,'S')+[T('tests','VERB','V')]+NP(o2,'O')+[P('?')]
    else:
        x=NP(s,'S')+[T('said','VERB','V'),T('that','SCONJ','M')]+NP(ppl,'S')+[T('understood','VERB','V'),T('what','PRON','O')]+NP(o,'S')+[T('needed','VERB','V'),T('before','SCONJ','M')]+NP(o2,'S')+[T('could','AUX','V'),T('be','AUX','V'),T('finished','VERB','V'),P()]
    return rec(x,f'gold_v2_{f:02d}')

def generate(n,start=0,forbidden=None):
    forbidden=set(forbidden or ()); seen=set(); out=[]; i=start
    while len(out)<n:
        x=one(i); i+=1
        if x['text'] in forbidden or x['text'] in seen: continue
        seen.add(x['text']); out.append(x)
    return out

def write(path,rows):
    with open(path,'w',encoding='utf-8') as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    train=generate(18000,0)
    val=generate(4000,900000,{x['text'] for x in train})
    write(OUT/'gold_v2_train_18000.jsonl',train); write(OUT/'gold_v2_val_4000.jsonl',val)
    fam={}
    for r in train: fam[r['family']]=fam.get(r['family'],0)+1
    meta={'train':len(train),'validation':len(val),'families':fam,'sealed_holdouts_included':False,'label_source':'deterministic human-designed grammar templates','seed':79191}
    (OUT/'gold_v2_manifest.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(meta)
