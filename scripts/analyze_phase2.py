"""Analyze simulated-bandwidth crossovers without pooling independent sessions."""
from collections import defaultdict
import argparse
import csv
import datetime
import json
from pathlib import Path
import re
import statistics
import sys

import numpy as np
from analyze_pilot import interval

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['run_id', 'model', 'workload', 'prefix_tokens', 'turn_tokens']


def crossover(points):
    """Crossover brackets are observations; harmonic interpolation is model-assisted."""
    points = sorted(points, key=lambda p: p['target_mb_s'] if p['target_mb_s'] is not None else float('inf'))
    brackets = []
    for a, b in zip(points, points[1:]):
        if a['delta_ms'] > 0 and b['delta_ms'] < 0:
            w = a['delta_ms'] / (a['delta_ms'] - b['delta_ms'])
            ba, bb = a['achieved_mb_s'], b['achieved_mb_s']
            estimate = 1 / ((1-w)/ba + w/bb) if ba > 0 and bb > 0 else None
            brackets.append(dict(target_mb_s=[a['target_mb_s'], b['target_mb_s']],
                                 achieved_mb_s=[ba, bb],
                                 interpolated_mb_s=estimate,
                                 paired_ci_resolved=(a.get('paired_delta',{}).get('ci95',[0,0])[0] > 0 and
                                                     b.get('paired_delta',{}).get('ci95',[0,0])[1] < 0),
                                 interpretation='harmonic interpolation of median TTFT; not a directly sampled threshold'))
    if brackets:
        return dict(status='bracketed', brackets=brackets,
                    nonmonotone=any(a['delta_ms'] < 0 < b['delta_ms'] for a,b in zip(points,points[1:])))
    if all(p['delta_ms'] < 0 for p in points):
        return dict(status='reload_faster_at_all_tested_simulated_rates',
                    upper_bound_target_mb_s=points[0]['target_mb_s'])
    if all(p['delta_ms'] > 0 for p in points):
        return dict(status='recompute_faster_at_all_tested_simulated_rates',
                    largest_achieved_mb_s=max(p['achieved_mb_s'] for p in points))
    return dict(status='unresolved_or_nonmonotone')


def fit_overhead(pairs):
    xs, ys = np.asarray([x for x,y in pairs]), np.asarray([y for x,y in pairs])
    if len(set(xs)) < 2:
        return 0.0, 'not_identified_from_single_payload'
    design = np.column_stack([np.ones(len(xs)), xs])
    raw, *_ = np.linalg.lstsq(design, ys, rcond=None)
    candidates = [np.array([ys.mean(), 0]), np.array([0, np.dot(xs,ys)/np.dot(xs,xs)])]
    if (raw >= 0).all():
        candidates.append(raw)
    best = min(candidates,key=lambda a:np.sum((design@a-ys)**2))
    return float(best[0]), 'nonnegative_microbenchmark_fit'


def telemetry(path):
    if not path.exists():
        return []
    data = []
    with path.open() as f:
        for row in csv.DictReader(f, skipinitialspace=True):
            try:
                if int(row['index']) != 0:
                    continue
                stamp = datetime.datetime.strptime(row['timestamp'].strip(), '%Y/%m/%d %H:%M:%S.%f')
                value = dict(timestamp_unix=stamp.replace(tzinfo=datetime.timezone.utc).timestamp())
                for key in ['clocks.sm','clocks.mem','temperature.gpu','power.draw','utilization.gpu']:
                    value[key] = float(row[key])
                reason = row.get('clocks_throttle_reasons.active', row.get('clocks_event_reasons.active'))
                value['throttle_reasons'] = reason.strip() if reason else None
                data.append(value)
            except (ValueError, KeyError, TypeError):
                continue
    return data


def analyze(source_results=None):
    ledger = json.loads((ROOT / 'outputs/phase2_ledger.json').read_text())
    raw, telemetry_by_run, purposes = [], {}, {}
    archived=[]
    if source_results:
        archived=[json.loads(x) for x in Path(source_results).read_text().splitlines()]
    for run in ledger['runs']:
        path = ROOT / 'outputs/raw/phase2' / run['name'] / 'phase2-output/results.jsonl'
        if run['status'] != 'fetched':
            continue
        if source_results:
            rows=[r for r in archived if r.get('record_origin')=='kernel'
                  and r.get('run_id')==run['specification']['run_id']]
        elif path.exists():
            rows = [json.loads(x) for x in path.read_text().splitlines()]
        else:
            continue
        if not rows:continue
        for row in rows:row['record_origin']='kernel'
        raw.extend(rows)
        purposes[rows[0]['run_id']] = run['purpose']
        telemetry_by_run[rows[0]['run_id']] = (
            [r['sample'] for r in archived if r.get('kind')=='telemetry_sample' and r['run_id']==rows[0]['run_id']]
            if source_results else telemetry(path.parent / 'telemetry.csv'))
    if not raw:
        raise ValueError('No source observations found; use --from-results outputs/results.jsonl for the public archive')
    derived = []

    def emit(kind, **fields):
        derived.append(dict(schema_version=2, phase='phase2', record_origin='analysis', kind=kind, **fields))

    emit('phase2_analysis_metadata',python=sys.version,numpy=np.__version__,
         bootstrap_resamples=10000,bootstrap_seed=7321,
         source_run_ids=sorted(purposes),session_pooling=False)

    groups, micros, seen = defaultdict(list), defaultdict(list), set()
    for r in raw:
        if r['kind'] == 'measurement':
            key = tuple(r[k] for k in FIELDS) + (r['condition'],)
            unique = key + (r['repeat'],)
            if unique in seen:
                raise ValueError('Duplicate measurement key: ' + str(unique))
            seen.add(unique)
            if r['repeat'] >= 0 and r['valid']:
                groups[key].append(r)
        elif r['kind'] == 'microbenchmark':
            key = (r['run_id'],r['model'],r['workload'],r['prefix_tokens'],r['condition'])
            micros[key].append(r)
    summaries = {}
    for key, values in groups.items():
        fields = dict(zip(FIELDS + ['condition'], key))
        fields.update(environment=values[0]['environment'], kv_bytes_per_token=values[0]['kv_bytes_per_token'],
                      attention_family=values[0]['attention_family'],
                      purpose=purposes[key[0]], simulated_bandwidth=values[0]['simulated_bandwidth'])
        summary = interval([r['wall_ms'] for r in values])
        summary['publication_repeat_count_met'] = len(values) >= 10
        summaries[key] = summary
        emit('phase2_summary', **fields, **summary)
    overhead = {}
    by_model_run = defaultdict(list)
    for key, values in micros.items():
        if key[-1] == 'h2d_pinned':
            by_model_run[key[:3]].append((values[0]['bytes'], statistics.median(r['transfer_ms'] for r in values)))
    for key, pairs in by_model_run.items():
        h, method = fit_overhead(pairs)
        overhead[key] = h
        emit('phase2_overhead', run_id=key[0], model=key[1], workload=key[2], overhead_ms=h, method=method)
    shapes = sorted(set(k[:5] for k in groups))
    for shape in shapes:
        run_id, model, workload, length, turn = shape
        if purposes[run_id] != 'sweep':
            continue
        required=['prefix_only','recompute','gpu_hit','cpu_pageable','file_torch_direct',
                  'file_torch_staged','file_raw_staged','simulated_unthrottled']
        required += ['simulated_'+str(rate)+'_MBps' for rate in [50,100,200,400,800,1600]]
        incomplete={name:len(groups.get(shape+(name,),[])) for name in required
                    if len(groups.get(shape+(name,),[]))<10}
        emit('shape_publication_coverage',**dict(zip(FIELDS,shape)),complete=not incomplete,
             missing_or_short_conditions=incomplete,required_repeats=10)
        if incomplete:
            continue
        if any(shape + (name,) not in summaries for name in ['prefix_only','recompute','gpu_hit']):
            continue
        rec = summaries[shape+('recompute',)]['median']
        hit = summaries[shape+('gpu_hit',)]['median']
        prefill = summaries[shape+('prefix_only',)]['median']
        row = groups[shape+('recompute',)][0]
        payload = row['kv_bytes']
        h = overhead[shape[:3]]
        denominator = rec - hit - h
        predicted = payload * 1000 / denominator / 1e6 if denominator > 0 else None
        prefix_threshold = payload * 1000 / prefill / 1e6
        rec_values = {r['repeat']:r['wall_ms'] for r in groups[shape+('recompute',)]}
        points = []
        for key, values in groups.items():
            if key[:5] != shape or not key[-1].startswith('simulated_'):
                continue
            target = values[0]['target_bandwidth_bytes_s']
            common = [r for r in values if r['repeat'] in rec_values]
            delta = interval([r['wall_ms']-rec_values[r['repeat']] for r in common])
            achieved = statistics.median(r['achieved_transport_bytes_s'] for r in values) / 1e6
            points.append(dict(condition=key[-1], target_mb_s=target/1e6 if target else None,
                               achieved_mb_s=achieved,
                               delta_ms=summaries[key]['median']-rec,
                               paired_delta=delta, repeats=len(values)))
            expected_load = payload/(target or achieved*1e6)*1000 + h
            emit('simulated_rule_prediction', **dict(zip(FIELDS,shape)), condition=key[-1],
                 simulated_bandwidth=True, target_mb_s=target/1e6 if target else None,
                 achieved_mb_s=achieved, predicted_ttft_ms=hit+expected_load,
                 recompute_ttft_ms=rec, gpu_hit_ms=hit, prefix_prefill_ms=prefill,
                 prefix_rule_predicts_reload=expected_load<prefill,
                 ttft_rule_predicts_reload=hit+expected_load<rec,
                 measured_reload_faster=(True if delta['ci95'][1]<0 else False if delta['ci95'][0]>0 else None),
                 measured_ttft_ms=summaries[key]['median'],
                 measured_transport_ms=statistics.median(r['transfer_ms'] for r in values),
                 paired_delta_ms=delta, sleep_median_ms=statistics.median(r['rate_limiter_sleep_ms'] for r in values))
        if points:
            cross = crossover(points)
            emit('bandwidth_crossover', **dict(zip(FIELDS,shape)),
                 environment=row['environment'], attention_family=row['attention_family'],
                 kv_bytes_per_token=row['kv_bytes_per_token'], simulated_bandwidth=True,
                 predicted_prefix_bstar_mb_s=prefix_threshold,
                 predicted_prefix_overhead_bstar_mb_s=payload*1000/(prefill-h)/1e6 if prefill>h else None,
                 predicted_ttft_bstar_mb_s=predicted, overhead_ms=h,
                 measured=cross, points=points, repeats_met=all(p['repeats']>=10 for p in points))
        for fmt in ['torch','raw']:
            key = shape + ('file_' + fmt + '_staged',)
            micro = micros.get(shape[:3]+(length,'file_legs_'+fmt))
            if key not in summaries or not micro:
                continue
            read = statistics.median(r['raw_read_ms'] for r in micro)
            deserialize = statistics.median(r['deserialize_ms'] for r in micro)
            h2d = statistics.median(r['transfer_ms'] for r in micro)
            observed = summaries[key]['median']
            old, new = hit + read + h2d, hit + read + deserialize + h2d
            emit('file_rule_residual', **dict(zip(FIELDS,shape)), format=fmt,
                 raw_read_ms=read, deserialize_ms=deserialize, h2d_ms=h2d,
                 measured_ttft_ms=observed, old_predicted_ms=old, new_predicted_ms=new,
                 old_signed_relative_error=(old-observed)/observed,
                 new_signed_relative_error=(new-observed)/observed,
                 physical_read_ratio_median=statistics.median(r['physical_read_bytes']/r['bytes'] for r in micro))
    across = defaultdict(list)
    scored=defaultdict(list)
    for r in derived:
        if r['kind']=='simulated_rule_prediction' and r['measured_reload_faster'] is not None:
            scored[(r['model'],r['workload'])].append(r)
    for (model,workload),values in scored.items():
        emit('phase2_rule_classification',model=model,workload=workload,
             resolved_comparisons=len(values),
             prefix_rule_agreements=sum(r['prefix_rule_predicts_reload']==r['measured_reload_faster'] for r in values),
             ttft_rule_agreements=sum(r['ttft_rule_predicts_reload']==r['measured_reload_faster'] for r in values),
             interpretation='descriptive counts over resolved simulated-rate cells; not independent generalization trials')
    for r in derived:
        if r['kind']=='phase2_summary' and r['purpose']=='sweep' and r['publication_repeat_count_met'] and r['model']=='Qwen/Qwen2.5-1.5B' and r['workload']=='ultrachat':
            key=(r['environment']['requested_gpu'],r['prefix_tokens'],r['turn_tokens'],r['condition'])
            across[key].append(r)
    for key, values in across.items():
        if len(values) > 1:
            medians = [r['median'] for r in values]
            emit('session_spread', model='Qwen/Qwen2.5-1.5B', workload='ultrachat',
                 gpu=key[0], prefix_tokens=key[1], turn_tokens=key[2], condition=key[3],
                 sessions=len(values), session_run_ids=[r['run_id'] for r in values],
                 session_medians_ms=medians, minimum_ms=min(medians), maximum_ms=max(medians),
                 sample_sd_ms=statistics.stdev(medians), relative_range=(max(medians)-min(medians))/statistics.median(medians),
                 within_session_ci95_ms=[r['ci95'] for r in values])
    source_run='phase2-main-session-1'
    heldout=defaultdict(list)
    for shape in shapes:
        run_id,model,workload,length,turn=shape
        if run_id==source_run or model!='Qwen/Qwen2.5-1.5B' or workload!='ultrachat' or purposes[run_id]!='sweep':
            continue
        source_shape=(source_run,model,workload,length,turn)
        if source_shape+('recompute',) not in summaries or source_shape+('gpu_hit',) not in summaries:
            continue
        source_rec=summaries[source_shape+('recompute',)]['median']
        source_hit=summaries[source_shape+('gpu_hit',)]['median']
        source_h=overhead[source_shape[:3]]
        source_copy=micros.get(source_shape[:3]+(length,'h2d_pinned'),[])
        actual_rec={r['repeat']:r['wall_ms'] for r in groups.get(shape+('recompute',),[])}
        for key,values in groups.items():
            if key[:5]!=shape or not key[-1].startswith('simulated_') or not actual_rec:
                continue
            if len(values)<10 or len(actual_rec)<10:
                continue
            target=values[0]['target_bandwidth_bytes_s']
            payload=values[0]['kv_bytes']
            load=payload/target*1000+source_h if target else statistics.median(r['transfer_ms'] for r in source_copy)
            delta=interval([r['wall_ms']-actual_rec[r['repeat']] for r in values if r['repeat'] in actual_rec])
            observed=True if delta['ci95'][1]<0 else False if delta['ci95'][0]>0 else None
            expected=source_hit+load
            value=dict(**dict(zip(FIELDS,shape)),condition=key[-1],calibration_run=source_run,
                       predicted_reload_faster=expected<source_rec,measured_reload_faster=observed,
                       predicted_ttft_ms=expected,measured_ttft_ms=summaries[key]['median'],
                       relative_error=(expected-summaries[key]['median'])/summaries[key]['median'])
            emit('heldout_session_prediction',**value)
            heldout[run_id].append(value)
    for run_id,values in heldout.items():
        resolved=[r for r in values if r['measured_reload_faster'] is not None]
        emit('heldout_session_score',run_id=run_id,calibration_run=source_run,
             resolved_cells=len(resolved),agreements=sum(r['predicted_reload_faster']==r['measured_reload_faster'] for r in resolved),
             median_absolute_relative_ttft_error=statistics.median(abs(r['relative_error']) for r in values),
             interpretation='same model/input/lengths, first-session calibration fixed; separate GPU kernel session, not a different GPU type')
    for shape in shapes:
        if shape[1]!='Qwen/Qwen2.5-1.5B' or shape[3:]!=(8192,32) or purposes[shape[0]]!='sweep':
            continue
        a=groups.get(shape+('prefix_only',),[])
        b=groups.get(shape+('recompute',),[])
        by_repeat={r['repeat']:r for r in b}
        paired=[r['wall_ms']-by_repeat[r['repeat']]['wall_ms'] for r in a if r['repeat'] in by_repeat]
        if paired:
            emit('prefill_anomaly_pair',**dict(zip(FIELDS,shape)),
                 prefix_minus_prefix_plus_turn_ms=interval(paired),
                 interpretation='positive value reproduces prefix-only slower than prefix-plus-turn in interleaved rounds')
    for run_id, values in telemetry_by_run.items():
        for sample in values:emit('telemetry_sample',run_id=run_id,sample=sample)
        if values:
            fields={k:dict(minimum=min(r[k] for r in values),maximum=max(r[k] for r in values),
                           median=statistics.median(r[k] for r in values))
                    for k in ['clocks.sm','clocks.mem','temperature.gpu','power.draw','utilization.gpu']}
            emit('telemetry_summary', run_id=run_id, samples=len(values), gpu_index=0,
                 effective_sample_hz=(len(values)-1)/(values[-1]['timestamp_unix']-values[0]['timestamp_unix']) if len(values)>1 else None,
                 throttle_reason_values=sorted(set(r['throttle_reasons'] for r in values)), metrics=fields)
            environment_row=next((r for r in raw if r['run_id']==run_id and r['kind']=='environment'),None)
            limits=re.findall(r'(\d+)W\s*/\s*(\d+)W',environment_row.get('nvidia_smi','')) if environment_row else []
            if limits:
                cap=float(limits[0][1])
                emit('telemetry_power_quality',run_id=run_id,startup_reported_power_cap_w=cap,
                     samples_above_cap=sum(r['power.draw']>cap for r in values),
                     maximum_reported_power_w=max(r['power.draw'] for r in values),
                     interpretation='raw sensor samples retained; not used to infer energy or instantaneous physical power accuracy')
    for key, samples in groups.items():
        if purposes[key[0]] != 'sweep':
            continue
        values = telemetry_by_run.get(key[0],[])
        if not values:
            continue
        matched, nearest = [], 0
        stamps = np.array([r['timestamp_unix'] for r in values])
        for sample in samples:
            start, end = sample['wall_start_unix'], sample['wall_end_unix']
            indices = np.where((stamps>=start)&(stamps<=end))[0]
            if not len(indices):
                index=int(np.argmin(abs(stamps-(start+end)/2)))
                if abs(stamps[index]-(start+end)/2) <= 0.75:
                    indices=[index]
                    nearest += 1
            matched.extend(values[int(i)] for i in indices)
        if matched:
            emit('timing_clock_summary', **dict(zip(FIELDS+['condition'],key)),
                 telemetry_points=len(matched), nearest_sample_measurements=nearest,
                 median_sm_mhz=statistics.median(r['clocks.sm'] for r in matched),
                 minimum_sm_mhz=min(r['clocks.sm'] for r in matched),
                 maximum_sm_mhz=max(r['clocks.sm'] for r in matched),
                 median_temperature_c=statistics.median(r['temperature.gpu'] for r in matched),
                 median_power_w=statistics.median(r['power.draw'] for r in matched),
                 reason_masks=sorted(set(r['throttle_reasons'] for r in matched)),
                 caveat='one-Hz telemetry; nearest samples used for subsecond timings; repeated matches are not independent')
    for run in ledger['runs']:
        path = ROOT/'outputs/raw/phase2'/run['name']/'phase2-output/anomaly-trace.json'
        if source_results or not path.exists():
            derived.extend(r for r in archived if r.get('kind')=='anomaly_shape_profile'
                           and r['run_id']==run['specification']['run_id'])
            continue
        events=json.loads(path.read_text())['traceEvents']
        for scope in [e for e in events if e.get('cat')=='user_annotation' and e.get('name','').startswith('shape_')]:
            inside=[e for e in events if e.get('cat')=='kernel' and e.get('ts',-1)>=scope['ts']
                    and e.get('ts',0)+e.get('dur',0)<=scope['ts']+scope['dur']]
            gemms=[e for e in inside if 'gemm' in e['name'] or 'gemvx' in e['name']]
            emit('anomaly_shape_profile', run_id='phase2-'+run['name'],
                 length=int(scope['name'].split('_')[-1]), wall_ms=scope['dur']/1000,
                 gpu_kernel_ms=sum(e['dur'] for e in inside)/1000,
                 gemm_ms=sum(e['dur'] for e in gemms)/1000,
                 gemm_kernels=sorted(set(e['name'] for e in gemms)),
                 excluded_from_benchmark_statistics=True)
    output = ROOT / 'outputs/phase2_results.jsonl'
    output.write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in raw+derived))
    print(json.dumps(dict(raw_rows=len(raw), derived_rows=len(derived), groups=len(groups), output=str(output))))
    return raw, derived


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--from-results',type=Path,help='Recompute from public kernel observations and telemetry samples')
    args=parser.parse_args()
    analyze(args.from_results)
