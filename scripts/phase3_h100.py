"""One H100 allocation: calibrate, commit predictions, release, collect."""
import argparse
import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import phase3_control as control
from phase3_plan import MAIN,MODELS,CONDITIONS,specification
from phase3_sweeps import project
from predict_phase3 import create

NAME='h100-single-session'
GPU='H100!'


def plan():
    runs=[dict(name='h100-main',models=[MAIN],workload='ultrachat',lengths_by_model={MAIN:[256,1024,4096,16384]},turns_by_model={MAIN:[32]},seed=8901),
          dict(name='h100-pythia',models=[MODELS[3]],workload='repeated_control',lengths_by_model={MODELS[3]:[256,1024]},turns_by_model={MODELS[3]:[32]},seed=8902)]
    result=dict(kind='phase3_h100_plan',phase='phase3',schema_version=3,gpu=GPU,planned_runs=runs,
        allocation_timeout_s=1680,initialization_allowance_s=120,registration_gate_max_s=300,
        calibration_anchors={MAIN:[64,1024,8192],MODELS[3]:[64,512,2016]},
        dropped_cells=[dict(gpu=GPU,model=MODELS[3],prefix_tokens=L,turn_tokens=32,condition=c,
                            reason='prefix plus new turn exceeds native context') for L in [4096,16384] for c in CONDITIONS])
    (ROOT/'configs/phase3_h100_plan.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def parent():return next(r for r in control.load()['runs'] if r['name']==NAME)


def command(args):
    subprocess.run(args,cwd=ROOT,check=True,stdout=subprocess.DEVNULL)


def download(remote,destination):
    p=subprocess.run(['modal','volume','get',control.OUTPUT_VOLUME,remote,str(destination),'--force'],
                     cwd=ROOT,capture_output=True,text=True,timeout=45)
    return p.returncode==0


def collect_stages(specs):
    stages=[]
    for spec in specs:
        name=spec['run_id'].removeprefix('phase3-');folder=control.RAW/name;folder.mkdir(exist_ok=True)
        output=folder/'output';output.mkdir(exist_ok=True)
        command(['modal','volume','get',control.OUTPUT_VOLUME,spec['run_id'],str(output),'--force'])
        nested=output/spec['run_id']
        if nested.exists():
            for path in nested.iterdir():shutil.move(str(path),str(output/path.name))
            nested.rmdir()
        outcome=json.loads((output/'done.json').read_text())
        started=json.loads((output/'started.json').read_text())
        rows=[json.loads(l) for l in (output/'results.jsonl').read_text().splitlines()]
        stages.append(dict(name=name,gpu=GPU,purpose=spec['purpose'],status='collected',specification=spec,
            submitted_at=datetime.datetime.fromtimestamp(started['started_unix'],datetime.timezone.utc).isoformat(),
            duration_s=outcome['duration_s'],outcome=outcome,complete=outcome['complete'],
            environment=next(r['environment'] for r in rows if r['kind']=='environment'),use_for_prediction=True))
    with (control.RAW/'control.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);ledger=control.load();run=next(r for r in ledger['runs'] if r['name']==NAME)
        merged={r['name']:r for r in run.get('logical_runs',[])};merged.update({r['name']:r for r in stages})
        run['logical_runs']=list(merged.values());run['environment']=stages[0]['environment'];control.save(ledger)
    return stages


def start():
    p=plan();calibration=[]
    for run in p['planned_runs']:
        model=run['models'][0]
        calibration.append(specification('calibration-'+run['name'],GPU,'calibration',240,[model],
             {model:p['calibration_anchors'][model]},{model:[32]},run['workload'],run['seed']))
    spec=dict(run_id='phase3-'+NAME,gpu=GPU,purpose='h100_combined',calibration_stages=calibration,
              planned_runs=p['planned_runs'],platform_cpu=4,platform_memory_mib=32768)
    path=control.RAW/'control/specs'/ (NAME+'.json');path.write_text(json.dumps(spec)+'\n')
    command([sys.executable,str(ROOT/'scripts/phase3_control.py'),'submit','--name',NAME,'--gpu',GPU,'--timeout','1680','--spec',str(path)])
    print('Submitted one bounded H100 allocation')


def release(ready):
    run=parent();collect_stages(run['specification']['calibration_stages'])
    manifest=ROOT/'configs/predictions_H100.json'
    registration=json.loads(manifest.read_text()) if manifest.exists() else create(GPU)
    projections=[];stages=[]
    for planned in registration['planned_runs']:
        projection=project(registration,planned);timeout=projection['projected_timeout_s']
        projection.update(selected_timeout_s=timeout,cost_covered_by_allocation=NAME)
        projections.append(projection)
        stages.append(specification(planned['name'],GPU,'sweep',timeout,planned['models'],planned['lengths_by_model'],
            planned['turns_by_model'],planned['workload'],planned['seed'],dict(_stage_timeout_s=timeout,cost_projection=projection)))
    assert sum(s['_stage_timeout_s'] for s in stages)+time.time()-ready['started_unix']+45<1680,'H100 projected sweeps exceed remaining time'
    projections_path=ROOT/'outputs/phase3_projections.json';existing=json.loads(projections_path.read_text())
    existing=[p for p in existing if p['gpu']!=GPU]+projections
    projections_path.write_text(json.dumps(existing,indent=2)+'\n')
    command(['git','add','configs/predictions_H100.json','docs/PREDICTIONS_H100.md','outputs/phase3_projections.json'])
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:
        command(['git','commit','-m','Preregister H100 predictions before releasing its sweep'])
    commit=subprocess.check_output(['git','log','-1','--format=%H','--','configs/predictions_H100.json'],cwd=ROOT,text=True).strip()
    for file in ['configs/predictions_H100.json','docs/PREDICTIONS_H100.md']:
        assert subprocess.check_output(['git','show',commit+':'+file],cwd=ROOT)==(ROOT/file).read_bytes(),'Uncommitted prediction change'
    try:subprocess.run(['git','push','origin','main'],cwd=ROOT,timeout=45,check=False)
    except subprocess.TimeoutExpired:print('Public push deferred; local preregistration commit is complete',flush=True)
    for stage in stages:stage.update(prediction_manifest='configs/predictions_H100.json',prediction_commit=commit)
    payload=dict(prediction_commit=commit,manifest_text=manifest.read_text(),manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),sweep_stages=stages)
    path=control.RAW/NAME/'release.json';path.write_text(json.dumps(payload)+'\n')
    command(['modal','volume','put',control.OUTPUT_VOLUME,str(path),'phase3-'+NAME+'/release.json','--force'])
    print(json.dumps(dict(released=True,commit=commit,projected_stage_seconds=sum(s['_stage_timeout_s'] for s in stages))),flush=True)
    return payload


def follow():
    run=parent();folder=control.RAW/NAME
    ready=folder/'ready.json';done=folder/'host-result.json';payload=None
    while not download('phase3-'+NAME+'/ready.json',ready):
        if download('phase3-'+NAME+'/done.json',done):raise RuntimeError('H100 ended before the calibration gate: '+done.read_text())
        time.sleep(5)
    release_file=folder/'release.json'
    if release_file.exists():
        payload=json.loads(release_file.read_text())
        command(['modal','volume','put',control.OUTPUT_VOLUME,str(release_file),'phase3-'+NAME+'/release.json','--force'])
    else:payload=release(json.loads(ready.read_text()))
    while not download('phase3-'+NAME+'/done.json',done):time.sleep(5)
    collect_stages(run['specification']['calibration_stages']+payload['sweep_stages'])
    command([sys.executable,str(ROOT/'scripts/phase3_control.py'),'collect','--name',NAME])
    print('H100 session collected',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','start','follow']);a=p.parse_args()
    {'plan':plan,'start':start,'follow':follow}[a.action]()
