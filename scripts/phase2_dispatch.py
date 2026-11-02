"""Drain the approved phase-two queue with two private Kaggle sessions at most."""
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
CONTROL=ROOT/'scripts/phase2_control.py'
LOG=ROOT/'outputs/raw/phase2/control/dispatch.log'


def control(arguments):
    with LOG.open('a') as f:
        result=subprocess.run([sys.executable,str(CONTROL),*arguments],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('Controller failed. Queue stopped; inspect dispatch.log before resuming.')


def main():
    LOG.parent.mkdir(parents=True,exist_ok=True)
    queue=json.loads((ROOT/'configs/phase2_queue.json').read_text())
    last=None
    while True:
        ledger=json.loads((ROOT/'outputs/phase2_ledger.json').read_text())
        active=[r for r in ledger['runs'] if r['status']=='submitted']
        for run in active:
            control(['fetch','--name',run['name']])
        ledger=json.loads((ROOT/'outputs/phase2_ledger.json').read_text())
        names={r['name'] for r in ledger['runs']}
        active=[r for r in ledger['runs'] if r['status']=='submitted']
        pending=[r for r in queue if r['name'] not in names]
        while len(active)<2 and pending:
            item=pending.pop(0)
            control(['submit','--name',item['name'],'--purpose','sweep','--models',item['models'],
                     '--workloads',item['workloads'],'--timeout',str(item['timeout']),'--seed',str(item['seed'])])
            ledger=json.loads((ROOT/'outputs/phase2_ledger.json').read_text())
            active=[r for r in ledger['runs'] if r['status']=='submitted']
        snapshot=[(r['name'],r['status'],r.get('actual_gpu_hours')) for r in ledger['runs']]
        if snapshot!=last:
            print(json.dumps(dict(timestamp=time.time(),runs=snapshot,
                                  used_plus_reserved_gpu_hours=sum(r.get('actual_gpu_hours',r['reserved_gpu_hours'])
                                                                  for r in ledger['runs']))),flush=True)
            last=snapshot
        if not active and not pending:
            print('PHASE2_QUEUE_FINISHED',flush=True)
            return
        time.sleep(30)


if __name__=='__main__':
    main()
