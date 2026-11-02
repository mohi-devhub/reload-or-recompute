"""Analyze simulated-bandwidth crossovers without pooling independent sessions."""
from collections import defaultdict
import csv
import datetime
import json
from pathlib import Path
import statistics

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


def analyze():
    ledger = json.loads((ROOT / 'outputs/phase2_ledger.json').read_text())
    raw, telemetry_by_run, purposes = [], {}, {}
    for run in ledger['runs']:
        path = ROOT / 'outputs/raw/phase2' / run['name'] / 'phase2-output/results.jsonl'
        if run['status'] != 'fetched' or not path.exists():
            continue
        rows = [json.loads(x) for x in path.read_text().splitlines()]
        raw.extend(rows)
        purposes[rows[0]['run_id']] = run['purpose']
        telemetry_by_run[rows[0]['run_id']] = telemetry(path.parent / 'telemetry.csv')
    derived = []

    def emit(kind, **fields):
        derived.append(dict(schema_version=2, phase='phase2', kind=kind, **fields))

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
    for r in derived:
        if r['kind']=='phase2_summary' and r['purpose']=='sweep' and r['model']=='Qwen/Qwen2.5-1.5B' and r['workload']=='ultrachat':
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
    for run_id, values in telemetry_by_run.items():
        if values:
            fields={k:dict(minimum=min(r[k] for r in values),maximum=max(r[k] for r in values),
                           median=statistics.median(r[k] for r in values))
                    for k in ['clocks.sm','clocks.mem','temperature.gpu','power.draw','utilization.gpu']}
            emit('telemetry_summary', run_id=run_id, samples=len(values), gpu_index=0,
                 throttle_reason_values=sorted(set(r['throttle_reasons'] for r in values)), metrics=fields)
    output = ROOT / 'outputs/phase2_results.jsonl'
    output.write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in raw+derived))
    print(json.dumps(dict(raw_rows=len(raw), derived_rows=len(derived), groups=len(groups), output=str(output))))
    return raw, derived


if __name__=='__main__':
    analyze()
