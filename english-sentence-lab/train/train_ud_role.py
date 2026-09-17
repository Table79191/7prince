#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, random, hashlib, time
from collections import defaultdict, Counter
from pathlib import Path
import torch
import torch.nn as nn

ROLE2I={None:0,'S':1,'V':2,'O':3,'C':4,'M':5}
I2ROLE=[None,'S','V','O','C','M']
POS_LIST=['UNK','ADJ','ADP','ADV','AUX','CCONJ','DET','INTJ','NOUN','NUM','PART','PRON','PROPN','PUNCT','SCONJ','SYM','VERB','X']
POS2I={x:i for i,x in enumerate(POS_LIST)}
CLAUSE_BOUNDARY={'acl','acl:relcl','advcl','ccomp','xcomp','parataxis'}

def fnv1a(s):
    h=2166136261
    for b in s.encode('utf-8','ignore'):
        h ^= b; h=(h*16777619)&0xffffffff
    return h

class AttentionBlock(nn.Module):
    def __init__(self,d_model=128,heads=4,dropout=.08):
        super().__init__(); self.attn=nn.MultiheadAttention(d_model,heads,batch_first=True,dropout=dropout)
        self.n1=nn.LayerNorm(d_model)
        self.ff=nn.Sequential(nn.Linear(d_model,192),nn.GELU(),nn.Dropout(dropout),nn.Linear(192,d_model))
        self.n2=nn.LayerNorm(d_model)
    def forward(self,x,mask):
        a,_=self.attn(x,x,x,key_padding_mask=~mask,need_weights=False)
        x=self.n1(x+a); return self.n2(x+self.ff(x))

class RoleNet(nn.Module):
    def __init__(self):
        super().__init__(); self.word=nn.Embedding(8192,32); self.pre=nn.Embedding(1024,8); self.suf=nn.Embedding(1024,8)
        self.pos=nn.Embedding(len(POS_LIST),16); self.brole=nn.Embedding(6,8); self.shape=nn.Linear(8,16); self.proj=nn.Linear(88,96)
        self.gru=nn.GRU(96,64,num_layers=3,batch_first=True,bidirectional=True)
        self.blocks=nn.ModuleList([AttentionBlock(128,4,.08)]); self.out=nn.Linear(128,6)
    def forward(self,b,mask):
        x=torch.cat([self.word(b['wid']),self.pre(b['pre']),self.suf(b['suf']),self.pos(b['pos']),self.brole(b['role']),torch.tanh(self.shape(b['shape']))],-1)
        x=torch.nn.functional.gelu(self.proj(x)); x,_=self.gru(x)
        for block in self.blocks: x=block(x,mask)
        return self.out(x)

def parse_conllu(path):
    sent=[]; meta={}
    def flush():
        nonlocal sent,meta
        if not sent: return None
        out=(meta,sent); sent=[]; meta={}; return out
    with open(path,encoding='utf-8') as f:
      for raw in f:
        line=raw.rstrip('\n')
        if not line:
            x=flush()
            if x: yield x
            continue
        if line.startswith('#'):
            if line.startswith('# text = '): meta['text']=line[9:]
            elif line.startswith('# sent_id = '): meta['sent_id']=line[12:]
            continue
        c=line.split('\t')
        if len(c)!=10 or '-' in c[0] or '.' in c[0]: continue
        try: tid=int(c[0]); head=int(c[6])
        except ValueError: continue
        sent.append({'id':tid,'text':c[1],'lemma':c[2],'pos':c[3],'feats':c[5],'head':head,'deprel':c[7]})
    x=flush()
    if x: yield x

def phrase_roles(tokens):
    id2i={t['id']:i for i,t in enumerate(tokens)}; ch=defaultdict(list)
    for i,t in enumerate(tokens):
        if t['head'] in id2i: ch[id2i[t['head']]].append(i)
    direct={}; cop_parents=set()
    for i,t in enumerate(tokens):
        base=t['deprel'].split(':',1)[0]
        if base in {'nsubj','csubj'}: direct[i]='S'
        elif base in {'obj','iobj'}: direct[i]='O'
        if base=='cop' and t['head'] in id2i: cop_parents.add(id2i[t['head']])
    for i in cop_parents: direct[i]='C'
    for i,t in enumerate(tokens):
        if t['deprel'].split(':',1)[0]=='xcomp' and t['pos'] in {'ADJ','NOUN','PROPN','PRON','NUM'}: direct[i]='C'
    roles=[None]*len(tokens)
    for root,role in sorted(direct.items(),key=lambda kv:{'S':0,'O':1,'C':2}[kv[1]]):
        stack=[root]; seen=set()
        while stack:
            i=stack.pop()
            if i in seen: continue
            seen.add(i)
            if i!=root and i in direct: continue
            if roles[i] is None: roles[i]=role
            for j in ch.get(i,[]):
                rel=tokens[j]['deprel']; base=rel.split(':',1)[0]
                if rel in CLAUSE_BOUNDARY or base in {'ccomp','xcomp','advcl','parataxis'}: continue
                stack.append(j)
    for i,t in enumerate(tokens):
        if t['pos'] in {'VERB','AUX'}: roles[i]='V'
    for i in cop_parents:
        if tokens[i]['pos'] not in {'VERB','AUX'}: roles[i]='C'
    for i,r in direct.items():
        if not (r=='C' and tokens[i]['pos'] in {'VERB','AUX'}): roles[i]=r
    for i,t in enumerate(tokens):
        if t['pos']=='PUNCT': roles[i]=None
        elif roles[i] is None: roles[i]='M'
    return roles

def weak_base_roles(tokens):
    out=[]; seen_pred=False
    for t in tokens:
        p=t['pos']
        if p in {'VERB','AUX'}: out.append('V'); seen_pred=True
        elif p=='PUNCT': out.append(None)
        elif p in {'NOUN','PROPN','PRON'}: out.append('S' if not seen_pred else 'O')
        else: out.append('M')
    return out

def feat_token(t,base_role):
    w=t['text']; lo=w.lower()
    return (fnv1a(lo)%8192,fnv1a(lo[:3])%1024,fnv1a(lo[-3:])%1024,POS2I.get(t['pos'],0),ROLE2I.get(base_role,0),[
        float(w[:1].isupper()),float(w.isupper() and any(c.isalpha() for c in w)),float(any(c.isdigit() for c in w)),float('-' in w),
        float(lo.endswith('ing')),float(lo.endswith('ed')),float(lo.endswith('ly')),min(len(w),20)/20.0])

def load_examples(data_root,max_per_corpus=12000,max_len=160):
    train=[]; val=[]; per=Counter()
    for path in sorted(Path(data_root).rglob('*.conllu')):
        corpus=path.parent.name; split='train' if '-train.' in path.name else ('dev' if '-dev.' in path.name else 'test')
        candidates=[]
        for meta,toks in parse_conllu(path):
            if not (2<=len(toks)<=max_len): continue
            gold=phrase_roles(toks); base=weak_base_roles(toks)
            feats=[feat_token(t,b) for t,b in zip(toks,base)]; labels=[ROLE2I[r] for r in gold]
            candidates.append((feats,labels,meta.get('text',''),corpus))
        random.Random(79191+len(corpus)).shuffle(candidates)
        if split=='train':
            selected=candidates[:max_per_corpus]; train.extend(selected); per[(corpus,'train')]+=len(selected)
        elif any((path.parent/f).exists() for f in [path.name.replace('-test.','-train.'),path.name.replace('-dev.','-train.')]):
            selected=candidates[:max(500,min(len(candidates),2000))]; val.extend(selected); per[(corpus,'val')]+=len(selected)
        else:
            for ex in candidates[:max_per_corpus]:
                key=ex[2].encode('utf-8'); bucket=int(hashlib.sha1(key).hexdigest()[:8],16)%100
                (train if bucket<85 else val).append(ex); per[(corpus,'train' if bucket<85 else 'val')]+=1
    return train,val,per

def collate(items,device):
    L=max(len(x[0]) for x in items); B=len(items)
    wid=torch.zeros(B,L,dtype=torch.long); pre=wid.clone(); suf=wid.clone(); pos=wid.clone(); role=wid.clone(); y=wid.clone()
    shape=torch.zeros(B,L,8); mask=torch.zeros(B,L,dtype=torch.bool)
    for i,(fs,ys,*_) in enumerate(items):
        n=len(fs); mask[i,:n]=True; y[i,:n]=torch.tensor(ys)
        for j,(a,b,c,d,e,sh) in enumerate(fs):
            wid[i,j]=a; pre[i,j]=b; suf[i,j]=c; pos[i,j]=d; role[i,j]=e; shape[i,j]=torch.tensor(sh)
    return {k:v.to(device) for k,v in {'wid':wid,'pre':pre,'suf':suf,'pos':pos,'role':role,'shape':shape}.items()},y.to(device),mask.to(device)

def evaluate(model,data,device,batch=32):
    model.eval(); total=correct=base=0; exact=0
    with torch.no_grad():
        for st in range(0,len(data),batch):
            items=data[st:st+batch]; b,y,m=collate(items,device); p=model(b,m).argmax(-1)
            total+=m.sum().item(); correct+=((p==y)&m).sum().item(); base+=((b['role']==y)&m).sum().item()
            for i,it in enumerate(items):
                n=len(it[0]); exact+=int(torch.equal(p[i,:n],y[i,:n]))
    return {'sentences':len(data),'tokens':total,'base_role_acc':base/total if total else 0,'neural_role_acc':correct/total if total else 0,'sentence_exact':exact}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--data',default='data/ud'); ap.add_argument('--out',default='artifacts/v1.7.0_ud_role.pt'); ap.add_argument('--metrics',default='artifacts/v1.7.0_ud_metrics.json')
    ap.add_argument('--epochs',type=int,default=1); ap.add_argument('--batch',type=int,default=32); ap.add_argument('--chunk-sentences',type=int,default=250); ap.add_argument('--max-per-corpus',type=int,default=12000); args=ap.parse_args()
    torch.set_num_threads(4); random.seed(79191); torch.manual_seed(79191); device=torch.device('cpu')
    train,val,per=load_examples(args.data,args.max_per_corpus)
    print('train',len(train),'val',len(val),'distribution',dict((f'{a}:{b}',n) for (a,b),n in per.items()))
    model=RoleNet().to(device); opt=torch.optim.AdamW(model.parameters(),lr=1.1e-3,weight_decay=2e-4)
    weights=torch.tensor([0.35,0.75,0.9,1.05,1.6,0.8],device=device); lossfn=nn.CrossEntropyLoss(weight=weights,reduction='none')
    logs=[]; rng=random.Random(79191)
    for ep in range(args.epochs):
        rng.shuffle(train); model.train(); seen=0
        for chunk_start in range(0,len(train),args.chunk_sentences):
            chunk=train[chunk_start:chunk_start+args.chunk_sentences]; t0=time.time(); tok=cor=base=0; lsum=0.0
            for st in range(0,len(chunk),args.batch):
                items=chunk[st:st+args.batch]; b,y,m=collate(items,device); opt.zero_grad(set_to_none=True); z=model(b,m)
                raw=lossfn(z.view(-1,6),y.view(-1)).view_as(y); loss=(raw*m).sum()/m.sum(); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step()
                with torch.no_grad():
                    p=z.argmax(-1); n=m.sum().item(); tok+=n; cor+=((p==y)&m).sum().item(); base+=((b['role']==y)&m).sum().item(); lsum+=loss.item()*n
            seen+=len(chunk); rec={'epoch':ep+1,'sentences_seen':seen,'loss':lsum/tok,'train_acc':cor/tok,'base_acc':base/tok,'seconds':time.time()-t0}; logs.append(rec); print(rec)
            out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
            torch.save({'model':model.state_dict(),'config':{'gru':3,'attn':1,'source':'UD-bootstrap','roles':I2ROLE},'progress':{'epoch':ep+1,'sentences_seen':seen}},out.with_name('latest.pt'))
    metrics={'version':'1.7.0-UD-BOOTSTRAP','params':sum(p.numel() for p in model.parameters()),'train_sentences':len(train),'validation':evaluate(model,val,device,args.batch),'distribution':{f'{a}:{b}':n for (a,b),n in per.items()},'last_chunks':logs[-12:]}
    out=Path(args.out); torch.save({'model':model.state_dict(),'config':{'gru':3,'attn':1,'source':'UD-bootstrap','roles':I2ROLE},'metrics':metrics},out)
    mp=Path(args.metrics); mp.parent.mkdir(parents=True,exist_ok=True); mp.write_text(json.dumps(metrics,indent=2),encoding='utf-8'); print(json.dumps(metrics,indent=2))
if __name__=='__main__': main()
