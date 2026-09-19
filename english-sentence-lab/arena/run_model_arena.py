#!/usr/bin/env python3
from __future__ import annotations

import argparse, ast, hashlib, json, math, random, re, sys, time
from collections import Counter
from pathlib import Path

import torch
import torch.nn as nn

ROOT=Path(__file__).resolve().parents[1]
TRAIN=ROOT/"train"
SCRIPTS=ROOT/"scripts"
CLAUSE=ROOT/"experiments/clause_anchor_graph_v1_01"
sys.path.insert(0,str(TRAIN))
sys.path.insert(0,str(SCRIPTS))
sys.path.insert(0,str(CLAUSE))

import train_ud_role as rbase
from canonical_roles import canonicalize_ud
from promoted_shards import iter_promoted
import model as cmodel
import data as cdata

ROLE_LABELS=[None,"S","V","O","C","M"]
R2I={r:i for i,r in enumerate(ROLE_LABELS)}
APPROVED={"ewt":1.0,"atis":0.70,"childes":0.35,"eslspok":0.70,"esl":0.70}
CORE={"S","V","O","C"}

def norm(s):
    return re.sub(r"\s+"," ",str(s).strip().lower())

def iter_jsonl(path):
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def canonical_roles(row):
    toks=row.get("analysis",{}).get("tokens",[])
    dec=canonicalize_ud(toks)
    roles=[d.role for d in dec]
    if any(r=="AMBIG" for r in roles):
        return None
    return roles

def valid_row(row):
    ana=row.get("analysis",{})
    toks=ana.get("tokens",[])
    if ana.get("status")!="auto_pass" or not (2<=len(toks)<=160):
        return False
    return canonical_roles(row) is not None

def load_pools(web_root,promoted_path):
    gold=[];dev=[];seen_train=set();seen_dev=set()
    for path in sorted(Path(web_root).glob("*.jsonl")):
        for row in iter_jsonl(path):
            if not valid_row(row):
                continue
            src=row.get("source",{})
            key=src.get("key",path.stem)
            fn=src.get("filename","")
            k=norm(row.get("text",""))
            if not k:
                continue
            if "-train." in fn and key in APPROVED and k not in seen_train:
                seen_train.add(k)
                gold.append({"row":row,"kind":"gold","weight":APPROVED[key]})
            elif "-dev." in fn and key in APPROVED and k not in seen_dev:
                seen_dev.add(k)
                dev.append({"row":row,"kind":"dev","weight":1.0})
    blocked=seen_train|seen_dev
    silver=[]
    if Path(promoted_path).exists():
        for row in iter_promoted(promoted_path):
            p=row.get("promotion",{})
            if p.get("status")!="auto_promoted_silver" or p.get("gate_version")!="PROMOTED-SILVER-1":
                continue
            k=norm(row.get("text",""))
            if not k or k in blocked or not valid_row(row):
                continue
            silver.append({"row":row,"kind":"silver","weight":0.18})
    return gold,silver,dev

def rec_key(rec):
    return hashlib.sha1(norm(rec["row"].get("text","")).encode("utf-8")).hexdigest()

def load_feed_state(outdir,silver,baseline_promoted_count=15620):
    path=Path(outdir)/"feed_state.json"
    current={rec_key(x):x for x in silver}
    if path.exists():
        try:
            state=json.loads(path.read_text(encoding="utf-8"))
            consumed=set(state.get("consumed_promoted_keys",[]))
        except Exception:
            consumed=set()
    else:
        # R015 already trained on the first 15,620 promoted rows. Anything appended
        # after that checkpoint is genuinely new arena feed and should be prioritized.
        baseline=max(0,min(int(baseline_promoted_count),len(silver)))
        consumed={rec_key(x) for x in silver[:baseline]}
    fresh=[rec for k,rec in current.items() if k not in consumed]
    return path,consumed,fresh

def save_feed_state(path,consumed,silver,total_fresh_used,last_round):
    payload={
      "version":"ARENA-HOT-FEED-1",
      "consumed_promoted_keys":sorted(consumed),
      "known_promoted_count":len(silver),
      "fresh_used_total":int(total_fresh_used),
      "last_round":int(last_round),
    }
    Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def role_item(rec,weight_scale=1.0):
    row=rec["row"]; toks=row["analysis"]["tokens"]; roles=canonical_roles(row)
    nt=rbase.normalize_surface_tokens(toks)
    weak=rbase.weak_base_roles(nt)
    feats=[rbase.feat_token(t,b) for t,b in zip(nt,weak)]
    labels=[rbase.ROLE2I[r] for r in roles]
    return (feats,labels,row.get("text",""),f'arena:{rec["kind"]}',float(rec["weight"])*weight_scale)

def clause_item(rec,weight_scale=1.0):
    ex=cdata.make_example(rec["row"],float(rec["weight"])*weight_scale)
    if ex is None:
        raise RuntimeError("validated arena row failed clause make_example")
    return ex

@torch.no_grad()
def role_predict(model,recs,device,batch_size=64):
    model.eval(); out=[]
    for st in range(0,len(recs),batch_size):
        items=[role_item(x,1.0) for x in recs[st:st+batch_size]]
        b,y,m=rbase.collate(items,device)
        p=model(b,m).argmax(-1)
        for j,rec in enumerate(recs[st:st+batch_size]):
            toks=rec["row"]["analysis"]["tokens"]; n=len(toks)
            roles=[rbase.I2ROLE[int(x)] for x in p[j,:n].tolist()]
            for i,t in enumerate(toks):
                pos=t.get("pos")
                if pos in {"VERB","AUX"}: roles[i]="V"
                elif pos=="PUNCT": roles[i]=None
            out.append(roles)
    return out

@torch.no_grad()
def clause_predict(model,recs,device,batch_size=48):
    model.eval(); all_out=[]
    for st in range(0,len(recs),batch_size):
        items=[clause_item(x,1.0) for x in recs[st:st+batch_size]]
        b,y,owner,heads,mask,w=cdata.collate(items,device)
        pids=b["pos"].detach().cpu().tolist()
        dec=cmodel.decode(model,b,mask,pids)
        all_out.extend([x.roles for x in dec])
    return all_out

def weighted_errors(gold,pred):
    err=0.0; core_err=0
    for g,p in zip(gold,pred):
        if g==p: continue
        if g in CORE:
            err+=3.0; core_err+=1
        else:
            err+=1.0
    return err,core_err

def battle(model_r,model_c,recs,device):
    rp=role_predict(model_r,recs,device)
    cp=clause_predict(model_c,recs,device)
    role_losses=[];clause_losses=[];both_wrong=[];stats=Counter()
    detail=[]
    for rec,a,b in zip(recs,rp,cp):
        g=canonical_roles(rec["row"])
        ea,ca=weighted_errors(g,a); eb,cb=weighted_errors(g,b)
        if ea<eb:
            stats["role_wins"]+=1; clause_losses.append((eb-ea,rec))
            winner="role"
        elif eb<ea:
            stats["clause_wins"]+=1; role_losses.append((ea-eb,rec))
            winner="clause"
        else:
            stats["ties"]+=1; winner="tie"
        if ea>0 and eb>0:
            both_wrong.append((max(ea,eb),rec));stats["both_wrong"]+=1
        if ea==0: stats["role_exact"]+=1
        if eb==0: stats["clause_exact"]+=1
        stats["role_weighted_error_x10"]+=int(round(ea*10))
        stats["clause_weighted_error_x10"]+=int(round(eb*10))
        detail.append((winner,ea,eb,rec))
    return role_losses,clause_losses,both_wrong,stats,detail

def role_eval(model,recs,device,batch=64):
    preds=role_predict(model,recs,device,batch)
    tok=cor=exact=0
    for rec,p in zip(recs,preds):
        g=canonical_roles(rec["row"])
        tok+=len(g); cor+=sum(a==b for a,b in zip(g,p)); exact+=int(g==p)
    return {"sentences":len(recs),"tokens":tok,"role_accuracy":cor/max(tok,1),
            "sentence_exact":exact,"sentence_exact_rate":exact/max(len(recs),1)}

@torch.no_grad()
def clause_eval(model,recs,device,batch_size=48):
    model.eval();tok=cor=exact=0;owner_ok=owner_n=0;tp=fp=fn=0
    for st in range(0,len(recs),batch_size):
        items=[clause_item(x,1.0) for x in recs[st:st+batch_size]]
        b,y,owner,heads,mask,w=cdata.collate(items,device)
        o=model(b,mask)
        pred_owner=o["owner_logits"].argmax(-1)
        pred=model.role_logits(o["hidden"],pred_owner).argmax(-1)
        # Same label-spec invariants used by decode.
        for bi,item in enumerate(items):
            n=len(item["roles"])
            for i in range(n):
                pid=int(b["pos"][bi,i])
                if pid in {cmodel.POS2I["VERB"],cmodel.POS2I["AUX"]}: pred[bi,i]=cmodel.ROLE2I["V"]
                elif pid==cmodel.POS2I["PUNCT"]: pred[bi,i]=0
        tok+=int(mask.sum());cor+=int(((pred==y)&mask).sum())
        owner_ok+=int(((pred_owner==owner)&mask).sum());owner_n+=int(mask.sum())
        hp=(torch.sigmoid(o["head_logits"])>=.45)&mask
        hg=(heads>.5)&mask
        tp+=int((hp&hg).sum());fp+=int((hp&~hg&mask).sum());fn+=int((~hp&hg&mask).sum())
        for bi,item in enumerate(items):
            n=len(item["roles"]); exact+=int(torch.equal(pred[bi,:n],y[bi,:n]))
    prec=tp/max(tp+fp,1);rec=tp/max(tp+fn,1)
    return {"sentences":len(recs),"tokens":tok,"role_accuracy":cor/max(tok,1),
            "sentence_exact":exact,"sentence_exact_rate":exact/max(len(recs),1),
            "owner_accuracy":owner_ok/max(owner_n,1),
            "clause_head_f1":2*prec*rec/max(prec+rec,1e-9)}

def role_score(m):
    return m["role_accuracy"]+0.06*m["sentence_exact_rate"]

def clause_score(m):
    return m["role_accuracy"]+0.08*m["sentence_exact_rate"]+0.06*m["owner_accuracy"]+0.04*m["clause_head_f1"]

def clone_state(model):
    return {k:v.detach().cpu().clone() for k,v in model.state_dict().items()}

def train_role(model,hard,both,replay,device,seed,batch=48):
    for module in [model.word,model.pre,model.suf,model.pos,model.brole,model.shape,model.proj]:
        for p in module.parameters(): p.requires_grad=False
    for module in [model.gru,model.blocks,model.out]:
        for p in module.parameters(): p.requires_grad=True
    rows=[]
    for margin,rec in hard[:1600]:
        rows.append(role_item(rec,min(2.1,1.25+0.08*margin)))
    for margin,rec in both[:500]:
        rows.append(role_item(rec,0.35))
    for rec in replay[:1300]:
        rows.append(role_item(rec,0.40))
    if len(rows)<64: return {"trained":False,"sentences":len(rows)}
    random.Random(seed).shuffle(rows)
    opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=1.8e-6,weight_decay=3e-4)
    weights=torch.tensor([0.35,0.78,0.92,1.08,1.72,0.78],device=device)
    lossfn=nn.CrossEntropyLoss(weight=weights,reduction="none")
    model.train();loss_sum=den_sum=0.0
    for st in range(0,len(rows),batch):
        items=rows[st:st+batch];b,y,m=rbase.collate(items,device)
        sw=torch.tensor([float(x[4]) for x in items],device=device).unsqueeze(1)
        opt.zero_grad(set_to_none=True);z=model(b,m)
        raw=lossfn(z.reshape(-1,6),y.reshape(-1)).reshape_as(y);wm=m.float()*sw
        den=wm.sum().clamp_min(1.0);loss=(raw*wm).sum()/den
        loss.backward();nn.utils.clip_grad_norm_(model.parameters(),0.85);opt.step()
        loss_sum+=float(loss)*float(den);den_sum+=float(den)
    return {"trained":True,"sentences":len(rows),"loss":loss_sum/max(den_sum,1.0)}

def clause_class_weights(items,device):
    c=Counter()
    for x in items:c.update(x["roles"])
    counts=torch.tensor([max(c.get(i,0),1) for i in range(6)],dtype=torch.float32,device=device)
    freq=counts/counts.sum();w=torch.sqrt(freq.mean()/freq);w=torch.clamp(w,.50,2.50)
    w[cmodel.ROLE2I["C"]]*=1.12;w=w/w.mean()
    return w

def train_clause(model,hard,both,replay,device,seed,batch=32):
    rows=[]
    for margin,rec in hard[:1600]:
        rows.append(clause_item(rec,min(2.0,1.20+0.07*margin)))
    for margin,rec in both[:500]:
        rows.append(clause_item(rec,0.35))
    for rec in replay[:1300]:
        rows.append(clause_item(rec,0.40))
    if len(rows)<64:return {"trained":False,"sentences":len(rows)}
    random.Random(seed).shuffle(rows)
    cw=clause_class_weights(rows,device)
    role_loss=nn.CrossEntropyLoss(weight=cw,reduction="none")
    head_loss=nn.BCEWithLogitsLoss(reduction="none")
    opt=torch.optim.AdamW(model.parameters(),lr=2.0e-5,weight_decay=2e-4)
    model.train();loss_sum=den_sum=0.0
    for st in range(0,len(rows),batch):
        items=rows[st:st+batch]
        b,y,owner,heads,mask,sw=cdata.collate(items,device)
        opt.zero_grad(set_to_none=True);o=model(b,mask,gold_owner=owner)
        rl=role_loss(o["role_logits"].reshape(-1,6),y.reshape(-1)).reshape_as(y)
        hl=head_loss(o["head_logits"],heads)
        ol=nn.functional.cross_entropy(o["owner_logits"].transpose(1,2),owner,reduction="none")
        wm=mask.float()*sw.unsqueeze(1);den=wm.sum().clamp_min(1.0)
        loss=(rl*wm).sum()/den+.35*(hl*wm).sum()/den+.46*(ol*wm).sum()/den
        loss.backward();nn.utils.clip_grad_norm_(model.parameters(),0.85);opt.step()
        loss_sum+=float(loss)*float(den);den_sum+=float(den)
    return {"trained":True,"sentences":len(rows),"loss":loss_sum/max(den_sum,1.0)}

def literal_assignments(path,names):
    tree=ast.parse(Path(path).read_text(encoding="utf-8"));out={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            name=node.targets[0].id
            if name in names:out[name]=ast.literal_eval(node.value)
    return out

def hard_cases_as_recs():
    # Convert fixed hand-authored cases into pseudo rows only for evaluation.
    cases=[]
    h14=literal_assignments(CLAUSE/"novel_hard14.py",{"CASES"})["CASES"]
    f16=literal_assignments(CLAUSE/"final_blind16.py",{"CASES"})["CASES"]
    old=literal_assignments(CLAUSE/"challenge_probe.py",{"SENTENCE","TOKENS","POS","FOCUS"})
    for group,arr in [("hard14",h14),("final16",f16)]:
        for c in arr:
            cases.append((group,c))
    cases.append(("original64",{"id":"ORIGINAL_64","sentence":old["SENTENCE"],"tokens":old["TOKENS"],
                    "pos":old["POS"],"focus":{str(k):v for k,v in old["FOCUS"].items()}}))
    return cases

def hard_predict_role(model,c,device):
    toks=[{"text":w,"pos":p} for w,p in zip(c["tokens"],c["pos"])]
    nt=rbase.normalize_surface_tokens(toks);weak=rbase.weak_base_roles(nt)
    feats=[rbase.feat_token(t,b) for t,b in zip(nt,weak)]
    b,y,m=rbase.collate([(feats,[0]*len(feats),"","hard")],device)
    with torch.no_grad():pred=model(b,m)[0,:len(feats)].argmax(-1).tolist()
    roles=[rbase.I2ROLE[int(x)] for x in pred]
    for i,p in enumerate(c["pos"]):
        if p in {"VERB","AUX"}:roles[i]="V"
        elif p=="PUNCT":roles[i]=None
    return roles

def hard_predict_clause(model,c,device):
    from infer import make_batch
    b,m,pids=make_batch(c["tokens"],c["pos"])
    b={k:v.to(device) for k,v in b.items()};m=m.to(device)
    return cmodel.decode(model,b,m,pids)[0].roles

def hard_eval(model_r,model_c,device):
    agg={"role":{},"clause":{}}
    buckets=Counter()
    cor={"role":Counter(),"clause":Counter()};tot=Counter();exact={"role":Counter(),"clause":Counter()}
    for group,c in hard_cases_as_recs():
        pr=hard_predict_role(model_r,c,device);pc=hard_predict_clause(model_c,c,device)
        allr=allc=True
        for raw,g in c["focus"].items():
            i=int(raw);tot[group]+=1
            okr=pr[i]==g;okc=pc[i]==g
            cor["role"][group]+=int(okr);cor["clause"][group]+=int(okc)
            allr&=okr;allc&=okc
        exact["role"][group]+=int(allr);exact["clause"][group]+=int(allc)
    for who in ("role","clause"):
        for group in ("hard14","final16","original64"):
            agg[who][group]={"correct":cor[who][group],"total":tot[group],
                             "accuracy":cor[who][group]/max(tot[group],1),
                             "exact_sentences":exact[who][group]}
    return agg

def hard_safe(initial,current,who):
    # Safety only: never optimize against these sets, just reject broad regressions.
    vals0=[initial[who][k]["accuracy"] for k in ("hard14","final16","original64")]
    vals1=[current[who][k]["accuracy"] for k in ("hard14","final16","original64")]
    mean0=sum(vals0)/3;mean1=sum(vals1)/3
    individual=all(b>=a-0.025 for a,b in zip(vals0,vals1))
    return individual and mean1>=mean0-0.006

def deterministic_cycle(rows,round_idx,n,seed):
    if not rows:return []
    order=list(range(len(rows)));random.Random(seed).shuffle(order)
    start=((round_idx-1)*n)%len(order)
    ids=[order[(start+i)%len(order)] for i in range(min(n,len(order)))]
    return [rows[i] for i in ids]

def choose_probe(gold,silver,fresh,round_idx,n,seed):
    # Fresh promoted rows get priority, but never crowd out the trusted gold anchor.
    if fresh:
        nf=min(len(fresh),n//2)
        ng=min(len(gold),max(1,min(int(n*.40),n-nf)))
        fresh_pick=deterministic_cycle(fresh,round_idx,nf,seed+4242)
        fresh_keys={rec_key(x) for x in fresh_pick}
        old=[x for x in silver if rec_key(x) not in fresh_keys]
        no=max(0,n-len(fresh_pick)-ng)
        probe=(fresh_pick
               +deterministic_cycle(gold,round_idx,ng,seed)
               +deterministic_cycle(old,round_idx,no,seed+919))
        if len(probe)<n:
            used={id(x) for x in probe}
            fill=[x for x in gold if id(x) not in used]
            probe.extend(deterministic_cycle(fill,round_idx,n-len(probe),seed+1717))
        return probe[:n],fresh_pick
    ng=min(len(gold),max(1,int(n*.78)));ns=min(len(silver),max(0,n-ng))
    return (deterministic_cycle(gold,round_idx,ng,seed)
            +deterministic_cycle(silver,round_idx,ns,seed+919)),[]

def choose_replay(gold,round_idx,n,seed):
    return deterministic_cycle(gold,round_idx+37,n,seed+31337)

def save_ckpt(path,model,version,metrics,config_extra):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    torch.save({"model":model.state_dict(),"config":{"version":version,"roles":ROLE_LABELS,**config_extra},
                "metrics":metrics},path)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--role-start",default="artifacts/v1.8.5_r015_accumulated_final_role.pt")
    ap.add_argument("--clause-start",default="artifacts/clause_anchor_graph_v1_01_final.pt")
    ap.add_argument("--out-dir",default="artifacts/arena")
    ap.add_argument("--rounds",type=int,default=24)
    ap.add_argument("--minutes",type=int,default=300)
    ap.add_argument("--probe-per-round",type=int,default=6000)
    ap.add_argument("--baseline-promoted-count",type=int,default=15620)
    ap.add_argument("--seed",type=int,default=79191)
    a=ap.parse_args()

    torch.set_num_threads(4);random.seed(a.seed);torch.manual_seed(a.seed)
    device=torch.device("cpu");outdir=ROOT/a.out_dir;outdir.mkdir(parents=True,exist_ok=True)
    role_latest=outdir/"role_arena_latest.pt";clause_latest=outdir/"clause_arena_latest.pt"
    role_path=role_latest if role_latest.exists() else ROOT/a.role_start
    clause_path=clause_latest if clause_latest.exists() else ROOT/a.clause_start

    gold,silver,dev=load_pools(ROOT/"data/web_corpus_bot",ROOT/"data/promoted_silver/promoted.jsonl")
    if not gold or not dev:raise SystemExit("arena requires non-empty approved gold train/dev pools")

    rck=torch.load(role_path,map_location="cpu",weights_only=False)
    cck=torch.load(clause_path,map_location="cpu",weights_only=False)
    role=rbase.RoleNet().to(device);role.load_state_dict(rck["model"],strict=True)
    clause=cmodel.ClauseAnchorGraph().to(device);clause.load_state_dict(cck["model"],strict=True)

    role_dev=role_eval(role,dev,device);clause_dev=clause_eval(clause,dev,device)
    current_hard=hard_eval(role,clause,device)
    summary_path=outdir/"summary.json"
    if summary_path.exists():
        try:
            initial_hard=json.loads(summary_path.read_text(encoding="utf-8")).get("initial_hard",current_hard)
        except Exception:
            initial_hard=current_hard
    else:
        initial_hard=current_hard
    history_path=outdir/"history.jsonl"
    old_history=[]
    if history_path.exists():
        old_history=[json.loads(x) for x in history_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    start_round=(old_history[-1]["round"]+1) if old_history else 1
    feed_path,consumed_promoted,fresh=load_feed_state(outdir,silver,a.baseline_promoted_count)
    previous_feed={}
    if feed_path.exists():
        try: previous_feed=json.loads(feed_path.read_text(encoding="utf-8"))
        except Exception: previous_feed={}
    fresh_used_total=int(previous_feed.get("fresh_used_total",0))

    started=time.monotonic();new_history=[];cum=Counter()
    for local in range(a.rounds):
        if time.monotonic()-started > max(60,(a.minutes-8)*60):
            break
        rnd=start_round+local
        # This invocation sees the latest promoted snapshot supplied by the workflow.
        # Fresh rows are those never consumed by a prior arena round.
        feed_path,consumed_promoted,fresh=load_feed_state(outdir,silver,a.baseline_promoted_count)
        probe,fresh_pick=choose_probe(gold,silver,fresh,rnd,a.probe_per_round,a.seed)
        replay=choose_replay(gold,rnd,1300,a.seed)
        rloss,closs,both,stats,detail=battle(role,clause,probe,device)
        rloss.sort(key=lambda x:x[0],reverse=True);closs.sort(key=lambda x:x[0],reverse=True);both.sort(key=lambda x:x[0],reverse=True)
        cum.update(stats)

        before_r=role_dev;before_c=clause_dev
        state_r=clone_state(role);state_c=clone_state(clause)

        trr=train_role(role,rloss,both,replay,device,a.seed+rnd)
        trc=train_clause(clause,closs,both,replay,device,a.seed+10000+rnd)

        cand_r=role_eval(role,dev,device);cand_c=clause_eval(clause,dev,device)
        candidate_hard=hard_eval(role,clause,device)

        accept_r=(trr.get("trained",False)
                  and cand_r["role_accuracy"]>=before_r["role_accuracy"]-0.00015
                  and cand_r["sentence_exact_rate"]>=before_r["sentence_exact_rate"]-0.0007
                  and role_score(cand_r)>role_score(before_r)+0.00001
                  and hard_safe(initial_hard,candidate_hard,"role"))
        accept_c=(trc.get("trained",False)
                  and cand_c["role_accuracy"]>=before_c["role_accuracy"]-0.00020
                  and clause_score(cand_c)>clause_score(before_c)+0.00001
                  and hard_safe(initial_hard,candidate_hard,"clause"))

        if accept_r:
            role_dev=cand_r
        else:
            role.load_state_dict(state_r);candidate_hard["role"]=current_hard["role"]
        if accept_c:
            clause_dev=cand_c
        else:
            clause.load_state_dict(state_c);candidate_hard["clause"]=current_hard["clause"]
        current_hard=hard_eval(role,clause,device)

        rec={
          "round":rnd,"probe_sentences":len(probe),
          "probe_gold":sum(x["kind"]=="gold" for x in probe),
          "probe_silver":sum(x["kind"]=="silver" for x in probe),
          "probe_fresh_silver":len(fresh_pick),
          "fresh_available_before":len(fresh),
          "promoted_pool_at_round":len(silver),
          "battle":{"role_wins":stats["role_wins"],"clause_wins":stats["clause_wins"],
                    "ties":stats["ties"],"both_wrong":stats["both_wrong"],
                    "role_exact":stats["role_exact"],"clause_exact":stats["clause_exact"],
                    "role_weighted_error":stats["role_weighted_error_x10"]/10,
                    "clause_weighted_error":stats["clause_weighted_error_x10"]/10},
          "queues":{"role_losses":len(rloss),"clause_losses":len(closs),"both_wrong":len(both)},
          "role":{"train":trr,"accepted":accept_r,"before_dev":before_r,
                  "candidate_dev":cand_r,"selected_dev":role_dev},
          "clause":{"train":trc,"accepted":accept_c,"before_dev":before_c,
                    "candidate_dev":cand_c,"selected_dev":clause_dev},
          "hard_after_selected":current_hard,
        }
        new_history.append(rec);print(json.dumps(rec))
        for x in fresh_pick:
            consumed_promoted.add(rec_key(x))
        fresh_used_total+=len(fresh_pick)
        save_feed_state(feed_path,consumed_promoted,silver,fresh_used_total,rnd)
        history_path.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in (old_history+new_history))+"\n",encoding="utf-8")
        # Safe local checkpoints after every round, so workflow can persist progress even if a later round fails.
        save_ckpt(role_latest,role,f"R015-ARENA-R{rnd}",
                  {"arena_round":rnd,"dev":role_dev,"hard":current_hard["role"]},
                  {"family":"RoleNet","parent":"1.8.5-R015-ACCUMULATED-FINAL"})
        save_ckpt(clause_latest,clause,f"CLAUSE-ARENA-R{rnd}",
                  {"arena_round":rnd,"dev":clause_dev,"hard":current_hard["clause"]},
                  {"family":"ClauseAnchorGraph","parent":"CLAUSE-ANCHOR-GRAPH-V1.01-FINAL"})

    all_history=old_history+new_history
    history_path.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in all_history)+"\n",encoding="utf-8")
    total_rounds=all_history[-1]["round"] if all_history else 0
    summary={
      "version":"SENTENCELAB-MODEL-ARENA-1",
      "gpt_in_loop":False,
      "judge":"canonical gold/silver labels; never opponent prediction",
      "gold_train_pool":len(gold),"promoted_silver_pool":len(silver),"clean_dev_pool":len(dev),
      "hot_feed":{"enabled":True,"baseline_promoted_count":a.baseline_promoted_count,
                  "fresh_available_at_start":len(fresh),
                  "fresh_used_total":fresh_used_total,
                  "feed_state":str(feed_path.relative_to(ROOT))},
      "rounds_this_run":len(new_history),"total_rounds":total_rounds,
      "elapsed_seconds":time.monotonic()-started,
      "current":{"role_dev":role_dev,"clause_dev":clause_dev,"hard":current_hard},
      "initial_hard":initial_hard,
      "this_run_battle_totals":dict(cum),
      "accepted_role_updates":sum(x["role"]["accepted"] for x in new_history),
      "accepted_clause_updates":sum(x["clause"]["accepted"] for x in new_history),
      "latest_role_checkpoint":str(role_latest.relative_to(ROOT)),
      "latest_clause_checkpoint":str(clause_latest.relative_to(ROOT)),
      "safety":{"official_test_used_for_training":False,"hardsets_used_as_training":False,
                "hardsets_used_only_as_nonregression_floors":True,"dev_used_for_candidate_selection":True}
    }
    (outdir/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("ARENA_SUMMARY="+json.dumps(summary,ensure_ascii=False))

if __name__=="__main__":
    main()
