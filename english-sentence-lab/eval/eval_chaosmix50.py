#!/usr/bin/env python3
from __future__ import annotations

import json, sys
from collections import Counter, defaultdict
from pathlib import Path

import spacy
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'train'))
import train_ud_role as base

DATA = ROOT / 'data' / 'chaoslike200' / 'ChaosMix50_ORIGINAL.json'
AUTO_MODEL = ROOT / 'artifacts' / 'v1.8.3_auto_promoted_silver_role.pt'
CORE_MODEL = ROOT / 'artifacts' / 'v1.8.2_r012_school_regression_role.pt'
MODEL = AUTO_MODEL if AUTO_MODEL.exists() else CORE_MODEL
OUT = ROOT / 'artifacts' / 'v1.8.0_chaosmix50_eval.json'
SUMMARY = ROOT / 'artifacts' / 'v1.8.0_chaosmix50_eval.txt'

# Sparse human/LLM-audited focus gold under docs/role_label_spec_v1.md.
# tuple = (exact token text, zero-based occurrence among case-insensitive matches, expected role)
GOLD = {
    'CM50-001':[('engineer',0,'S'),('whom',0,'O'),('board',0,'S'),('prototype',0,'S'),('success',0,'C')],
    'CM50-002':[('committee',0,'S'),('whom',0,'O'),('exception',0,'S'),('anyone',0,'S'),('increase',0,'O')],
    'CM50-003':[('What',0,'O'),('witnesses',0,'S'),('door',0,'S'),('sensors',0,'S'),('camera',0,'S')],
    'CM50-004':[('researcher',0,'S'),('measurements',0,'S'),('copy',0,'O'),('we',0,'S'),('anomaly',0,'S')],
    'CM50-005':[('translator',0,'S'),('pages',0,'S'),('negation',0,'S'),('team',0,'S'),('meaning',0,'S')],
    'CM50-006':[('analysts',0,'S'),('demand',0,'S'),('surge',0,'S'),('investors',0,'S'),('wrong',0,'C')],
    'CM50-007':[('whoever',0,'S'),('meeting',0,'O'),('interview',0,'S'),('dean',0,'S'),('professor',0,'S')],
    'CM50-008':[('report',0,'S'),('what',0,'O'),('footnote',0,'O'),('scale',0,'S'),('questions',0,'O')],
    'CM50-009':[('device',0,'S'),('manual',0,'S'),('technician',0,'S'),('light',0,'S'),('power',0,'O')],
    'CM50-010':[('It',0,'S'),('rumor',0,'C'),('manager',0,'S'),('orders',0,'S'),('workers',0,'O')],
    'CM50-011':[('Whoever',0,'S'),('curator',0,'O'),('painting',0,'O'),('space',0,'S'),('restoration',0,'O')],
    'CM50-012':[('agreement',0,'S'),('side',0,'S'),('lawyer',0,'S'),('engineer',0,'O'),('product',0,'S')],
    'CM50-013':[('what',0,'O'),('algorithm',0,'S'),('evidence',0,'O'),('model',0,'O'),('ones',0,'C')],
    'CM50-014':[('director',0,'S'),('delay',0,'S'),('shipment',0,'S'),('storm',0,'S'),('someone',0,'M')],
    'CM50-015':[('generator',0,'S'),('technicians',0,'S'),('update',0,'S'),('controller',0,'O'),('pumps',0,'S')],
    'CM50-016':[('student',0,'S'),('whom',0,'O'),('proof',0,'S'),('counterexample',0,'O'),('assumption',0,'O')],
    'CM50-017':[('committee',0,'S'),('result',0,'O'),('replication',0,'S'),('it',0,'S'),('interval',0,'S')],
    'CM50-018':[('it',0,'S'),('machine',0,'S'),('records',0,'S'),('that',0,'S'),('step',0,'S')],
    'CM50-019':[('it',0,'S'),('intern',0,'M'),('timestamps',0,'S'),('team',0,'S'),('sequence',0,'S')],
    'CM50-020':[('Whatever',0,'O'),('witness',0,'S'),('reconstruction',0,'S'),('behind',0,'M'),('fact',0,'O')],
    'CM50-021':[('contract',0,'O'),('clause',0,'S'),('supplier',0,'O'),('what',0,'S'),('compromise',0,'C')],
    'CM50-022':[('There',0,'S'),('record',0,'C'),('who',0,'S'),('investigators',0,'S'),('value',0,'S')],
    'CM50-023':[('editor',0,'S'),('claim',0,'O'),('error',0,'S'),('punctuation',0,'S'),('coincidence',0,'O')],
    'CM50-024':[('Few',0,'S'),('who',0,'S'),('city',0,'S'),('model',0,'S'),('bridge',0,'O')],
    'CM50-025':[('telescope',0,'S'),('pattern',0,'S'),('astronomers',0,'S'),('regularity',0,'S'),('effect',0,'O')],
    'CM50-026':[('package',0,'S'),('samples',0,'O'),('reactor',0,'S'),('logger',0,'S'),('gap',0,'O')],
    'CM50-027':[('policy',0,'S'),('information',0,'M'),('categories',0,'S'),('identifier',0,'S'),('metadata',0,'M')],
    'CM50-028':[('mathematician',0,'S'),('shortcut',0,'O'),('sequence',0,'S'),('experiments',0,'S'),('cases',0,'O')],
    'CM50-029':[('spokesperson',0,'S'),('decision',0,'S'),('email',0,'S'),('assistant',0,'M'),('employees',0,'O')],
    'CM50-030':[('What',0,'S'),('archive',0,'O'),('dates',0,'S'),('clerks',0,'S'),('record',0,'S')],
    'CM50-031':[('survey',0,'S'),('audience',0,'O'),('conclusion',0,'S'),('residents',0,'S'),('assumption',0,'M')],
    'CM50-032':[('witness',0,'S'),('alarm',0,'O'),('sensor',0,'S'),('timeline',0,'S'),('assumption',0,'S')],
    'CM50-033':[('parser',0,'S'),('clause',0,'O'),('what',1,'S'),('sentences',0,'O'),('question',0,'O')],
    'CM50-034':[('claim',0,'S'),('critics',0,'S'),('river',0,'S'),('photograph',0,'M'),('shadow',0,'S')],
    'CM50-035':[('fact',0,'S'),('simulation',0,'S'),('model',0,'S'),('us',0,'O'),('mechanism',0,'S')],
    'CM50-036':[('supplier',0,'S'),('component',0,'O'),('factory',0,'S'),('regulator',0,'S'),('waiver',0,'O')],
    'CM50-037':[('report',0,'S'),('exception',0,'S'),('review',0,'S'),('process',0,'O'),('person',0,'O')],
    'CM50-038':[('it',0,'S'),('teams',0,'S'),('possibility',0,'S'),('someone',0,'S'),('both',0,'S')],
    'CM50-039':[('department',0,'M'),('complaint',0,'S'),('office',0,'S'),('it',0,'O'),('deadline',0,'S')],
    'CM50-040':[('experiment',0,'S'),('test',0,'C'),('material',0,'S'),('protocol',0,'S'),('sensors',0,'O')],
    'CM50-041':[('message',0,'S'),('server',0,'S'),('process',0,'S'),('sequence',0,'S'),('causation',0,'O')],
    'CM50-042':[('distinction',0,'S'),('witness',0,'S'),('interviewer',0,'S'),('answers',0,'O'),('phrases',0,'S')],
    'CM50-043':[('reason',0,'S'),('redesign',0,'S'),('components',0,'O'),('load',0,'O'),('inspections',0,'O')],
    'CM50-044':[('Whatever',0,'S'),('it',0,'S'),('proposal',0,'M'),('forecast',0,'O'),('difference',0,'S')],
    'CM50-045':[('samples',0,'M'),('controls',0,'M'),('curve',0,'M'),('there',0,'S'),('little',0,'S')],
    'CM50-046':[('rule',0,'S'),('definition',0,'S'),('records',0,'S'),('it',0,'S'),('deals',0,'O')],
    'CM50-047':[('machine',0,'S'),('lever',0,'O'),('operator',0,'S'),('logs',0,'S'),('prediction',0,'O')],
    'CM50-048':[('anyone',0,'S'),('sensor',0,'S'),('readings',0,'S'),('team',0,'S'),('what',0,'S')],
    'CM50-049':[('It',0,'S'),('committee',0,'S'),('members',0,'S'),('minutes',0,'S'),('reasons',0,'S')],
    'CM50-050':[('designers',0,'S'),('fact',0,'O'),('rarity',0,'S'),('filter',0,'S'),('metadata',1,'S')],
}


def locate(doc, text: str, occurrence: int):
    hits = [i for i, t in enumerate(doc) if t.text.lower() == text.lower()]
    if occurrence >= len(hits):
        raise RuntimeError(f'focus token not found: {text!r} occurrence={occurrence}; hits={hits}')
    return hits[occurrence]


def score(rows, key):
    correct = sum(r[key] == r['gold'] for r in rows)
    exact = 0
    by_sent = defaultdict(list)
    for r in rows:
        by_sent[r['id']].append(r)
    for rs in by_sent.values():
        exact += int(all(r[key] == r['gold'] for r in rs))
    by_role = {}
    for role in ['S','V','O','C','M']:
        rr = [r for r in rows if r['gold'] == role]
        if rr:
            c = sum(r[key] == role for r in rr)
            by_role[role] = {'checks':len(rr),'correct':c,'accuracy':c/len(rr)}
    return {'checks':len(rows),'correct':correct,'accuracy':correct/len(rows),'exact_sentences':exact,'exact_sentence_accuracy':exact/len(by_sent),'by_gold_role':by_role}


def main():
    torch.set_num_threads(4)
    data = json.loads(DATA.read_text(encoding='utf-8'))
    sentences = data['sentences']
    if len(sentences) != 50 or set(GOLD) != {s['id'] for s in sentences}:
        raise RuntimeError('ChaosMix50 cardinality/id mismatch')
    if sum(map(len, GOLD.values())) != 250:
        raise RuntimeError('Gold focus check count must be 250')

    nlp = spacy.load('en_core_web_sm')
    ck = torch.load(MODEL, map_location='cpu', weights_only=False)
    model = base.RoleNet().cpu(); model.load_state_dict(ck['model'], strict=True); model.eval()

    rows = []
    with torch.no_grad():
        for s in sentences:
            doc = nlp(s['sentence'])
            toks = [{'text':t.text, 'pos':t.pos_} for t in doc]
            broles = base.weak_base_roles(toks)
            feats = [base.feat_token(t,b) for t,b in zip(toks,broles)]
            dummy = [0] * len(feats)
            b,y,m = base.collate([(feats,dummy,'','chaosmix50')], torch.device('cpu'))
            logits = model(b,m)[0,:len(feats)]
            probs = torch.softmax(logits,dim=-1)
            conf,pred = probs.max(dim=-1)
            neural = [base.I2ROLE[int(i)] for i in pred.tolist()]
            confidence = [float(x) for x in conf.tolist()]
            hybrid = [n if c >= 0.75 else br for n,c,br in zip(neural,confidence,broles)]
            for text,occ,gold in GOLD[s['id']]:
                i = locate(doc,text,occ)
                rows.append({
                    'id':s['id'],'token':doc[i].text,'occurrence':occ,'gold':gold,
                    'pos':doc[i].pos_,'dep':doc[i].dep_,'head':doc[i].head.text,
                    'weak_base':broles[i],'neural_direct':neural[i],
                    'confidence':round(confidence[i],6),'hybrid75':hybrid[i],
                })

    modes = {k:score(rows,k) for k in ['weak_base','neural_direct','hybrid75']}
    errors = [r for r in rows if r['neural_direct'] != r['gold']]
    confusions = Counter((r['gold'],r['neural_direct']) for r in errors)
    result = {
        'model':ck.get('metrics',{}).get('version','unknown'),
        'checkpoint':MODEL.name,
        'dataset':'ChaosMix50_ORIGINAL',
        'sentences':50,
        'focus_checks':250,
        'training_contamination':False,
        'benchmark_role':'development_stress_set',
        'postprocess_or_rule_tuning_seen':True,
        'frontend':'spaCy en_core_web_sm POS/tokenization + existing RoleNet feature path',
        'modes':modes,
        'neural_error_count':len(errors),
        'neural_confusions':[{'gold':a,'pred':b,'count':n} for (a,b),n in confusions.most_common()],
        'neural_errors':errors,
    }
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines = [
        f"SentenceLab {ck.get('metrics',{}).get('version','unknown')} — ChaosMix50 development stress evaluation",
        'Evaluation-only: 50 sentences / 250 sparse canonical-role focus checks',
    ]
    for name in ['weak_base','neural_direct','hybrid75']:
        x=modes[name]
        lines.append(f"{name}: {x['correct']}/{x['checks']} = {x['accuracy']*100:.2f}% | exact {x['exact_sentences']}/50")
    lines.append('Top neural confusions: ' + ', '.join(f'{a}->{b}:{n}' for (a,b),n in confusions.most_common(8)))
    SUMMARY.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
