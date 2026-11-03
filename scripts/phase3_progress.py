"""Read incremental study logs; never restart a remote measurement."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import datetime
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
VOLUME='reload-recompute-phase3-results-20261103'


def read(run):
    path=ROOT/'outputs/raw/phase3'/run['name']/'progress.jsonl'
    path.parent.mkdir(exist_ok=True)
    p=subprocess.run(['modal','volume','get',VOLUME,run['specification']['run_id']+'/results.jsonl',str(path),'--force'],
                     capture_output=True,text=True,timeout=30)
    if p.returncode:return dict(name=run['name'],available=False)
    rows=[json.loads(l) for l in path.read_text().splitlines()]
    samples=[r for r in rows if r['kind']=='measurement']
    return dict(name=run['name'],available=True,timing_samples=len(samples),invalid=sum(not r['valid'] for r in samples),
                completed_shapes=sum(r['kind']=='shape_complete' for r in rows),
                last_elapsed_s=rows[-1]['process_elapsed_s'],last_model=rows[-1].get('model'),
                failures=[r['error'] for r in rows if r['kind'] in ['fatal_error','model_failed']],
                run_complete=any(r['kind']=='run_complete' for r in rows))


if __name__=='__main__':
    ledger=json.loads((ROOT/'outputs/phase3_ledger.json').read_text())
    containers=json.loads(subprocess.check_output(['modal','container','list','--json'],text=True))
    active={c['app_name'].removeprefix('reload-recompute-p3-') for c in containers if c['app_name'].startswith('reload-recompute-p3-')}
    runs=[r for r in ledger['runs'] if r['name'] in active and r['purpose']!='prepare']
    expanded=[]
    for run in runs:
        if run['purpose']=='h100_combined':
            specs=run['specification']['calibration_stages'].copy()
            release=ROOT/'outputs/raw/phase3'/run['name']/'release.json'
            if release.exists():specs+=json.loads(release.read_text())['sweep_stages']
            expanded.extend(dict(name=s['run_id'].removeprefix('phase3-'),specification=s) for s in specs)
        else:expanded.append(run)
    runs=expanded
    with ThreadPoolExecutor(max_workers=4) as pool:progress=list(pool.map(read,runs))
    snapshot=dict(observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),active=sorted(active),progress=progress)
    (ROOT/'outputs/raw/phase3/control/progress-latest.json').write_text(json.dumps(snapshot,indent=2)+'\n')
    print(json.dumps(snapshot))
