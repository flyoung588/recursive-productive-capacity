#!/usr/bin/python3
"""Root-owned, sudo-restricted adapter to EXISTING OpenClaw; no routing or tools."""
import os
import subprocess
import sys
prompt = sys.stdin.read(180001)
if not prompt or len(prompt)>180000:
    raise SystemExit('Invalid prompt size')
env={'HOME':'/root','PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}
result=subprocess.run(['/usr/bin/openclaw','--log-level','error','infer','model','run',
    '--gateway','--model','openai/gpt-6.1-sol','--thinking','low','--prompt',prompt,'--json'],
    env=env,capture_output=True,text=True,timeout=240)
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
raise SystemExit(result.returncode)
