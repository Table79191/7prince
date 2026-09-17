#!/usr/bin/env python3
from __future__ import annotations

import bz2, hashlib, json, re, sys, urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import spacy
import stanza
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'train'))
sys.path.insert(0, str(ROOT / 'scripts'))
import train_ud_role as base
from spacy_role_postprocess import postprocess_roles

SOURCE_URL = 'https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences_CC0.tsv.bz2'
MODEL = ROOT / 'artifacts' / 'v1.8.0_r011_canonical_role.pt'
OUT_JSON = ROOT / 'artifacts' / 'tatoeba_daily500_eval.json'
OUT_TXT = ROOT / 'artifacts' / 'tatoeba_daily500_eval.txt'
OUT_TSV = ROOT / 'data' / 'tatoeba500' / 'TatoebaDaily500_CC0.tsv'
COUNT = 500
ROLES = ['S','V','O','C','M']
CORE = {'S','V','O','C'}

WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
ALLOWED_RE = re.compile(r"^[A-Za-z0-9 ,.?!'\-]+$")


def download_cc0():
    req = urllib.request.Request(SOURCE_URL, headers={'User-Agent':'SentenceLab-eval/1.0'})
    with urllib.request.urlopen(req, timeout=180) as r:
        raw = r.read()
        last_modified = r.headers.get('Last-Modified')
    return bz2.decompress(raw).decode('utf-8', errors='replace'), last_modified


def basic_candidate(text: str) -> bool:
    text = text.strip()
    words = WORD_RE.findall(text)
    if not (2 <= len(words) <= 10): return False
    if len(text) > 80: return False
    if not text.endswith(('.', '?', '!')): return False
    if sum(text.count(x) for x in '.?!') != 1: return False
    if not ALLOWED_RE.fullmatch(text): return False
    if re.search(r'https?://|www\.|@|\d', text, re.I): return False
    if any(len(w) > 15 for w in words): return False
    return True


def select_500(tsv: str, nlp):
    rows=[]
    for line in tsv.splitlines():
        parts=line.split('\t')
        if len(parts) < 3: continue
        sid, lang, text = parts[0], parts[1], parts[2].strip()
        if lang != 'eng' or not basic_candidate(text): continue
        key=hashlib.sha256((sid+'\t'+text).encode()).hexdigest()
        rows.append((key,sid,text))
    rows.sort()
    selected=[]
    for _,sid,text in rows:
        doc=nlp(text)
        if any(t.pos_ in {'PROPN','X','SYM'} for t in doc if not t.is_punct):
            continue
        alpha=[t for t in doc if t.is_alpha]
        if len(alpha) < 2 or len(alpha) > 10: continue
        selected.append((sid,text))
        if len(selected) == COUNT: break
    if len(selected) != COUNT:
        raise RuntimeError(f'could only select {len(selected)} sentences')
    return selected


def depbase(dep): return (dep or '').split(':',1)[0]


def stanza_roles(sentence):
    words=sentence.words
    by_head=defaultdict(list)
    for w in words: by_head[w.head].append(w)
    out=[]
    for w in words:
        d=depbase(w.deprel)
        up=w.upos
        if up == 'PUNCT': role=None
        elif d in {'nsubj','csubj','expl'}: role='S'
        elif d in {'obj','iobj'}: role='O'
        elif up in {'VERB','AUX'}: role='V'
        else:
            has_cop=any(depbase(ch.deprel)=='cop' for ch in by_head.get(w.id,[]))
            if has_cop and up in {'ADJ','NOUN','PROPN','PRON','NUM'}:
                role='C'
            elif d == 'xcomp' and up in {'ADJ','NOUN','PROPN'}:
                role='C'
            else:
                role='M'
        out.append((w,role))
    return out


def locate_word_spans(text, words):
    low=text.lower(); cursor=0; out=[]
    for w in words:
        piece=w.text
        idx=low.find(piece.lower(), cursor)
        if idx < 0:
            return None
        out.append((idx,idx+len(piece)))
        cursor=idx+len(piece)
    return out


def overlap(a,b,c,d): return max(0,min(b,d)-max(a,c))


def predict_roles(doc, model):
    toks=[{'text':t.text,'pos':t.pos_} for t in doc]
    broles=base.weak_base_roles(toks)
    feats=[base.feat_token(t,b) for t,b in zip(toks,broles)]
    dummy=[0]*len(feats)
    b,y,m=base.collate([(feats,dummy,'','tatoeba500')],torch.device('cpu'))
    with torch.no_grad():
        pred=torch.softmax(model(b,m)[0,:len(feats)],dim=-1).argmax(dim=-1)
    direct=[base.I2ROLE[int(i)] for i in pred.tolist()]
    guarded,reasons=postprocess_roles(doc,direct)
    return direct,guarded,reasons


def score(rows,key):
    rr=[r for r in rows if r['gold'] is not None]
    correct=sum(r[key]==r['gold'] for r in rr)
    core=[r for r in rr if r['gold'] in CORE]
    core_correct=sum(r[key]==r['gold'] for r in core)
    by_role={}
    f1s=[]
    for role in ROLES:
        tp=sum(r['gold']==role and r[key]==role for r in rr)
        fp=sum(r['gold']!=role and r[key]==role for r in rr)
        fn=sum(r['gold']==role and r[key]!=role for r in rr)
        p=tp/(tp+fp) if tp+fp else 0.0
        rec=tp/(tp+fn) if tp+fn else 0.0
        f1=2*p*rec/(p+rec) if p+rec else 0.0
        by_role[role]={'support':sum(r['gold']==role for r in rr),'precision':p,'recall':rec,'f1':f1}
        f1s.append(f1)
    by_sent=defaultdict(list)
    for r in rr: by_sent[r['sentence_id']].append(r)
    exact=sum(all(x[key]==x['gold'] for x in xs) for xs in by_sent.values())
    return {
        'tokens':len(rr),'correct':correct,'accuracy':correct/len(rr),
        'core_tokens':len(core),'core_correct':core_correct,'core_accuracy':core_correct/len(core) if core else 0,
        'macro_f1':sum(f1s)/len(f1s),'exact_sentences':exact,'exact_sentence_accuracy':exact/COUNT,
        'by_role':by_role,
    }


def main():
    torch.set_num_threads(4)
    nlp=spacy.load('en_core_web_sm')
    stz=stanza.Pipeline(lang='en',processors='tokenize,pos,lemma,depparse',tokenize_no_ssplit=True,use_gpu=False,verbose=False)
    ck=torch.load(MODEL,map_location='cpu',weights_only=False)
    model=base.RoleNet().cpu(); model.load_state_dict(ck['model'],strict=True); model.eval()

    tsv,last_modified=download_cc0()
    selected=select_500(tsv,nlp)
    OUT_TSV.parent.mkdir(parents=True,exist_ok=True)
    OUT_TSV.write_text('tatoeba_id\ttext\n'+'\n'.join(f'{sid}\t{text}' for sid,text in selected)+'\n',encoding='utf-8')

    rows=[]; skipped_words=0; total_gold_words=0; sentence_meta=[]
    for sid,text in selected:
        sdoc=stz(text)
        if not sdoc.sentences:
            sentence_meta.append({'id':sid,'text':text,'aligned':0,'gold_words':0}); continue
        gold_pairs=stanza_roles(sdoc.sentences[0])
        words=[w for w,_ in gold_pairs]
        spans=locate_word_spans(text,words)
        doc=nlp(text)
        direct,guarded,reasons=predict_roles(doc,model)
        aligned=0
        if spans is None:
            skipped_words += sum(role is not None for _,role in gold_pairs)
            total_gold_words += sum(role is not None for _,role in gold_pairs)
            sentence_meta.append({'id':sid,'text':text,'aligned':0,'gold_words':len(gold_pairs)}); continue
        for (w,gold),(a,b) in zip(gold_pairs,spans):
            if gold is None: continue
            total_gold_words += 1
            best=None; bestov=0
            for i,t in enumerate(doc):
                ov=overlap(a,b,t.idx,t.idx+len(t.text))
                if ov>bestov: bestov=ov; best=i
            if best is None or bestov==0:
                skipped_words += 1; continue
            aligned += 1
            rows.append({
                'sentence_id':sid,'text':text,'token':w.text,'upos':w.upos,'deprel':w.deprel,
                'gold':gold,'spacy_token':doc[best].text,'spacy_pos':doc[best].pos_,'spacy_dep':doc[best].dep_,
                'neural_direct':direct[best],'final':guarded[best],'guard_reason':reasons[best],
            })
        sentence_meta.append({'id':sid,'text':text,'aligned':aligned,'gold_words':sum(role is not None for _,role in gold_pairs)})

    direct_score=score(rows,'neural_direct'); final_score=score(rows,'final')
    conf=Counter((r['gold'],r['final']) for r in rows if r['gold']!=r['final'])
    errors=[r for r in rows if r['gold']!=r['final']]
    result={
        'benchmark':'TatoebaDaily500-CC0 independent-silver',
        'source_url':SOURCE_URL,'source_last_modified':last_modified,'license':'CC0 1.0',
        'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),
        'selection':'deterministic SHA-256 sample after 2-10 word, <=80 char, single-sentence, no URL/digits, spaCy no-PROPN/X/SYM filter',
        'sentences':COUNT,'training_allowed':False,'gold_method':'Stanza English UD tokenize+POS+lemma+dependency mapped to SentenceLab S/V/O/C/M roles',
        'alignment':{'gold_nonpunct_words':total_gold_words,'aligned_words':len(rows),'skipped_words':skipped_words,'coverage':len(rows)/total_gold_words if total_gold_words else 0},
        'neural_direct':direct_score,'final_r018':final_score,
        'remaining_confusions':[{'gold':a,'pred':b,'count':n} for (a,b),n in conf.most_common()],
        'errors':errors,'sentences_meta':sentence_meta,
    }
    OUT_JSON.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=[
        'SentenceLab practical benchmark — Tatoeba Daily 500 (CC0)',
        f'sentences: {COUNT} | aligned tokens: {len(rows)}/{total_gold_words} ({result["alignment"]["coverage"]*100:.2f}%)',
        f'neural direct: full {direct_score["accuracy"]*100:.2f}% | core {direct_score["core_accuracy"]*100:.2f}% | macro-F1 {direct_score["macro_f1"]*100:.2f}% | exact {direct_score["exact_sentences"]}/{COUNT}',
        f'R018 final   : full {final_score["accuracy"]*100:.2f}% | core {final_score["core_accuracy"]*100:.2f}% | macro-F1 {final_score["macro_f1"]*100:.2f}% | exact {final_score["exact_sentences"]}/{COUNT}',
        'role F1: '+', '.join(f'{r}={final_score["by_role"][r]["f1"]*100:.2f}%' for r in ROLES),
        'top confusions: '+', '.join(f'{a}->{b}:{n}' for (a,b),n in conf.most_common(10)),
        'NOTE: independent Stanza-derived UD labels are silver reference labels, not human-audited gold.',
    ]
    OUT_TXT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))

if __name__=='__main__': main()
