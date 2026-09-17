import json,sys,torch,torch.nn as nn
sys.path.insert(0,'/mnt/data/sentence_lab_assets');import train_ud_role as base
class M19(nn.Module):
 def __init__(self):
  super().__init__();self.word=nn.Embedding(8192,32);self.pre=nn.Embedding(1024,8);self.suf=nn.Embedding(1024,8);self.pos=nn.Embedding(19,16);self.brole=nn.Embedding(6,8);self.shape=nn.Linear(8,16);self.proj=nn.Linear(88,96);self.gru=nn.GRU(96,64,3,batch_first=True,bidirectional=True);self.blocks=nn.ModuleList([base.AttentionBlock(128,4,.08)]);self.out=nn.Linear(128,6)
 def forward(self,b,m):
  x=torch.cat([self.word(b['wid']),self.pre(b['pre']),self.suf(b['suf']),self.pos(b['pos']),self.brole(b['role']),torch.tanh(self.shape(b['shape']))],-1);x=torch.nn.functional.gelu(self.proj(x));x,_=self.gru(x)
  for z in self.blocks:x=z(x,m)
  return self.out(x)
ROLE=base.I2ROLE;R2={r:i for i,r in enumerate(ROLE)};torch.set_num_threads(4)
m16=M19();m16.load_state_dict(torch.load('/mnt/data/v161_gru3_attn1_chunked.pt',map_location='cpu',weights_only=False)['model']);m16.eval();m17=base.RoleNet();m17.load_state_dict(torch.load('/mnt/data/sentence_lab_assets/v1.7.5_gold_ewt_masc_role.pt',map_location='cpu',weights_only=False)['model']);m17.eval()
def batch(ts):
 fs=[base.feat_token({'text':t['text'],'pos':t.get('pos') or 'UNK'},t.get('role')) for t in ts];return base.collate([(fs,[0]*len(fs),'','')],torch.device('cpu'))
def flat_exact(split):
 inp=json.load(open(f'/mnt/data/exact_long_gold/{split}_v155.json'));g={r['id']:r for r in json.load(open(f'/mnt/data/exact_long_gold/exact_long_{split}.json'))};A=[];B=[];Y=[]
 with torch.inference_mode():
  for s in inp:
   bt,_,mask=batch(s['tokens']);a=m16(bt,mask)[0];b=m17(bt,mask)[0]
   for i,t in enumerate(g[s['id']]['tokens']):
    if t['role'] is None:continue
    A.append(a[i]);B.append(b[i]);Y.append(R2[t['role']])
 return torch.stack(A),torch.stack(B),torch.tensor(Y)
cal=flat_exact('cal200');test=flat_exact('test200')
def fitT(z,y):
 logT=torch.tensor(0.,requires_grad=True);opt=torch.optim.Adam([logT],lr=.05);lossfn=nn.CrossEntropyLoss()
 for _ in range(120):
  opt.zero_grad();loss=lossfn(z/logT.exp(),y);loss.backward();opt.step()
 return float(logT.detach().exp())
T16=fitT(cal[0],cal[2]);T17=fitT(cal[1],cal[2]);print('T',T16,T17)
def score_flat(data,method):
 a,b,y=data;p16=(a/T16).softmax(-1);p17=(b/T17).softmax(-1);a1=a.argmax(-1);b1=b.argmax(-1)
 if method=='v16':pred=a1
 elif method=='v17':pred=b1
 elif method=='conf':pred=torch.where(p16.gather(1,a1[:,None])[:,0]>=p17.gather(1,b1[:,None])[:,0],a1,b1)
 elif method=='margin':
  m16v=torch.topk(p16,2,dim=1).values;m17v=torch.topk(p17,2,dim=1).values;pred=torch.where((m16v[:,0]-m16v[:,1])>=(m17v[:,0]-m17v[:,1]),a1,b1)
 else:pred=(p16+p17).argmax(-1)
 return float((pred==y).float().mean())
inp=json.load(open('/mnt/data/chaos_eval/chaos_long50_eval_input_v155.json'))['sentences'];gd={r['id']:{idx:R2[role] for idx,w,p,role in r['f']} for r in json.load(open('/mnt/data/chaos_eval/chaos_gold_indexed.json'))};CA=[];CB=[];CY=[]
with torch.inference_mode():
 for s in inp:
  bt,_,mask=batch(s['tokens']);a=m16(bt,mask)[0];b=m17(bt,mask)[0]
  for i,gy in gd[s['id']].items():CA.append(a[i]);CB.append(b[i]);CY.append(gy)
cha=(torch.stack(CA),torch.stack(CB),torch.tensor(CY))
out={'T16':T16,'T17':T17,'cal':{},'test':{},'chaos':{}}
for m in ['v16','v17','conf','margin','avg']:
 out['cal'][m]=score_flat(cal,m);out['test'][m]=score_flat(test,m);out['chaos'][m]=score_flat(cha,m);print(m,'cal',out['cal'][m],'test',out['test'][m],'chaos',out['chaos'][m])
json.dump(out,open('/mnt/data/temp_router_result.json','w'),indent=2)
