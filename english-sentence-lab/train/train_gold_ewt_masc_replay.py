#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, random
from pathlib import Path
import torch
import torch.nn as nn
import train_ud_role as base
from train_gold_finetune import load_gold, train_epoch, clone_state
from train_gold_replay import freeze_lower

PTB_TO_UPOS = {
    'CC':'CCONJ','CD':'NUM','DT':'DET','EX':'PRON','FW':'X','IN':'ADP','JJ':'ADJ','JJR':'ADJ','JJS':'ADJ',
    'LS':'X','MD':'AUX','NN':'NOUN','NNS':'NOUN','NNP':'PROPN','NNPS':'PROPN','PDT':'DET','POS':'PART',
    'PRP':'PRON','PRP$':'DET','RB':'ADV','RBR':'ADV','RBS':'ADV','RP':'PART','SYM':'SYM','TO':'PART',
    'UH':'INTJ','WDT':'DET','WP':'PRON','WP$':'DET','WRB':'ADV',
    '.':'PUNCT',',':'PUNCT',':':'PUNCT','``':'PUNCT',"''":'PUNCT','-LRB-':'PUNCT','-RRB-':'PUNCT',
}
PROPAGATE = {'NMOD','AMOD','PMOD','NAME','TITLE'}


def ptb_to_upos(tag: str, lemma: str) -> str:
    if tag.startswith('VB'):
        return 'AUX' if lemma.lower() == 'be' else 'VERB'
    return PTB_TO_UPOS.get(tag, 'X')


def decode_bytes(data: bytes) -> str:
    for enc in ('utf-8','cp1252','iso-8859-1'):
        try: return data.decode(enc)
        except UnicodeDecodeError: pass
    return data.decode('utf-8','replace')


def parse_masc_sentence(lines):
    toks=[]
    for line in lines:
        cols=line.split('\t')
        if len(cols) < 10: return None, 'short-row'
        try: tid=int(cols[0]); head=int(cols[8])
        except ValueError: return None, 'bad-id'
        form,lemma,gpos,split_form,deprel=cols[1],cols[2],cols[3],cols[5],cols[9]
        if gpos == '_' or form == '_' or split_form == '_' or form != split_form:
            return None, 'split-or-no-gold-pos'
        if gpos == 'SU' and form == '/':
            continue
        toks.append({'id':tid,'text':form,'lemma':lemma,'gpos':gpos,'pos':ptb_to_upos(gpos,lemma),'head':head,'deprel':deprel})
    if not (2 <= len(toks) <= 160): return None, 'length'
    return toks, None


def masc_roles(tokens):
    id2i={t['id']:i for i,t in enumerate(tokens)}
    children={i:[] for i in range(len(tokens))}
    for i,t in enumerate(tokens):
        if t['head'] in id2i: children[id2i[t['head']]].append(i)
    direct={}
    for i,t in enumerate(tokens):
        rel=t['deprel'].upper()
        if rel == 'SBJ': direct[i]='S'
        elif rel == 'OBJ': direct[i]='O'
        elif rel in {'PRD','OPRD'}: direct[i]='C'
    roles=[None]*len(tokens)
    for root,role in direct.items():
        stack=[root]
        while stack:
            i=stack.pop()
            if roles[i] is None: roles[i]=role
            for j in children.get(i,[]):
                if j in direct and j != root: continue
                if tokens[j]['deprel'].upper() in PROPAGATE and tokens[j]['pos'] not in {'VERB','AUX'}:
                    stack.append(j)
    # Verbal predicates override phrase labels: clausal OBJ/PRD heads should still be V.
    for i,t in enumerate(tokens):
        if t['pos'] in {'VERB','AUX'}: roles[i]='V'
    # Re-assert nominal/adjectival direct complements/arguments.
    for i,role in direct.items():
        if tokens[i]['pos'] not in {'VERB','AUX'}: roles[i]=role
    for i,t in enumerate(tokens):
        if t['pos']=='PUNCT': roles[i]=None
        elif roles[i] is None: roles[i]='M'
    return roles


def load_masc(root: str):
    root=Path(root)
    train=[]; val=[]; stats={'files':0,'accepted':0,'train':0,'val':0,'rejected':{}}
    rejected={}
    for path in sorted(root.rglob('*.conll')):
        if '__MACOSX' in path.parts: continue
        stats['files']+=1
        text=decode_bytes(path.read_bytes())
        lines=[]
        for raw in text.splitlines()+['']:
            if raw.strip(): lines.append(raw.rstrip('\r'))
            elif lines:
                toks,reason=parse_masc_sentence(lines); lines=[]
                if toks is None:
                    rejected[reason]=rejected.get(reason,0)+1; continue
                gold=masc_roles(toks); weak=base.weak_base_roles(toks)
                feats=[base.feat_token(t,b) for t,b in zip(toks,weak)]
                labels=[base.ROLE2I[r] for r in gold]
                sent=' '.join(t['text'] for t in toks)
                ex=(feats,labels,sent,'masc')
                key=(str(path.relative_to(root))+'\n'+sent).encode('utf-8')
                bucket=int(hashlib.sha1(key).hexdigest()[:8],16)%100
                if bucket < 85: train.append(ex); stats['train']+=1
                else: val.append(ex); stats['val']+=1
                stats['accepted']+=1
    stats['rejected']=rejected
    return train,val,stats


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--base',default='artifacts/v1.7.4_gold_ewt_role.pt')
    ap.add_argument('--gold-train',default='data/gold/gold_v2_train_18000.jsonl')
    ap.add_argument('--gold-val',default='data/gold/gold_v2_val_4000.jsonl')
    ap.add_argument('--ewt',default='data/gold_external/ewt')
    ap.add_argument('--masc',default='data/gold_external/masc_conll/extracted/masc-conll/data')
    ap.add_argument('--ud',default='data/ud')
    ap.add_argument('--out',default='artifacts/v1.7.5_gold_ewt_masc_role.pt')
    ap.add_argument('--metrics',default='artifacts/v1.7.5_gold_ewt_masc_metrics.json')
    ap.add_argument('--epochs',type=int,default=2); ap.add_argument('--batch',type=int,default=32); ap.add_argument('--replay',type=int,default=8000)
    args=ap.parse_args()

    torch.set_num_threads(4); random.seed(79191); torch.manual_seed(79191); dev=torch.device('cpu')
    gold_train=load_gold(args.gold_train); gold_val=load_gold(args.gold_val)
    ewt_train,ewt_val,_=base.load_examples(args.ewt,max_per_corpus=20000)
    masc_train,masc_val,masc_stats=load_masc(args.masc)
    ud_train,ud_val,_=base.load_examples(args.ud,max_per_corpus=12000)
    rng=random.Random(79191); rng.shuffle(ud_train); replay=ud_train[:min(args.replay,len(ud_train))]
    print('MASC',masc_stats)

    ck=torch.load(args.base,map_location='cpu',weights_only=False)
    model=base.RoleNet().to(dev); model.load_state_dict(ck['model'],strict=True); freeze_lower(model)
    bg=base.evaluate(model,gold_val,dev,args.batch); be=base.evaluate(model,ewt_val,dev,args.batch); bm=base.evaluate(model,masc_val,dev,args.batch); bu=base.evaluate(model,ud_val,dev,args.batch)
    best_state=clone_state(model); best={'epoch':0,'gold':bg,'ewt':be,'masc':bm,'ud':bu}
    best_score=bg['neural_role_acc']+.65*be['neural_role_acc']+.9*bm['neural_role_acc']+.55*bu['neural_role_acc']; history=[]
    opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=4e-5,weight_decay=3e-4)
    weights=torch.tensor([0.35,0.75,0.9,1.05,1.6,0.8],device=dev); lossfn=nn.CrossEntropyLoss(weight=weights,reduction='none')

    for ep in range(1,args.epochs+1):
        mix=list(gold_train)+list(ewt_train)+list(masc_train)+list(replay); random.Random(107000+ep).shuffle(mix)
        logs=train_epoch(model,mix,opt,lossfn,dev,args.batch,250,107000+ep)
        g=base.evaluate(model,gold_val,dev,args.batch); e=base.evaluate(model,ewt_val,dev,args.batch); m=base.evaluate(model,masc_val,dev,args.batch); u=base.evaluate(model,ud_val,dev,args.batch)
        score=g['neural_role_acc']+.65*e['neural_role_acc']+.9*m['neural_role_acc']+.55*u['neural_role_acc']
        rec={'epoch':ep,'gold':g,'ewt':e,'masc':m,'ud':u,'score':score,'last_train':logs[-1]}; history.append(rec); print(rec)
        safe=(g['neural_role_acc']>=.995 and e['neural_role_acc']>=be['neural_role_acc']-.005 and u['neural_role_acc']>=bu['neural_role_acc']-.0075 and m['neural_role_acc']>=bm['neural_role_acc'])
        if safe and score>best_score:
            best_score=score; best_state=clone_state(model); best={'epoch':ep,'gold':g,'ewt':e,'masc':m,'ud':u}

    model.load_state_dict(best_state)
    metrics={'version':'1.7.5-GOLD-EWT-MASC-REPLAY','params':sum(p.numel() for p in model.parameters()),'trainable_params':sum(p.numel() for p in model.parameters() if p.requires_grad),'synthetic_gold_train_sentences':len(gold_train),'ewt_train_sentences':len(ewt_train),'masc_train_sentences':len(masc_train),'masc_eval_sentences':len(masc_val),'ud_replay_sentences':len(replay),'masc_filter_stats':masc_stats,'baseline':{'gold':bg,'ewt':be,'masc':bm,'ud':bu},'history':history,'selected':best,'sealed_project_holdouts_included':False,'source_note':'MASC-CONLL checksum-verified; 85/15 deterministic split; split-token or missing-Gold-POS sentences rejected.'}
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); torch.save({'model':model.state_dict(),'config':{'gru':3,'attn':1,'source':'v1.7.4 + synthetic-gold + EWT-gold + MASC-gold + UD-replay','roles':base.I2ROLE},'metrics':metrics},out); Path(args.metrics).write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8'); print(json.dumps(metrics,indent=2))

if __name__=='__main__': main()
