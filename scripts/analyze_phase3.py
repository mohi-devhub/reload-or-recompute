"""Score committed hardware predictions without refitting; retain session identity."""
import argparse
from collections import defaultdict
import csv
import datetime
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from analyze_pilot import interval
from analyze_phase2 import crossover,telemetry
from phase3_plan import MAIN,MODELS,CONDITIONS

FIELDS=['run_id','model','workload','prefix_tokens','turn_tokens']


def archived_rows(ledger,source=None):
    archive=[]
    if source:
        with Path(source).open() as f:
            archive=[json.loads(line) for line in f if line.strip()]
    raw=[];samples=[]
    for run in ledger['runs']:
        if run['purpose']=='prepare' or run['status']!='collected':continue
        run_id=run['specification']['run_id']
        if source:
            rows=[r for r in archive if r.get('phase')=='phase3' and r.get('record_origin')=='kernel' and r.get('run_id')==run_id]
            stream=[r['sample'] for r in archive if r.get('phase')=='phase3' and r.get('kind')=='telemetry_sample' and r.get('run_id')==run_id]
        else:
            folder=ROOT/'outputs/raw/phase3'/run['name']/'output'
            rows=[json.loads(line) for line in (folder/'results.jsonl').read_text().splitlines()]
            stream=telemetry(folder/'telemetry.csv')
            # Extend the established telemetry parser with PCIe fields.
            by_time={r['timestamp_unix']:r for r in stream}
            with (folder/'telemetry.csv').open() as f:
                for row in csv.DictReader(f,skipinitialspace=True):
                    try:
                        stamp=datetime.datetime.strptime(row['timestamp'].strip(),'%Y/%m/%d %H:%M:%S.%f').replace(tzinfo=datetime.timezone.utc).timestamp()
                        for field in ['pcie.link.gen.current','pcie.link.gen.max','pcie.link.width.current','pcie.link.width.max']:
                            by_time[stamp][field]=float(row[field])
                    except (ValueError,KeyError,TypeError):pass
        for r in rows:r['record_origin']='kernel'
        raw.extend(rows)
        samples.extend(dict(phase='phase3',schema_version=3,kind='telemetry_sample',record_origin='telemetry',run_id=run_id,sample=s) for s in stream)
    return raw,samples


def analyze(source=None):
    ledger=json.loads((ROOT/'outputs/phase3_ledger.json').read_text())
    raw,streams=archived_rows(ledger,source)
    purposes={r['specification']['run_id']:r['purpose'] for r in ledger['runs'] if r.get('specification')}
    registrations={}
    for gpu in ['L4','A10','H100!']:
        path=ROOT/'configs'/('predictions_'+gpu+'.json')
        if path.exists():registrations[gpu]=json.loads(path.read_text())
    prediction={tuple(p[k] for k in FIELDS)+ (p['condition'],):p for reg in registrations.values() for p in reg['predictions']}
    derived=[]
    def emit(kind,**fields):
        row=dict(schema_version=3,phase='phase3',record_origin='analysis',kind=kind,**fields);derived.append(row);return row
    emit('phase3_analysis_metadata',bootstrap_resamples=10000,bootstrap_seed=7321,refitted=False,session_pooling=False)
    groups=defaultdict(list);micros=defaultdict(list);seen=set()
    for r in raw:
        if r['kind']=='measurement':
            key=tuple(r[k] for k in FIELDS)+(r['condition'],);unique=key+(r['repeat'],)
            assert unique not in seen,'Duplicate sample';seen.add(unique)
            if r['valid'] and r['repeat']>=0:groups[key].append(r)
        elif r['kind']=='microbenchmark':micros[(r['run_id'],r['model'],r['workload'],r['prefix_tokens'],r['condition'])].append(r)
    summaries={}
    for key,values in groups.items():
        fields=dict(zip(FIELDS+['condition'],key));summary=interval([r['wall_ms'] for r in values])
        row=emit('phase3_summary',**fields,**summary,purpose=purposes[key[0]],gpu=values[0]['environment']['requested_gpu'],
                 environment=values[0]['environment'],kv_bytes_per_token=values[0]['kv_bytes_per_token'],
                 complete=len(values)>=10,attention_family=values[0]['attention_family'])
        if key[-1]=='prefix_only':row['prefill_tokens_s']=key[3]*1000/summary['median']
        summaries[key]=row
    for key,values in micros.items():
        emit('phase3_micro_summary',**dict(zip(['run_id','model','workload','prefix_tokens','condition'],key)),
             gpu=values[0]['environment']['requested_gpu'],purpose=purposes[key[0]],
             bandwidth_mb_s=interval([r['bytes']/r['transfer_ms']/1000 for r in values]) if key[-1].startswith('h2d_') else None,
             leg_timings_ms={field:interval([r[field] for r in values]) for field in ['raw_read_ms','deserialize_ms','direct_load_ms','transfer_ms'] if field in values[0]},
             physical_read_ratio_median=statistics.median(r['physical_read_bytes']/r['bytes'] for r in values) if 'physical_read_bytes' in values[0] else None)
    scored=[]
    for key,p in prediction.items():
        observed=summaries.get(key)
        if observed is None or not observed['complete']:
            emit('phase3_missing_prediction_cell',**{k:p[k] for k in FIELDS+['condition','gpu']},observed_repeats=observed['n'] if observed else 0)
            continue
        rec_key=key[:5]+('recompute',)
        delta=None;decision=None
        if p['predicted_reload'] is not None and summaries.get(rec_key,{}).get('complete'):
            rec={r['repeat']:r['wall_ms'] for r in groups[rec_key]}
            delta=interval([r['wall_ms']-rec[r['repeat']] for r in groups[key] if r['repeat'] in rec])
            decision=True if delta['ci95'][1]<0 else False if delta['ci95'][0]>0 else None
        error=p['predicted_ttft_ms']-observed['median']
        row=emit('phase3_prediction_score',**p,observed_ttft_ms=observed['median'],observed_ci95_ms=observed['ci95'],
                 signed_error_ms=error,absolute_error_ms=abs(error),absolute_relative_error=abs(error)/observed['median'],
                 paired_path_minus_recompute_ms=delta,observed_reload=decision,
                 correct=decision==p['predicted_reload'] if decision is not None else None)
        scored.append(row)
    shapes=sorted({k[:5] for k in groups if purposes[k[0]]=='sweep'})
    crosses=[]
    t4=json.loads((ROOT/'configs/phase3_t4_reference.json').read_text())['observations']
    for shape in shapes:
        if not all(summaries.get(shape+(c,),{}).get('complete') for c in CONDITIONS):continue
        fields=dict(zip(FIELDS,shape));rec=summaries[shape+('recompute',)];pref=summaries[shape+('prefix_only',)]
        rec_values={r['repeat']:r['wall_ms'] for r in groups[shape+('recompute',)]}
        points=[]
        for condition in CONDITIONS:
            if not condition.startswith('simulated_'):continue
            values=groups[shape+(condition,)]
            target=values[0]['target_bandwidth_bytes_s']
            delta=interval([r['wall_ms']-rec_values[r['repeat']] for r in values])
            points.append(dict(condition=condition,target_mb_s=target/1e6 if target else None,
                               achieved_mb_s=statistics.median(r['achieved_transport_bytes_s'] for r in values)/1e6,
                               delta_ms=summaries[shape+(condition,)]['median']-rec['median'],paired_delta=delta))
        p=prediction[shape+('recompute',)]
        observed=crossover(points)
        matched_prefill=[r['prefill_tokens_s'] for r in t4 if r['kind']=='phase2_summary' and r['purpose']=='sweep'
                         and r['model']==shape[1] and r['workload']==shape[2] and r['prefix_tokens']==shape[3]
                         and r['turn_tokens']==shape[4] and r['condition']=='prefix_only']
        t4_tps=statistics.median(matched_prefill) if matched_prefill else None
        row=emit('phase3_bandwidth_crossover',**fields,gpu=p['gpu'],kv_bytes_per_token=p['kv_bytes_per_token'],
                 predicted_bstar_mb_s=p['predicted_bstar_mb_s'],predicted_prefill_tokens_s=shape[3]*1000/p['predicted_prefix_ms'],
                 measured_prefill_tokens_s=pref['prefill_tokens_s'],measured=observed,points=points,
                 t4_prefill_tokens_s=t4_tps,measured_prefill_ratio_to_t4=pref['prefill_tokens_s']/t4_tps if t4_tps else None,
                 calibration_region=p['calibration_region'],hypothesis_prefill_ratio_to_t4=p['hypothesis_prefill_ratio_to_t4'])
        crosses.append(row)
        old=[r for r in t4 if r['kind']=='bandwidth_crossover' and r['model']==shape[1] and r['workload']==shape[2] and r['prefix_tokens']==shape[3] and r['turn_tokens']==shape[4]]
        bounds=[];comparisons=[]
        ratio=p['hypothesis_prefill_ratio_to_t4']
        for old_row in old:
            for a in observed.get('brackets',[]):
                for b in old_row['measured'].get('brackets',[]):
                    if a['paired_ci_resolved'] and b['paired_ci_resolved']:
                        bound=[min(a['achieved_mb_s'])/max(b['achieved_mb_s']),max(a['achieved_mb_s'])/min(b['achieved_mb_s'])]
                        bounds.append(bound)
                        comparisons.append(dict(t4_run_id=old_row['run_id'],observed_ratio_interval=bound,
                                                compatible=bound[0]<=ratio<=bound[1] if ratio is not None else None))
        emit('phase3_hypothesis_score',**fields,gpu=p['gpu'],frozen_expected_ratio=ratio,
             observed_ratio_intervals=bounds,compatible=any(lo<=ratio<=hi for lo,hi in bounds) if bounds and ratio is not None else None,
             compatible_all=all(lo<=ratio<=hi for lo,hi in bounds) if bounds and ratio is not None else None,
             comparisons=comparisons,measured_prefill_ratio_to_t4=pref['prefill_tokens_s']/t4_tps if t4_tps else None,
             interpretation='resolved achieved-bandwidth brackets; no ratio inferred from censored thresholds')
    # Aggregate only score summaries; observations keep run and session identity.
    for gpu in registrations:
        for scope,subset in [('all',[s for s in scored if s['gpu']==gpu])]+[(r,[s for s in scored if s['gpu']==gpu and s['calibration_region']==r]) for r in ['anchor','interpolation','extrapolation']]:
            if not subset:continue
            decisions=[r for r in subset if r['correct'] is not None]
            emit('phase3_scorecard',gpu=gpu,scope=scope,complete_cells=len(subset),resolved_decisions=len(decisions),
                 correct_decisions=sum(r['correct'] for r in decisions),
                 unresolved_decisions=sum(r['predicted_reload'] is not None and r['correct'] is None for r in subset),
                 median_absolute_ttft_error_ms=statistics.median(r['absolute_error_ms'] for r in subset),
                 median_absolute_relative_ttft_error=statistics.median(r['absolute_relative_error'] for r in subset))
        for condition in CONDITIONS:
            subset=[s for s in scored if s['gpu']==gpu and s['condition']==condition]
            if subset:
                decisions=[s for s in subset if s['correct'] is not None]
                emit('phase3_path_scorecard',gpu=gpu,condition=condition,complete_cells=len(subset),resolved_decisions=len(decisions),
                     correct_decisions=sum(s['correct'] for s in decisions),median_absolute_ttft_error_ms=statistics.median(s['absolute_error_ms'] for s in subset))
    across=defaultdict(list)
    for r in summaries.values():
        if r['purpose']=='sweep' and r['complete'] and r['model']==MAIN and r['workload']=='ultrachat':
            across[(r['gpu'],r['prefix_tokens'],r['turn_tokens'],r['condition'])].append(r)
    for (gpu,L,N,c),values in across.items():
        if len(values)<2:continue
        medians=[r['median'] for r in values]
        emit('phase3_session_spread',gpu=gpu,model=MAIN,prefix_tokens=L,turn_tokens=N,condition=c,
             sessions=[r['run_id'] for r in values],medians_ms=medians,ci95_ms=[r['ci95'] for r in values],
             range_over_median=(max(medians)-min(medians))/statistics.median(medians))
    for run in ledger['runs']:
        if run.get('purpose')=='prepare' or run['status']!='collected':continue
        run_id=run['specification']['run_id'];samples=[s['sample'] for s in streams if s['run_id']==run_id]
        trials=[r for r in raw if r['kind']=='measurement' and r['run_id']==run_id]
        active=[s for s in samples if any(r['wall_start_unix']<=s['timestamp_unix']<=r['wall_end_unix'] for r in trials)]
        emit('phase3_telemetry_summary',run_id=run_id,gpu=run['gpu'],sample_count=len(samples),timing_sample_count=len(active),
             timing_ranges={field:[min(s[field] for s in active if field in s),max(s[field] for s in active if field in s)] for field in ['clocks.sm','clocks.mem','temperature.gpu','power.draw','pcie.link.gen.current','pcie.link.width.current'] if any(field in s for s in active)},
             timing_throttle_reasons=sorted({s['throttle_reasons'] for s in active if s.get('throttle_reasons')}))
    invalid=[r for r in raw if r['kind']=='measurement' and not r['valid']]
    provenance=[r for r in raw if r['kind']=='source_provenance']
    audit=emit('phase3_audit',measurements=sum(r['kind']=='measurement' for r in raw),invalid_measurements=len(invalid),
               missing_prediction_cells=sum(r['kind']=='phase3_missing_prediction_cell' for r in derived),
               protected_source_all_match=all(r['protected_functions_match_t4'] for r in provenance),source_run_count=len(provenance),
               main_cost_estimate_and_reservation_usd=ledger['infrastructure_reservation_usd']+sum(r.get('estimated_cost_usd',r['reserved_cost_usd']) for r in ledger['runs'] if r.get('gpu')!='H100!'),
               h100_cost_estimate_and_reservation_usd=sum(r.get('estimated_cost_usd',r['reserved_cost_usd']) for r in ledger['runs'] if r.get('gpu')=='H100!'))
    assert not invalid,'Cache correctness failures require investigation'
    assert audit['main_cost_estimate_and_reservation_usd']<=6 and audit['h100_cost_estimate_and_reservation_usd']<=4
    records=raw+streams+derived
    records.extend(dict(phase='phase3',record_origin='control',kind='phase3_run_ledger',**r) for r in ledger['runs'])
    records.extend(registrations.values())
    (ROOT/'outputs/phase3_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    (ROOT/'outputs/phase3_analysis.jsonl').write_text(''.join(json.dumps(r,allow_nan=False,separators=(',',':'))+'\n' for r in derived))
    return records,derived,registrations


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--from-results');parser.add_argument('--publish',action='store_true');args=parser.parse_args()
    records,derived,registrations=analyze(args.from_results)
    if args.publish:
        path=ROOT/'outputs/results.jsonl';temporary=path.with_suffix('.tmp')
        with temporary.open('w') as f:
            with path.open() as old:
                for line in old:
                    if json.loads(line).get('phase')!='phase3':f.write(line)
            for row in records:f.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n')
        temporary.replace(path)
    print(json.dumps(next(r for r in derived if r['kind']=='phase3_audit')))


if __name__=='__main__':main()
