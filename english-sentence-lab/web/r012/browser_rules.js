(function(root){
  'use strict';
  const POSSESSIVE_DET=new Set(['my','your','his','her','its','our','their']);
  const PRONOUNS=new Set('i me mine myself you yours yourself yourselves he him himself she hers herself it itself we us ours ourselves they them theirs themselves who whom whose what which whoever whatever'.split(' '));
  const DETS=new Set('a an the this that these those each every either neither some any no another such all both few many much several enough'.split(' '));
  const AUX=new Set('am is are was were be been being have has had having do does did can could may might must shall should will would'.split(' '));
  const CCONJ=new Set('and or but nor yet so'.split(' '));
  const SCONJ=new Set('although though because since while whilst when whenever where wherever if unless until before after once whether as than that'.split(' '));
  const ADP=new Set('in on at by for from with without about against between into through during before after above below to of over under around near behind beside beyond across toward towards upon within outside inside like despite except'.split(' '));
  const ADV=new Set('very really still already just also too quite rather here there now then soon always never often sometimes usually perhaps maybe almost even only again together apart away early late first next well poorly today tomorrow yesterday exactly'.split(' '));
  const ADJ=new Set('good bad new old young high low large small big little long short right wrong sure ready able likely unlikely possible impossible realistic unrealistic exhausted missing talented gifted skilled tired interested bored convincing conclusive acceptable reasonable ineffective unacceptable dangerous operational stable reliable available enforceable usable publishable'.split(' '));
  const VERBS=new Set('say says said tell tells told think thinks thought know knows knew known make makes made take takes took taken get gets got gotten go goes went gone come comes came see sees saw seen want wants wanted need needs needed like likes liked love loves loved work works worked help helps helped let lets leave leaves left argue argues argued test tests tested rewrite rewrites rewrote rewritten notice notices noticed assume assumes assumed warn warns warned miss misses missed use uses used give gives gave given find finds found call calls called ask asks asked feel feels felt become becomes became remain remains remained seem seems seemed keep keeps kept believe believes believed lead leads led practice practices practiced improve improves improved rely relies relied perform performs performed focus focuses focused inspect inspects inspected compare compares compared check checks checked review reviews reviewed learn learns learned start starts started respond responds responded rebuild rebuilds rebuilt redo redoes redid redone admit admits admitted repair repairs repaired damage damages damaged approve approves approved accept accepts accepted reject rejects rejected revise revises revised release releases released hire hires hired redesign redesigns redesigned criticize criticizes criticized promote promotes promoted document documents documented endorse endorses endorsed calibrate calibrates calibrated ignore ignores ignored train trains trained examine examines examined overlook overlooks overlooked propose proposes proposed underestimate underestimates underestimated prepare prepares prepared omit omits omitted realize realizes realized discover discovers discovered copy copies copied require requires required hide hides hid hidden request requests requested delay delays delayed change changes changed expect expects expected repeat repeats repeated alter alters altered contaminate contaminates contaminated misplace misplaces misplaced recover recovers recovered amend amends amended measure measures measured mislabel mislabels mislabeled confess confesses confessed acknowledge acknowledges acknowledged reverse reverses reversed describe describes described reopen reopens reopened predict predicts predicted sell sells sold write writes wrote written complain complains complained record records recorded stop stops stopped report reports reported observe observes observed prove proves proved proven suspend suspends suspended cancel cancels canceled cancelled confirm confirms confirmed replace replaces replaced halt halts halted violate violates violated show shows showed shown uphold upholds upheld build builds built design designs designed modify modifies modified adjust adjusts adjusted validate validates validated update updates updated solve solves solved present presents presented monitor monitors monitored board boards boarded submit submits submitted return returns returned'.split(' '));
  const INTJ=new Set('oh wow hey hi hello yes no okay ok thanks thank please sorry'.split(' '));
  const COPULAS=new Set(['am','is','are','was','were','be','been','being']);
  const LINKING_VERBS=new Set(['remain','remains','remained','become','becomes','became','seem','seems','seemed']);
  const CONTEXT_NOUNS=new Set('hospital principal detective factory proposal signal permit'.split(' '));
  const CLAUSE_MARKERS=new Set('although though because since while whilst when whenever if unless until before after once whether that why how what'.split(' '));
  const WH=new Set(['what','who','whom','which']);
  const DEMONSTRATIVES=new Set(['this','that','these','those']);

  function expandContractions(text){
    let s=String(text||'').replace(/[’‘]/g,"'");
    const pairs=[[/\bcan't\b/gi,'can not'],[/\bwon't\b/gi,'will not'],[/\bshan't\b/gi,'shall not'],[/\bdon't\b/gi,'do not'],[/\bdoesn't\b/gi,'does not'],[/\bdidn't\b/gi,'did not'],[/\bisn't\b/gi,'is not'],[/\baren't\b/gi,'are not'],[/\bwasn't\b/gi,'was not'],[/\bweren't\b/gi,'were not'],[/\bhaven't\b/gi,'have not'],[/\bhasn't\b/gi,'has not'],[/\bhadn't\b/gi,'had not'],[/\bcouldn't\b/gi,'could not'],[/\bshouldn't\b/gi,'should not'],[/\bwouldn't\b/gi,'would not'],[/\bmustn't\b/gi,'must not'],[/\bmightn't\b/gi,'might not'],[/\bneedn't\b/gi,'need not']];
    for(const [re,full] of pairs) s=s.replace(re,full);
    s=s.replace(/\b([A-Za-z]+)n't\b/gi,'$1 not')
     .replace(/\b([A-Za-z]+)'re\b/gi,'$1 are')
     .replace(/\b([A-Za-z]+)'ve\b/gi,'$1 have')
     .replace(/\b([A-Za-z]+)'ll\b/gi,'$1 will')
     .replace(/\b([A-Za-z]+)'m\b/gi,'$1 am');
    return s;
  }
  function splitTokens(text){return expandContractions(text).match(/[A-Za-z]+|'(?:s|d)|\d+(?:[.,]\d+)?|[^\sA-Za-z0-9]/g)||[];}
  function looksVerb(w){return VERBS.has(w)||/(ing|ed|ize|ise|ify)$/.test(w);}
  function nounContext(tokens,i){
    const prev=(tokens[i-1]||'').toLowerCase(),next=(tokens[i+1]||'').toLowerCase();
    const prevDet=DETS.has(prev)||POSSESSIVE_DET.has(prev);
    const nextBoundary=!next||/^[,.!?;:]$/.test(tokens[i+1]||'')||AUX.has(next)||SCONJ.has(next)||CCONJ.has(next)||looksVerb(next);
    return prevDet&&nextBoundary;
  }
  function inferPos(tokens){
    const out=[];
    for(let i=0;i<tokens.length;i++){
      const raw=tokens[i],w=raw.toLowerCase(),next=(tokens[i+1]||'').toLowerCase();let p;
      if(raw==='%')p='SYM';
      else if(/^[^\w']+$/.test(raw))p='PUNCT';
      else if(/^\d+(?:[.,]\d+)?$/.test(raw))p='NUM';
      else if(w==='not')p='PART';
      else if(w==="'d")p='AUX';
      else if(w==="'s")p=(ADJ.has(next)||looksVerb(next)||ADV.has(next)||next==='not')?'AUX':'PART';
      else if(AUX.has(w))p='AUX';
      else if(POSSESSIVE_DET.has(w))p='DET';
      else if(PRONOUNS.has(w))p='PRON';
      else if(DETS.has(w))p='DET';
      else if(CCONJ.has(w))p='CCONJ';
      else if(SCONJ.has(w))p='SCONJ';
      else if(w==='to')p='PART';
      else if(ADP.has(w))p='ADP';
      else if(INTJ.has(w))p='INTJ';
      else if(nounContext(tokens,i)&&(VERBS.has(w)||CONTEXT_NOUNS.has(w)))p='NOUN';
      else if(VERBS.has(w))p='VERB';
      else if(ADV.has(w)||/ly$/.test(w))p='ADV';
      else if(ADJ.has(w))p='ADJ';
      else if(/(ing|ed|ize|ise|ify)$/.test(w))p='VERB';
      else if(/(ous|ful|less|ive|able|ible|al|ic|ary|ory)$/.test(w))p='ADJ';
      else if(i>0&&/^[A-Z]/.test(raw))p='PROPN';
      else p='NOUN';
      out.push(p);
    }
    return out;
  }
  function weakRoles(pos){
    const out=[];let seen=false;
    for(const p of pos){
      if(p==='VERB'||p==='AUX'){out.push('V');seen=true;}
      else if(p==='PUNCT')out.push(null);
      else if(p==='NOUN'||p==='PROPN'||p==='PRON')out.push(seen?'O':'S');
      else out.push('M');
    }
    return out;
  }
  function postprocessRoles(tokens,pos,inputRoles){
    const roles=[...inputRoles],lo=tokens.map(x=>x.toLowerCase()),setRole=(i,r)=>{if(i>=0&&i<roles.length)roles[i]=r;};
    for(let i=0;i<lo.length;i++){
      if(lo[i]!=='not')continue;
      setRole(i,'M');
      if(i>0&&(pos[i-1]==='AUX'||AUX.has(lo[i-1])||lo[i-1]==="'s"||lo[i-1]==="'d"))setRole(i-1,'V');
      for(let j=i+1;j<lo.length;j++){
        if(pos[j]==='PUNCT')break;
        if(pos[j]==='ADV'||pos[j]==='PART')continue;
        if(pos[j]==='VERB'||['be','have','do'].includes(lo[j]))setRole(j,'V');
        break;
      }
    }
    for(let i=0;i<lo.length;i++){
      if((lo[i]==="'s"||lo[i]==="'d")&&pos[i]==='AUX')setRole(i,'V');
      if(lo[i]==="'s"&&pos[i]==='PART')setRole(i,'M');
    }
    let cop=-1;
    for(let i=0;i<lo.length;i++)if(COPULAS.has(lo[i])&&(pos[i]==='AUX'||pos[i]==='VERB')){cop=i;break;}
    const finiteBeforeFirstCop=cop>0&&pos.slice(1,cop).some(p=>p==='VERB'||p==='AUX');
    const directWhCopular=cop>0&&WH.has(lo[0])&&!finiteBeforeFirstCop;
    if(directWhCopular){
      setRole(0,'C');
      for(let i=1;i<cop;i++)if(pos[i]!=='PUNCT')setRole(i,'M');
      setRole(cop,'V');
      for(let i=cop+1;i<lo.length;i++){if(pos[i]==='PUNCT')break;setRole(i,'S');}
    }

    // Process every local copular/linking predicate instead of only the first copula.
    for(let link=0;link<lo.length;link++){
      if(!(COPULAS.has(lo[link])||LINKING_VERBS.has(lo[link])))continue;
      if(!(pos[link]==='AUX'||pos[link]==='VERB'))continue;
      if(directWhCopular&&link===cop)continue;
      let candidate=-1;
      for(let i=link+1;i<lo.length;i++){
        if(pos[i]==='PUNCT'||pos[i]==='CCONJ'||pos[i]==='SCONJ')break;
        if(pos[i]==='ADV'||pos[i]==='DET'||pos[i]==='NUM'||pos[i]==='SYM'||pos[i]==='PART'){setRole(i,'M');continue;}
        if(pos[i]==='ADJ'||pos[i]==='NOUN'||pos[i]==='PROPN'||pos[i]==='PRON'){candidate=i;break;}
        if(pos[i]==='VERB'||pos[i]==='AUX')break;
      }
      if(candidate>=0)setRole(candidate,'C');
    }

    // "whom" is an object-form relative/interrogative pronoun in the school-style role set.
    for(let i=0;i<lo.length;i++)if(lo[i]==='whom')setRole(i,'O');

    const nominal=i=>i>=0&&i<pos.length&&['NOUN','PROPN','PRON'].includes(pos[i]);
    const boundary=i=>i<0||i>=pos.length||pos[i]==='PUNCT'||pos[i]==='CCONJ';
    const markClauseSubject=(start,end)=>{
      let verb=-1,subj=-1;
      for(let i=start;i<end;i++){
        if(boundary(i))break;
        if(pos[i]==='ADP')continue;
        if((pos[i]==='VERB'||pos[i]==='AUX')&&verb<0){verb=i;break;}
        if(subj<0&&nominal(i))subj=i;
      }
      if(subj>=0&&verb>subj)setRole(subj,'S');
    };

    // Sentence-initial and comma-delimited clause subjects. Preserve direct WH-copular C.
    if(!directWhCopular)markClauseSubject(0,lo.length);
    // A leading determiner NP remains the main subject even when a comma-delimited relative clause follows.
    if(DETS.has(lo[0])||POSSESSIVE_DET.has(lo[0])){
      for(let i=1;i<lo.length;i++){
        if(pos[i]==='VERB'||pos[i]==='AUX')break;
        if(nominal(i)){setRole(i,'S');break;}
        if(pos[i]==='PUNCT')break;
      }
    }
    for(let i=0;i<lo.length;i++){
      if(pos[i]==='PUNCT'&&/[,:;]/.test(tokens[i]))markClauseSubject(i+1,lo.length);
      if(CLAUSE_MARKERS.has(lo[i])&&!(directWhCopular&&i===0))markClauseSubject(i+1,lo.length);
    }

    // Do-support inversion: "did the accountant admit ..." / ordinary questions.
    for(let i=0;i<lo.length;i++){
      if(!['do','does','did'].includes(lo[i])||pos[i]!=='AUX')continue;
      let subj=-1,lex=-1;
      for(let j=i+1;j<lo.length&&!boundary(j);j++){
        if(subj<0&&nominal(j)){subj=j;continue;}
        if(subj>=0&&pos[j]==='VERB'){lex=j;break;}
      }
      if(subj>=0&&lex>subj){setRole(subj,'S');setRole(i,'V');setRole(lex,'V');}
    }

    // Local lexical-verb objects. Stop at prepositions/subordinators so PP objects stay M.
    for(let i=0;i<lo.length;i++){
      if(pos[i]!=='VERB'||LINKING_VERBS.has(lo[i]))continue;
      let obj=-1;
      for(let j=i+1;j<lo.length;j++){
        if(pos[j]==='PUNCT'||pos[j]==='SCONJ'||pos[j]==='CCONJ'||pos[j]==='ADP'||pos[j]==='AUX'||pos[j]==='VERB'||CLAUSE_MARKERS.has(lo[j]))break;
        if(nominal(j)){obj=j;break;}
      }
      if(obj>=0)setRole(obj,'O');
    }

    // Causative make + O + bare infinitive: made the team rewrite ...
    for(let i=0;i<lo.length;i++){
      if(!['make','makes','made'].includes(lo[i]))continue;
      let obj=-1,comp=-1;
      for(let j=i+1;j<lo.length&&!boundary(j);j++){
        if(obj<0&&nominal(j)){obj=j;continue;}
        if(obj>=0&&pos[j]==='VERB'){comp=j;break;}
      }
      if(obj>=0){setRole(obj,'O');if(comp>obj)setRole(comp,'C');}
    }

    // Ordinary prepositional phrases are modifier material in the v2 school-head spec.
    for(let i=0;i<pos.length;i++){
      if(pos[i]!=='ADP')continue;
      setRole(i,'M');
      for(let j=i+1;j<pos.length;j++){
        if(pos[j]==='PUNCT'||pos[j]==='VERB'||pos[j]==='AUX'||pos[j]==='CCONJ'||pos[j]==='SCONJ')break;
        setRole(j,'M');
      }
    }
    const isNum=w=>/^\d+(?:\.\d+)?$/.test(w.replace(/,/g,''));
    const isModifier=i=>{
      const w=lo[i],p=pos[i];
      return POSSESSIVE_DET.has(w)||DETS.has(w)||isNum(w)||w==='%'||['DET','ADJ','NUM','SYM'].includes(p)||(w==="'s"&&p==='PART');
    };
    for(let head=0;head<tokens.length;head++){
      if(!['NOUN','PROPN','PRON'].includes(pos[head])||!['S','O','C'].includes(roles[head]))continue;
      for(let j=head-1;j>=0;j--){if(/^[,.!?;:]$/.test(tokens[j])||!isModifier(j))break;setRole(j,'M');}
    }
    if(cop>=0){
      for(let i=cop+1;i<lo.length;i++){
        if(pos[i]==='PUNCT')break;
        if(DEMONSTRATIVES.has(lo[i])&&(i+1===lo.length||pos[i+1]==='PUNCT')){pos[i]='PRON';setRole(i,'S');}
        break;
      }
    }
    return roles;
  }
  const api={expandContractions,splitTokens,inferPos,weakRoles,postprocessRoles};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.SentenceLabBrowserRules=api;
})(typeof globalThis!=='undefined'?globalThis:this);
