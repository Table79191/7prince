#!/usr/bin/env python3
from __future__ import annotations
import json, random
from pathlib import Path

OUT = Path(__file__).resolve().parent
R = random.Random(79191)

SUBJ = [('manager','NOUN'),('engineer','NOUN'),('teacher','NOUN'),('researcher','NOUN'),('student','NOUN'),('analyst','NOUN'),('doctor','NOUN'),('designer','NOUN'),('committee','NOUN'),('team','NOUN'),('board','NOUN'),('company','NOUN')]
PEOPLE = [('interns','NOUN'),('students','NOUN'),('workers','NOUN'),('researchers','NOUN'),('reviewers','NOUN'),('engineers','NOUN'),('editors','NOUN'),('assistants','NOUN')]
OBJECTS = [('report','NOUN'),('proposal','NOUN'),('prototype','NOUN'),('design','NOUN'),('system','NOUN'),('device','NOUN'),('experiment','NOUN'),('project','NOUN'),('plan','NOUN'),('document','NOUN'),('model','NOUN'),('sensor','NOUN')]
ADJ = [('useful','ADJ'),('reliable','ADJ'),('unsafe','ADJ'),('effective','ADJ'),('unrealistic','ADJ'),('confusing','ADJ'),('stable','ADJ'),('ready','ADJ'),('necessary','ADJ'),('incorrect','ADJ'),('harmless','ADJ'),('slippery','ADJ')]
ADV = [('carefully','ADV'),('quietly','ADV'),('quickly','ADV'),('eventually','ADV'),('probably','ADV'),('clearly','ADV'),('surprisingly','ADV'),('deliberately','ADV')]
VERBS_PAST = [('reviewed','VERB'),('tested','VERB'),('revised','VERB'),('checked','VERB'),('approved','VERB'),('rejected','VERB'),('explained','VERB'),('reported','VERB'),('noticed','VERB'),('questioned','VERB')]
VERBS_BASE = [('review','VERB'),('test','VERB'),('rewrite','VERB'),('check','VERB'),('approve','VERB'),('finish','VERB'),('explain','VERB'),('repair','VERB'),('compare','VERB'),('publish','VERB')]


def T(text,pos,role): return {'text':text,'pos':pos,'role':role}
def det(role): return T('the','DET',role)
def np(noun, role, adjective=None):
    xs=[det(role)]
    if adjective: xs.append(T(adjective[0],adjective[1],role))
    xs.append(T(noun[0],noun[1],role)); return xs

def punct(ch='.'): return T(ch,'PUNCT',None)

def join_text(tokens):
    s=''
    for t in tokens:
        w=t['text']
        if w in '.,?!;:': s=s.rstrip()+w
        else: s += ('' if not s else ' ') + w
    return s

def rec(tokens,family): return {'text':join_text(tokens),'family':family,'tokens':tokens}


def make_one(i):
    s=R.choice(SUBJ); p=R.choice(PEOPLE); o=R.choice(OBJECTS); o2=R.choice([x for x in OBJECTS if x!=o]); a=R.choice(ADJ); ad=R.choice(ADV); vp=R.choice(VERBS_PAST); vb=R.choice(VERBS_BASE)
    fam=i%16
    if fam==0: # causative + embedded adjunct clause
        x=np(s,'S')+[T('made','VERB','V')]+np(p,'O',('exhausted','ADJ'))+[T(vb[0],vb[1],'V')]+np(o,'O')+[T('before','SCONJ','M')]+np(o2,'S')+[T('was','AUX','V'),T('checked','VERB','V'),punct()]
    elif fam==1: # find O+C
        x=np(s,'S')+[T('found','VERB','V')]+np(o,'O')+[T(ad[0],ad[1],'C'),T(a[0],a[1],'C')]+[T('after','SCONJ','M')]+np(o2,'S')+[T('failed','VERB','V'),punct()]
    elif fam==2: # consider O+C + relative
        x=np(s,'S')+[T('considered','VERB','V')]+np(o,'O')+[T(a[0],a[1],'C')]+[T('because','SCONJ','M')]+np(p,'S')+[T('who','PRON','S'),T(vp[0],vp[1],'V')]+np(o2,'O')+[T('agreed','VERB','V'),punct()]
    elif fam==3: # WH object question + subject relative
        x=[T('Which','DET','O'),T(o[0],o[1],'O'),T('did','AUX','V')]+np(s,'S')+[T('who','PRON','S'),T(vp[0],vp[1],'V')]+np(o2,'O')+[T('say','VERB','V')]+np(p,'S')+[T('should','AUX','V'),T(vb[0],vb[1],'V'),T('first','ADV','M'),punct('?')]
    elif fam==4: # indirect WH + relative
        x=[T('I','PRON','S'),T('wonder','VERB','V'),T('which','DET','O'),T(o[0],o[1],'O')]+np(s,'S')+[T('that','PRON','S'),T('met','VERB','V'),T('yesterday','ADV','M'),T('will','AUX','V'),T(vb[0],vb[1],'V'),T('tomorrow','ADV','M'),punct()]
    elif fam==5: # passive + object relative
        x=np(o,'S')+[T('that','PRON','O')]+np(p,'S')+[T(vp[0],vp[1],'V'),T('was','AUX','V'),T('approved','VERB','V'),T('by','ADP','M')]+np(s,'M')+[T('after','SCONJ','M')]+np(o2,'S')+[T('was','AUX','V'),T('checked','VERB','V'),punct()]
    elif fam==6: # extraposition
        x=[T('It','PRON','S'),T('is','AUX','V'),T(a[0],a[1],'C'),T('that','SCONJ','M')]+np(s,'S')+[T(vp[0],vp[1],'V')]+np(o,'O')+[T('after','SCONJ','M')]+np(p,'S')+[T('warned','VERB','V'),T('them','PRON','O'),punct()]
    elif fam==7: # raising + relative
        x=[T('It','PRON','S'),T('seems','VERB','V'),T('that','SCONJ','M')]+np(p,'S')+[T('who','PRON','S'),T(vp[0],vp[1],'V'),T(ad[0],ad[1],'M'),T('will','AUX','V'),T(vb[0],vb[1],'V')]+np(o,'O')+[punct()]
    elif fam==8: # comparison complement
        x=np(o,'S',('new','ADJ'))+[T('is','AUX','V'),T('far','ADV','C'),T('more','ADV','C'),T(a[0],a[1],'C'),T('than','SCONJ','M')]+np(o2,'S',('old','ADJ'))+[T('was','AUX','V'),T('during','ADP','M'),T('testing','NOUN','M'),punct()]
    elif fam==9: # participial clause
        x=[T('Having','AUX','V'),T('finished','VERB','V')]+np(o,'O')+[punct(',')]+np(p,'S')+[T(ad[0],ad[1],'M'),T(vp[0],vp[1],'V')]+np(o2,'O')+[T('that','PRON','O')]+np(s,'S')+[T('produced','VERB','V'),punct()]
    elif fam==10: # although + whether
        x=[T('Although','SCONJ','M')]+np(s,'S')+[T('who','PRON','S'),T('joined','VERB','V'),T('recently','ADV','M'),T('doubted','VERB','V'),T('whether','SCONJ','M')]+np(o,'S')+[T('would','AUX','V'),T('work','VERB','V'),punct(',')]+np(p,'S')+[T('approved','VERB','V')]+np(o2,'O')+[T('because','SCONJ','M')]+np(o,'S')+[T('had','AUX','V'),T('succeeded','VERB','V'),punct()]
    elif fam==11: # parenthetical + resultative make O C
        x=[T('In','ADP','M'),T('fact','NOUN','M'),punct(',')]+np(p,'S')+[T('argue','VERB','V'),punct(',')]+np(o,'S')+[T('makes','VERB','V')]+np(o2,'O',('such','ADJ'))+[T(a[0],a[1],'C'),punct()]
    elif fam==12: # yes/no question without punctuation dependence
        x=[T('Can','AUX','V')]+np(s,'S')+[T('who','PRON','S'),T(vp[0],vp[1],'V')]+np(o,'O')+[T('explain','VERB','V'),T('why','ADV','M')]+np(o2,'S')+[T('stopped','VERB','V'),T('working','VERB','V'),punct('?')]
    elif fam==13: # double object
        x=np(s,'S')+[T('gave','VERB','V')]+np(p,'O')+np(o,'O',('difficult','ADJ'))+[T('before','SCONJ','M')]+np(o2,'S')+[T('ended','VERB','V'),punct()]
    elif fam==14: # how + adjective inversion
        x=[T('How','ADV','M'),T(a[0],a[1],'C'),T('is','AUX','V')]+np(o,'S')+[T('when','SCONJ','M')]+np(s,'S')+[T(vp[0],vp[1],'V')]+np(o2,'O')+[punct('?')]
    else: # nested that + what clause
        x=np(s,'S')+[T('said','VERB','V'),T('that','SCONJ','M')]+np(p,'S')+[T('understood','VERB','V'),T('what','PRON','O')]+np(o,'S')+[T('needed','VERB','V'),T('before','SCONJ','M')]+np(o2,'S')+[T('could','AUX','V'),T('be','AUX','V'),T(vb[0],vb[1],'V'),punct()]
    return rec(x,f'gold_{fam:02d}')


def generate(n,offset=0):
    seen=set(); out=[]; i=offset
    while len(out)<n:
        x=make_one(i); i+=1
        if x['text'] in seen: continue
        seen.add(x['text']); out.append(x)
    return out


def write_jsonl(path,rows):
    with open(path,'w',encoding='utf-8') as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    train=generate(12000,0)
    # fresh RNG stream and disjoint texts for validation
    train_text={x['text'] for x in train}; val=[]; j=500000
    while len(val)<3000:
        x=make_one(j); j+=1
        if x['text'] in train_text or any(x['text']==y['text'] for y in val): continue
        val.append(x)
    write_jsonl(OUT/'gold_train_12000.jsonl',train)
    write_jsonl(OUT/'gold_val_3000.jsonl',val)
    meta={'train':len(train),'validation':len(val),'families':16,'sealed_holdouts_included':False,'seed':79191}
    (OUT/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(meta)
