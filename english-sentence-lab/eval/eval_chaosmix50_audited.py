#!/usr/bin/env python3
from __future__ import annotations

import eval_chaosmix50 as e

# Audit corrections after inspecting the first baseline run against
# docs/role_label_spec_v2.md. These change evaluation labels only; the
# ChaosMix50 sentences remain strictly evaluation-only.
e.GOLD['CM50-002'] = [('committee',0,'S'),('whom',0,'M'),('exception',0,'S'),('anyone',0,'S'),('increase',0,'O')]
e.GOLD['CM50-016'] = [('student',0,'S'),('whom',0,'O'),('proof',0,'S'),('counterexample',0,'S'),('assumption',0,'O')]
e.GOLD['CM50-018'] = [('it',0,'S'),('machine',0,'S'),('records',0,'S'),('that',1,'S'),('step',0,'S')]
e.GOLD['CM50-028'] = [('mathematician',0,'S'),('shortcut',0,'S'),('sequence',0,'S'),('experiments',0,'S'),('cases',0,'O')]
e.GOLD['CM50-033'] = [('parser',0,'S'),('clause',0,'O'),('what',1,'S'),('sentences',0,'O'),('relative',0,'O')]
e.GOLD['CM50-044'] = [('Whatever',0,'S'),('it',0,'S'),('proposal',0,'M'),('forecast',1,'O'),('difference',0,'S')]

e.OUT = e.ROOT / 'artifacts' / 'v1.8.0_chaosmix50_audited_baseline.json'
e.SUMMARY = e.ROOT / 'artifacts' / 'v1.8.0_chaosmix50_audited_baseline.txt'

if __name__ == '__main__':
    e.main()
