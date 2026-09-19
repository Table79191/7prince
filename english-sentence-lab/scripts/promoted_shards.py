#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

LEGACY_NAME="promoted.jsonl"
SHARD_GLOB="promoted-*.jsonl"

def promoted_files(path):
    p=Path(path)
    base=p if p.is_dir() else p.parent
    files=[]
    legacy=base/LEGACY_NAME
    if legacy.exists():
        files.append(legacy)
    files.extend(sorted(base.glob(SHARD_GLOB)))
    return files

def iter_promoted(path):
    for p in promoted_files(path):
        with p.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)
