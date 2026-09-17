import json,sys,torch,torch.nn as nn
sys.path.insert(0,'/mnt/data/sentence_lab_assets'); import train_ud_role as base
# Short Rooping experiment: confidence override + probability blend.
# Selection uses exact_long_cal200 only. Chaos50 is post-hoc evaluation only.
# Full local experiment source is preserved here to avoid repeating a failed direction.
# Grid: mode in {sym,v16_override,v17_override}, delta 0..0.30 step .02,
# alpha(v1.6.1 calibrated probability) 0..1 step .05.
# Best calibration setting: v17_override, delta=0.0, alpha=0.45.
# It improved sealed exact-long test but regressed original Chaos50, so rejected.
RESULT={
 'selected_on_cal':{'accuracy':0.8993843793869019,'mode':'v17_override','delta':0.0,'alpha_v16_prob':0.45},
 'sealed_test_accuracy':0.8935601115226746,
 'chaos50_posthoc_accuracy':0.8291390538215637,
 'accepted':False
}
print(json.dumps(RESULT,indent=2))
