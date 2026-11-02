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
            calibrated={model for run in ledger['runs'] if run['purpose']=='calibration' and run['status']=='fetched'
                        and run['gpu']=='NvidiaTeslaT4' for model in run.get('calibrated_models',[])}
            eligible=[item for item in pending if item.get('purpose','sweep')=='calibration'
                      or set(item['models'].split(','))<=calibrated]
            if not eligible:
                if not active:
                    raise RuntimeError('Queue blocked by a failed model calibration; inspect results before choosing a fallback')
                break
            item=eligible[0]
            pending.remove(item)
            purpose=item.get('purpose','sweep')
            arguments=['submit','--name',item['name'],'--purpose',purpose,'--models',item['models'],
                       '--workloads',item['workloads'],'--timeout',str(item['timeout']),'--seed',str(item['seed'])]
            if purpose=='calibration':
                arguments += ['--lengths','32,512','--turns','32','--rates','50,200',
                              '--repeats','3','--micro-repeats','3','--stabilize','3']
            control(arguments)
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
