#!/usr/bin/env python3
from __future__ import annotations

import json, sys
from collections import Counter
from pathlib import Path

import spacy
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'train'))

import eval_chaosmix50 as e
import eval_chaosmix50_audited  # applies audited GOLD corrections to e.GOLD
from spacy_role_postprocess import postprocess_roles

OUT = ROOT / 'artifacts' / 'r013_chaosmix50_eval.json'
SUMMARY = ROOT / 'artifacts' / 'r013_chaosmix50_eval.txt'
MODEL = ROOT / 'artifacts' / 'v1.8.2_r012_school_regression_role.pt'


def main():
    torch.set_num_threads(4)
    data = json.loads(e.DATA.read_text(encoding='utf-8'))
    sentences = data['sentences']
    if len(sentences) != 50 or sum(map(len,e.GOLD.values())) != 250:
        raise RuntimeError('ChaosMix50 audited gold mismatch')

    nlp = spacy.load('en_core_web_sm')
    ck = torch.load(MODEL,map_location='cpu',weights_only=False)
    model = e.base.RoleNet().cpu(); model.load_state_dict(ck['model'],strict=True); model.eval()

    rows=[]
    with torch.no_grad():
        for s in sentences:
            doc=nlp(s['sentence'])
            toks=[{'text':t.text,'pos':t.pos_} for t in doc]
            broles=e.base.weak_base_roles(toks)
            feats=[e.base.feat_token(t,b) for t,b in zip(toks,broles)]
            dummy=[0]*len(feats)
            b,y,m=e.base.collate([(feats,dummy,'','chaosmix50-current')],torch.device('cpu'))
            probs=torch.softmax(model(b,m)[0,:len(feats)],dim=-1)
            conf,pred=probs.max(dim=-1)
            neural=[e.base.I2ROLE[int(i)] for i in pred.tolist()]
            confidence=[float(x) for x in conf.tolist()]
            guarded,reasons=postprocess_roles(doc,neural)
            for text,occ,gold in e.GOLD[s['id']]:
                i=e.locate(doc,text,occ)
                h=doc[i].head
                rows.append({
                    'id':s['id'],'token':doc[i].text,'occurrence':occ,'gold':gold,
                    'pos':doc[i].pos_,'tag':doc[i].tag_,'dep':doc[i].dep_,
                    'head':h.text,'head_pos':h.pos_,'head_tag':h.tag_,
                    'head_dep':h.dep_,'head_lemma':h.lemma_,
                    'head_neural':neural[h.i],
                    'prev':doc[i-1].text if i else None,
                    'next':doc[i+1].text if i+1 < len(doc) else None,
                    'neural_direct':neural[i],'confidence':round(confidence[i],6),
                    'dep_guard':guarded[i],'guard_reason':reasons[i],
                })

    direct=e.score(rows,'neural_direct')
    guarded_score=e.score(rows,'dep_guard')
    fixed=[r for r in rows if r['neural_direct']!=r['gold'] and r['dep_guard']==r['gold']]
    regressed=[r for r in rows if r['neural_direct']==r['gold'] and r['dep_guard']!=r['gold']]
    remaining=[r for r in rows if r['dep_guard']!=r['gold']]
    conf=Counter((r['gold'],r['dep_guard']) for r in remaining)
    reasons=Counter(r['guard_reason'] for r in fixed)
    result={
        'version':'current dependency-aware postprocess',
        'base_model':ck.get('metrics',{}).get('version','unknown'),
        'benchmark_status':'development_stress_set_tuned_against_postprocess',
        'dataset':'ChaosMix50_ORIGINAL audited sparse gold',
        'training_contamination':False,
        'independent_final_holdout':False,
        'focus_checks':250,
        'before_neural_direct':direct,
        'after_dep_guard':guarded_score,
        'fixed_checks':len(fixed),
        'regressed_checks':len(regressed),
        'net_corrections':len(fixed)-len(regressed),
        'fix_reasons':dict(reasons),
        'remaining_confusions':[{'gold':a,'pred':b,'count':n} for (a,b),n in conf.most_common()],
        'fixed_examples':fixed,
        'regressed_examples':regressed,
        'remaining_errors':remaining,
    }
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=[
        'SentenceLab current — dependency-aware ChaosMix50 evaluation',
        f"before: {direct['correct']}/250 = {direct['accuracy']*100:.2f}% | exact {direct['exact_sentences']}/50",
        f"after : {guarded_score['correct']}/250 = {guarded_score['accuracy']*100:.2f}% | exact {guarded_score['exact_sentences']}/50",
        f"fixed {len(fixed)} | regressed {len(regressed)} | net +{len(fixed)-len(regressed)}",
        'remaining confusions: '+', '.join(f'{a}->{b}:{n}' for (a,b),n in conf.most_common(8)),
    ]
    SUMMARY.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
