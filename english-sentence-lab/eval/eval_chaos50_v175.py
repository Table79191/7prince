#!/usr/bin/env python3
from __future__ import annotations

import base64, gzip, json, sys
from collections import defaultdict
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'train'))
import train_ud_role as base

EVAL_DIR = ROOT / 'eval'
ART = ROOT / 'artifacts'
MODEL = ART / 'v1.7.5_gold_ewt_masc_role.pt'
BASE_B64 = EVAL_DIR / 'chaos50_base_v153.json.gz.b64'
GOLD_B64 = EVAL_DIR / 'chaos50_gold.json.gz.b64'
OUT = ART / 'v1.7.5_chaos50_eval.json'
SUMMARY = ART / 'v1.7.5_chaos50_eval.txt'


def decode_b64_json(path: Path):
    raw = gzip.decompress(base64.b64decode(path.read_text(encoding='ascii').strip()))
    return json.loads(raw.decode('utf-8'))


def eval_mode(sentences, gold, neural_roles, neural_conf, mode: str):
    total = pos_ok = role_ok = both_ok = exact = 0
    cats = defaultdict(lambda: {'checks':0,'pos':0,'role':0,'both':0,'sentences':0,'exact':0})
    improved = regressed = 0
    examples_improved=[]; examples_regressed=[]
    for s, g, preds, confs in zip(sentences, gold, neural_roles, neural_conf):
        assert s['id'] == g['id']
        toks = s['tokens']
        sent_exact = True
        c = cats[g['cat']]; c['sentences'] += 1
        for token, exp_pos, exp_role in g['f']:
            idx = next((i for i,t in enumerate(toks) if t['text'].lower() == token.lower()), None)
            if idx is None:
                raise RuntimeError(f"focus token not found: sentence={s['id']} token={token}")
            t=toks[idx]
            base_role=t['role']; nr=preds[idx]; cf=confs[idx]
            if mode=='base': final_role=base_role
            elif mode=='direct': final_role=nr
            elif mode=='hybrid75': final_role=nr if cf >= 0.75 else base_role
            else: raise ValueError(mode)
            p=(t['pos']==exp_pos); r=(final_role==exp_role); b=p and r
            total += 1; pos_ok += p; role_ok += r; both_ok += b
            c['checks'] += 1; c['pos'] += p; c['role'] += r; c['both'] += b
            sent_exact = sent_exact and b
            if mode!='base':
                before=(base_role==exp_role)
                after=r
                if (not before) and after:
                    improved += 1
                    if len(examples_improved)<20: examples_improved.append({'sentence':s['id'],'token':token,'base':base_role,'neural':nr,'confidence':cf,'gold':exp_role})
                elif before and (not after):
                    regressed += 1
                    if len(examples_regressed)<20: examples_regressed.append({'sentence':s['id'],'token':token,'base':base_role,'neural':nr,'confidence':cf,'gold':exp_role})
        exact += int(sent_exact); c['exact'] += int(sent_exact)
    return {
        'focus_checks':total,
        'pos_correct':pos_ok,'pos_accuracy':pos_ok/total,
        'role_correct':role_ok,'role_accuracy':role_ok/total,
        'both_correct':both_ok,'both_accuracy':both_ok/total,
        'exact_sentences':exact,'exact_sentence_accuracy':exact/len(sentences),
        'role_improvements_vs_base':improved,
        'role_regressions_vs_base':regressed,
        'net_role_corrections':improved-regressed,
        'categories':{k:{**v,'pos_accuracy':v['pos']/v['checks'],'role_accuracy':v['role']/v['checks'],'both_accuracy':v['both']/v['checks']} for k,v in cats.items()},
        'sample_improvements':examples_improved,
        'sample_regressions':examples_regressed,
    }


def main():
    torch.set_num_threads(4)
    data = decode_b64_json(BASE_B64)
    gold = decode_b64_json(GOLD_B64)
    sentences=data['sentences']
    if len(sentences)!=50 or len(gold)!=50:
        raise RuntimeError('Chaos50 cardinality mismatch')

    ck=torch.load(MODEL,map_location='cpu',weights_only=False)
    model=base.RoleNet().cpu(); model.load_state_dict(ck['model'],strict=True); model.eval()

    all_roles=[]; all_conf=[]
    with torch.no_grad():
        for s in sentences:
            feats=[base.feat_token({'text':t['text'],'pos':t['pos']}, t.get('role')) for t in s['tokens']]
            dummy=[0]*len(feats)
            b,y,m=base.collate([(feats,dummy,'','chaos')],torch.device('cpu'))
            logits=model(b,m)[0,:len(feats)]
            probs=torch.softmax(logits,dim=-1)
            conf,pred=probs.max(dim=-1)
            all_roles.append([base.I2ROLE[int(i)] for i in pred.tolist()])
            all_conf.append([float(x) for x in conf.tolist()])

    base_res=eval_mode(sentences,gold,all_roles,all_conf,'base')
    # Integrity check: must reproduce the original sealed v1.5.3 Chaos50 evaluation.
    expected={'focus_checks':755,'pos_correct':670,'role_correct':534,'both_correct':528,'exact_sentences':0}
    for k,v in expected.items():
        if base_res[k] != v:
            raise RuntimeError(f'baseline integrity mismatch {k}: {base_res[k]} != {v}')

    direct=eval_mode(sentences,gold,all_roles,all_conf,'direct')
    hybrid=eval_mode(sentences,gold,all_roles,all_conf,'hybrid75')
    result={
        'model':'v1.7.5-GOLD-EWT-MASC',
        'checkpoint':MODEL.name,
        'sealed_holdout':'Chaos Long50',
        'sentences':50,
        'focus_checks':755,
        'input_source':'frozen v1.5.3 parser token/POS/base-role outputs from original sealed holdout package',
        'training_contamination':False,
        'notes':['POS is frozen from v1.5.3 for apples-to-apples RoleNet comparison.','hybrid75 uses the pre-existing 0.75 confidence gate; threshold was not tuned on Chaos50.'],
        'base_v153':base_res,
        'v175_direct_neural':direct,
        'v175_hybrid75':hybrid,
    }
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=[
        'SentenceLab v1.7.5 — sealed Chaos Long50 evaluation',
        f"Base v1.5.3 role: {base_res['role_correct']}/755 = {base_res['role_accuracy']*100:.2f}% | both {base_res['both_accuracy']*100:.2f}% | exact {base_res['exact_sentences']}/50",
        f"v1.7.5 direct role: {direct['role_correct']}/755 = {direct['role_accuracy']*100:.2f}% | both {direct['both_accuracy']*100:.2f}% | exact {direct['exact_sentences']}/50 | +{direct['net_role_corrections']} net role corrections",
        f"v1.7.5 hybrid75 role: {hybrid['role_correct']}/755 = {hybrid['role_accuracy']*100:.2f}% | both {hybrid['both_accuracy']*100:.2f}% | exact {hybrid['exact_sentences']}/50 | +{hybrid['net_role_corrections']} net role corrections",
    ]
    SUMMARY.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))

if __name__=='__main__': main()
