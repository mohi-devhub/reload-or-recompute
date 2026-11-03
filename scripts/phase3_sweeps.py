"""Project and submit a registered sweep without changing its frozen predictions."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from predict_phase3 import evaluate
from phase3_plan import specification


def project(registration,run):
    rows=[p for p in registration['predictions'] if p['run_id']=='phase3-'+run['name']]
    # Eleven complete rounds include the unreported warmup. Correctness forwards
    # and microbenchmarks are outside the timed trials but consume allocation time.
    measured_rounds_s=sum(p['predicted_ttft_ms'] for p in rows)*11/1000
    legs=registration['micro_fits'];micro_s=0;validation_s=0
    for model in run['models']:
        bpt=next(p['kv_bytes_per_token'] for p in rows if p['model']==model)
        for length in run['lengths_by_model'][model]:
            payload=bpt*length
            for condition in ['h2d_pinned','h2d_pageable','file_legs_raw','file_legs_torch']:
                micro_s+=10*sum(evaluate(f,payload) for f in legs[model][condition].values())/1000
            shape=[p for p in rows if p['model']==model and p['prefix_tokens']==length]
            validation_s+=sum(p['predicted_ttft_ms'] for p in shape if p['condition'] in ['recompute','gpu_hit','prefix_only'])/1000
    modeled=measured_rounds_s+micro_s+validation_s
    # Setup is a wall-time allowance, not a measured latency. All estimates retain
    # the same explicit margin rather than tuning it from sweep outcomes.
    timeout=math.ceil((modeled*1.25+90*len(run['models'])+90)/30)*30
    return dict(kind='phase3_cost_projection',phase='phase3',gpu=registration['gpu'],run_name=run['name'],
                round_projection_s=measured_rounds_s,micro_projection_s=micro_s,
                validation_projection_s=validation_s,margin_fraction=.25,
                setup_allowance_s=90*len(run['models']),finalization_allowance_s=90,
                projected_timeout_s=timeout,prediction_only=True)


def main(args):
    manifest=Path('configs')/('predictions_'+args.gpu+'.json')
    registration=json.loads((ROOT/manifest).read_text())
    run=next(r for r in registration['planned_runs'] if r['name']==args.name)
    projection=project(registration,run)
    commit=subprocess.check_output(['git','log','-1','--format=%H','--',str(manifest)],cwd=ROOT,text=True).strip()
    timeout=args.timeout or projection['projected_timeout_s']
    projection.update(selected_timeout_s=timeout,prediction_commit=commit)
    path=ROOT/'outputs/raw/phase3/control/specs'/(args.name+'.json')
    spec=specification(run['name'],args.gpu,'sweep',timeout,run['models'],run['lengths_by_model'],
                       run['turns_by_model'],run['workload'],run['seed'],
                       dict(prediction_manifest=str(manifest),prediction_commit=commit,cost_projection=projection))
    path.write_text(json.dumps(spec)+'\n')
    public=ROOT/'outputs/phase3_projections.json'
    projections=json.loads(public.read_text()) if public.exists() else []
    projections=[p for p in projections if p['run_name']!=args.name]+[projection]
    public.write_text(json.dumps(projections,indent=2)+'\n')
    print(json.dumps(projection))
    if args.submit:
        subprocess.run([sys.executable,str(ROOT/'scripts/phase3_control.py'),'submit','--name',args.name,
                        '--gpu',args.gpu,'--timeout',str(timeout),'--spec',str(path)],check=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--gpu',required=True);p.add_argument('--name',required=True)
    p.add_argument('--timeout',type=int);p.add_argument('--submit',action='store_true');main(p.parse_args())
