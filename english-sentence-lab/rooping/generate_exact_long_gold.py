#!/usr/bin/env python3
# Exact-gold long-sentence curriculum used by Rooping.
# Gold roles are assigned when each token is emitted; no external parser creates labels.
import random,json
from pathlib import Path
R=random.Random(92617)
subjects=['engineer','analyst','researcher','auditor','manager','editor','scientist','reviewer','architect','consultant','investigator','planner','chemist','historian','economist','designer','programmer','coordinator','translator','supervisor']
objects=['report','prototype','dataset','schedule','proposal','estimate','diagram','contract','forecast','memorandum','record','blueprint','inventory','summary','model','statement','document','sample','ledger','questionnaire']
adjs=['reliable','uncertain','coherent','fragile','incomplete','accurate','misleading','stable','plausible','inconsistent','useful','ambiguous','defensible','obsolete','precise','questionable']
verbs=['reviewed','rejected','revised','questioned','examined','rechecked','approved','challenged','summarized','compared','tested','inspected','rewrote','validated','circulated']
baseverbs=['review','reject','revise','question','examine','recheck','approve','challenge','summarize','compare','test','inspect','rewrite','validate','circulate']
def T(text,pos,role): return {'text':text,'pos':pos,'role':role}
def np(role,noun=None):
    noun=noun or R.choice(subjects+objects); adj=R.choice(adjs) if R.random()<.55 else None; first=adj or noun
    indef='an' if first[0].lower() in 'aeiou' else 'a'; xs=[T(R.choice(['the',indef]),'DET',role)]
    if adj: xs.append(T(adj,'ADJ',role))
    xs.append(T(noun,'NOUN',role)); return xs
def comma(): return [T(',','PUNCT',None)]
def period(): return [T('.','PUNCT',None)]
def rel_subject(): return [T('who','PRON','S'),T(R.choice(verbs),'VERB','V')]+np('O',R.choice(objects))
def rel_object(): return [T('which','PRON','O')]+np('S',R.choice(subjects))+[T(R.choice(verbs),'VERB','V')]
def whether_clause(): return [T('whether','SCONJ','M')]+np('S')+[T('had','AUX','V'),T(R.choice(['changed','failed','improved','shifted']),'VERB','V')]
def why_clause(): return [T('why','ADV','M')]+np('S')+[T('had','AUX','V'),T(R.choice(['failed','changed','vanished','shifted']),'VERB','V')]
def because_clause(): return [T('because','SCONJ','M')]+np('S')+[T(R.choice(verbs),'VERB','V')]+np('O')
def although_clause(): return [T('although','SCONJ','M')]+np('S')+[T(R.choice(verbs),'VERB','V')]+np('O')
def passive_clause(): return np('S',R.choice(objects))+[T('was','AUX','V'),T(R.choice(['reviewed','rejected','revised','questioned','examined','approved']),'VERB','V'),T('by','ADP','M')]+np('M',R.choice(subjects))
def causative_clause(): return np('S')+[T('made','VERB','V')]+np('O',R.choice(subjects))+[T(R.choice(baseverbs),'VERB','V')]+np('O')
def find_oc_clause(): return np('S')+[T(R.choice(['found','considered','declared']),'VERB','V')]+np('O')+[T(R.choice(adjs),'ADJ','C')]
def cop_clause(): return np('S')+[T('was','AUX','V'),T(R.choice(['still','surprisingly','clearly']),'ADV','M'),T(R.choice(adjs),'ADJ','C')]
def parenthetical(): return [T('according','VERB','M'),T('to','ADP','M')]+np('M',R.choice(subjects))
def wh_question(): return [T(R.choice(['Why','How']),'ADV','M'),T('did','AUX','V')]+np('S')+[T(R.choice(baseverbs),'VERB','V')]+np('O')
def inversion(): return [T('Only','ADV','M'),T('after','ADP','M')]+np('M')+[T('had','AUX','V')]+np('S')+[T(R.choice(['noticed','admitted','confirmed']),'VERB','V')]+np('O')
def participle_intro(): return [T(R.choice(['Having','After']),'SCONJ','M'),T(R.choice(['reviewed','checked','compared']),'VERB','V')]+np('O')+comma()+np('S')+[T(R.choice(verbs),'VERB','V')]+np('O')
def build(fam):
    if fam==0: x=wh_question()+[T('after','SCONJ','M')]+np('S')+rel_object()+[T('had','AUX','V'),T('been','AUX','V'),T('questioned','VERB','V')]+comma()+causative_clause()
    elif fam==1: x=participle_intro()+[T('while','SCONJ','M')]+passive_clause()+comma()+[T('and','CCONJ','M')]+np('S')+[T('wondered','VERB','V')]+whether_clause()
    elif fam==2: x=inversion()+comma()+although_clause()+comma()+[T('yet','CCONJ','M')]+cop_clause()
    elif fam==3: x=[T('If','SCONJ','M')]+find_oc_clause()+comma()+np('S')+rel_subject()+[T('will','AUX','V'),T('make','VERB','V')]+np('O',R.choice(subjects))+[T(R.choice(baseverbs),'VERB','V')]+np('O')
    elif fam==4: x=[T('What','PRON','O')]+np('S')+[T('wanted','VERB','V'),T('to','PART','M'),T('know','VERB','V'),T('was','AUX','V')]+whether_clause()+comma()+because_clause()
    elif fam==5: x=[T('It','PRON','S'),T('was','AUX','V'),T(R.choice(adjs),'ADJ','C'),T('that','SCONJ','M')]+np('S')+[T(R.choice(verbs),'VERB','V')]+np('O')+comma()+[T('which','PRON','S'),T('made','VERB','V')]+np('O')+[T(R.choice(adjs),'ADJ','C')]
    elif fam==6: x=np('S')+rel_subject()+[T('was','AUX','V'),T(R.choice(['questioned','reviewed','approved']),'VERB','V'),T('by','ADP','M')]+np('M')+comma()+[T('whose','DET','S')]+np('S')+[T('had','AUX','V'),T(R.choice(['changed','failed','improved']),'VERB','V')]
    elif fam==7: x=np('S')+comma()+parenthetical()+comma()+[T('considered','VERB','V')]+np('O')+[T(R.choice(adjs),'ADJ','C')]+comma()+[T('even','ADV','M'),T('though','SCONJ','M')]+np('S')+[T('was','AUX','V'),T(R.choice(adjs),'ADJ','C')]
    elif fam==8: x=[T('Unless','SCONJ','M')]+np('S')+[T(R.choice(verbs),'VERB','V')]+np('O')+comma()+np('S')+[T('cannot','AUX','V'),T('decide','VERB','V')]+whether_clause()+comma()+[T('because','SCONJ','M')]+np('S')+[T('asked','VERB','V')]+why_clause()
    else: x=[T('Frankly','ADV','M')]+comma()+np('S')+comma()+parenthetical()+comma()+[T('seemed','VERB','V'),T('to','PART','M'),T('consider','VERB','V')]+np('O')+[T(R.choice(adjs),'ADJ','C')]+comma()+although_clause()
    marked=[because_clause,although_clause,participle_intro]; bare=[passive_clause,causative_clause,find_oc_clause,cop_clause]
    while len([t for t in x if t['pos']!='PUNCT'])<95:
        if R.random()<.35: x+=comma()+R.choice(marked)()
        else:
            conn=R.choice(['while','although','because','and']); pos='CCONJ' if conn=='and' else 'SCONJ'; x+=comma()+[T(conn,pos,'M')]+R.choice(bare)()
    return x+period()
def generate():
    rows=[]
    for i in range(400):
        toks=build(i%10); text=' '.join(t['text'] for t in toks).replace(' ,',',').replace(' .','.').replace(' ?','?')
        rows.append({'id':i+1,'family':i%10,'text':text,'tokens':toks,'word_count':sum(t['pos']!='PUNCT' for t in toks)})
    cal=[r for r in rows if ((r['id']-1)//10)%2==0][:200]; test=[r for r in rows if r not in cal][:200]
    return cal,test
if __name__=='__main__':
    out=Path('exact_long_gold');out.mkdir(exist_ok=True);cal,test=generate();json.dump(cal,open(out/'exact_long_cal200.json','w'),indent=2);json.dump(test,open(out/'exact_long_test200.json','w'),indent=2)
    print(len(cal),len(test),sum(r['word_count'] for r in cal+test)/400)
