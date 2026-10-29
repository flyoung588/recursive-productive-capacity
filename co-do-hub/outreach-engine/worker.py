#!/usr/bin/env python3
"""Explicit local queued task; no scheduler and no autonomous contact."""
import json
import os
from pathlib import Path
import re
import sys
from runtime import Runtime
name=sys.argv[1]
if not re.fullmatch(r'[a-zA-Z0-9_-]+',name): raise SystemExit('Invalid task name')
state=Path(os.environ.get('CO_DO_STATE','/var/lib/co-do'))
task=json.loads((state/'tasks'/f'{name}.json').read_text())
result=Runtime(state).run(task['researcher'],name,task.get('learning',True),task.get('evidence_from'))
print(json.dumps(result,ensure_ascii=False))
