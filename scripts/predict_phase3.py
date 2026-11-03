"""Freeze calibration-only coefficients and every planned decision before a sweep."""
from collections import defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from phase3_plan import MAIN,MODELS,RATES,CONDITIONS,specification


def fit(xs,ys,degree):
    scale=max(xs);x=np.asarray(xs,dtype=float)/scale;y=np.asarray(ys,dtype=float)
    design=np.column_stack([x**d for d in range(degree+1)])
    candidates=[]
    for size in range(1,degree+2):
        for active in itertools.combinations(range(degree+1),size):
            part=np.linalg.lstsq(design[:,active],y,rcond=None)[0]
            if (part>=0).all():
                coefficients=np.zeros(degree+1);coefficients[list(active)]=part
                candidates.append(coefficients)
    best=min(candidates,key=lambda c:float(np.sum((design@c-y)**2)))
    return dict(scale=float(scale),coefficients=[float(v) for v in best],degree=degree,
                calibration_x=list(xs),calibration_y_ms=list(ys),method='nonnegative least squares over active coefficient sets')


def evaluate(model,x):return sum(c*(x/model['scale'])**i for i,c in enumerate(model['coefficients']))


def calibration(gpu):
    ledger=json.loads((ROOT/'outputs/phase3_ledger.json').read_text());rows=[];sources=[]
    for run in ledger['runs']:
        if run.get('gpu')!=gpu or run['purpose']!='calibration' or run['status']!='collected' or not run.get('use_for_prediction',True):continue
        path=ROOT/'outputs/raw/phase3'/run['name']/'output/results.jsonl'
        sources.append(dict(run_id=run['specification']['run_id'],sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        rows.extend(json.loads(line) for line in path.read_text().splitlines())
    if not rows:raise ValueError('No completed calibration for '+gpu)
    completed={r['model'] for r in rows if r['kind']=='model_complete' and r['completed']}
    assert set(MODELS)<=completed,'A requested model has not completed calibration'
    measurements=defaultdict(list);micros=defaultdict(list)
    for r in rows:
        if r['kind']=='measurement':
            assert r['condition'] in ['prefix_only','recompute','gpu_hit'],'Calibration included a tested reload outcome'
            assert r['valid'],'Calibration cache correctness failed'
            measurements[(r['model'],r['workload'],r['turn_tokens'],r['condition'],r['prefix_tokens'])].append(r['wall_ms'])
        elif r['kind']=='microbenchmark':micros[(r['model'],r['workload'],r['condition'],r['prefix_tokens'])].append(r)
    baseline={};legs={}
    for model in MODELS:
        workload='ultrachat' if model==MAIN else 'repeated_control'
        baseline[model]={};legs[model]={}
        for turn in ([32,256] if model==MAIN else [32]):
            baseline[model][str(turn)]={}
            for condition in ['prefix_only','recompute','gpu_hit']:
                points=sorted((key[-1],statistics.median(values)) for key,values in measurements.items() if key[:4]==(model,workload,turn,condition))
                assert len(points)>=3 and all(len(measurements[(model,workload,turn,condition,L)])>=3 for L,t in points)
                baseline[model][str(turn)][condition]=fit([L for L,t in points],[t for L,t in points],1 if condition=='gpu_hit' else 2)
        bpt=next(r['kv_bytes_per_token'] for r in rows if r['kind']=='model_config' and r['model']==model)
        for condition,fields in [('h2d_pinned',['transfer_ms']),('h2d_pageable',['transfer_ms']),
                                 ('file_legs_raw',['raw_read_ms','deserialize_ms','transfer_ms']),
                                 ('file_legs_torch',['raw_read_ms','deserialize_ms','transfer_ms']),
                                 ('file_legs_direct',['direct_load_ms','transfer_ms'])]:
            legs[model][condition]={}
            for field in fields:
                points=sorted((key[-1]*bpt,statistics.median(r[field] for r in values)) for key,values in micros.items()
                              if key[:3]==(model,workload,condition))
                assert len(points)>=3,'Missing independent microbenchmark leg'
                legs[model][condition][field]=fit([x for x,y in points],[y for x,y in points],1)
    return baseline,legs,sources,rows


def create(gpu):
    destination=ROOT/'configs'/('predictions_'+gpu+'.json')
    assert not destination.exists(),'Prediction registration is immutable; use a new registered experiment for changes'
    plan=json.loads((ROOT/'configs/phase3_plan.json').read_text())
    reference=json.loads((ROOT/'configs/phase3_t4_reference.json').read_text())
    baseline,legs,sources,rows=calibration(gpu)
    scheduled=[]
    for session in [1,2]:
        name=gpu.lower()+'-main-'+str(session)
        scheduled.append(dict(name=name,models=[MAIN],workload='ultrachat',
                              lengths_by_model={MAIN:plan['main_lengths']},turns_by_model={MAIN:[32,256]},seed=8600+session))
    scheduled.append(dict(name=gpu.lower()+'-controls',models=MODELS[1:],workload='repeated_control',
                          lengths_by_model=plan['control_lengths_by_model'],turns_by_model={m:[32] for m in MODELS[1:]},seed=8701))
    predictions=[]
    t4=reference['observations']
    for run in scheduled:
        for model in run['models']:
            bpt=reference['configs'][model]['kv_bytes_per_token']
            for length in run['lengths_by_model'][model]:
                for turn in run['turns_by_model'][model]:
                    fits=baseline[model][str(turn)];rec=evaluate(fits['recompute'],length);hit=evaluate(fits['gpu_hit'],length)
                    prefix=evaluate(fits['prefix_only'],length);payload=bpt*length
                    h=legs[model]['h2d_pinned']['transfer_ms']['coefficients'][0]
                    denominator=rec-hit-h;bstar=payload/denominator/1000 if denominator>0 else None
                    anchors=fits['recompute']['calibration_x']
                    region='anchor' if length in anchors else 'interpolation' if min(anchors)<length<max(anchors) else 'extrapolation'
                    old=[r['median'] for r in t4 if r['kind']=='phase2_summary' and r['purpose']=='sweep'
                         and r['model']==model and r['workload']==run['workload'] and r['turn_tokens']==turn
                         and r['prefix_tokens']==length and r['condition']=='prefix_only']
                    ratio=statistics.median(old)/prefix if old else None
                    for condition in CONDITIONS:
                        if condition=='recompute':expected=rec
                        elif condition=='prefix_only':expected=prefix
                        elif condition=='gpu_hit':expected=hit
                        elif condition=='simulated_unthrottled':expected=hit+evaluate(legs[model]['h2d_pinned']['transfer_ms'],payload)
                        elif condition.startswith('simulated_'):
                            rate=float(condition.split('_')[1])*1e6;expected=hit+payload/rate*1000+h
                        elif condition=='cpu_pageable':expected=hit+evaluate(legs[model]['h2d_pageable']['transfer_ms'],payload)
                        elif condition=='file_raw_staged':expected=hit+sum(evaluate(f,payload) for f in legs[model]['file_legs_raw'].values())
                        elif condition=='file_torch_direct':expected=hit+sum(evaluate(f,payload) for f in legs[model]['file_legs_direct'].values())
                        else:raise ValueError(condition)
                        predictions.append(dict(run_id='phase3-'+run['name'],gpu=gpu,model=model,workload=run['workload'],
                            prefix_tokens=length,turn_tokens=turn,condition=condition,simulated_bandwidth=condition.startswith('simulated_'),
                            kv_bytes_per_token=bpt,predicted_ttft_ms=expected,predicted_recompute_ms=rec,
                            predicted_gpu_hit_ms=hit,predicted_prefix_ms=prefix,predicted_bstar_mb_s=bstar,
                            hypothesis_prefill_ratio_to_t4=ratio,calibration_region=region,
                            predicted_reload=expected<rec if condition not in ['recompute','prefix_only'] else None))
    registration=dict(schema_version=3,kind='phase3_prediction_registration',phase='phase3',gpu=gpu,
                      calibration_only=True,calibration_sources=sources,baseline_fits=baseline,micro_fits=legs,
                      planned_runs=scheduled,predictions=predictions,
                      method='calibration-only nonnegative quadratic prefix/recompute; affine GPU-hit and transport; no sweep refit',
                      source_commit=__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    destination.write_text(json.dumps(registration,indent=2,allow_nan=False)+'\n')
    lines=['# Preregistered predictions: '+gpu,'',
           'Frozen using calibration data only, before any sweep for this GPU. The JSON registration contains every '
           'session/rate/path cell, coefficients, source hashes, expected TTFT, and the throughput-ratio hypothesis. '
           'The same main-model predictions apply to both independently allocated sweep sessions. '
           'T4 time measurements are used only in the hypothesis comparison, not the new-GPU fits.','',
           '| Model | Prefix | New turn | Predicted B*, MB/s | Expected prefill ratio to T4 | Decisions by rate/path |',
           '| --- | --- | --- | --- | --- | --- |']
    by=defaultdict(list)
    for r in predictions:
        if r['run_id'].endswith('-main-2') or r['condition'] in ['prefix_only','recompute']:continue
        by[(r['model'],r['prefix_tokens'],r['turn_tokens'])].append(r)
    for (model,length,turn),values in sorted(by.items()):
        first=values[0];b=first['predicted_bstar_mb_s'];ratio=first['hypothesis_prefill_ratio_to_t4']
        decisions='; '.join(r['condition']+': '+('reload' if r['predicted_reload'] else 'recompute') for r in values)
        lines.append(f"| {model} | {length} | {turn} | {format(b,'.3f') if b is not None else 'No positive denominator'} | "
                     f"{format(ratio,'.3f') if ratio is not None else 'No matched T4 length'} | {decisions} |")
    lines.extend(['','The swept simulated rates are 50, 100, 200, 400, 800, 1600 MB/s and unthrottled. '
                  'The unthrottled pinned control is scored once. File predictions include the independently measured '
                  'CPU load/read/deserialization and H2D legs. A nonpositive denominator predicts recomputation for any finite bandwidth.',''])
    (ROOT/'docs'/('PREDICTIONS_'+gpu+'.md')).write_text('\n'.join(lines))
    print('Wrote immutable prediction registration for',gpu)
    return registration

if __name__=='__main__':create(sys.argv[1])
