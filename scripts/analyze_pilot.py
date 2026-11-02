"""Validate fetched pilot data and derive reviewable summaries without rerunning GPUs."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

CONDITIONS = ['recompute', 'cpu_pinned', 'cpu_pageable', 'file', 'gpu_hit']
PREFIXES = [512, 2048, 8192]
TURNS = [32, 256]
SEED = 7321


def interval(values):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(SEED)
    medians = np.median(rng.choice(values, size=(10000, len(values))), axis=1)
    return dict(median=float(np.median(values)),
                ci95=[float(x) for x in np.quantile(medians, [0.025, 0.975])],
                minimum=float(values.min()), maximum=float(values.max()), n=len(values))


def nonnegative_fit(xs, ys):
    """Least-squares t = overhead + bytes * slope, with physical constraints."""
    xs, ys = np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)
    design = np.column_stack([np.ones(len(xs)), xs])
    raw, *_ = np.linalg.lstsq(design, ys, rcond=None)
    candidates = [np.array([ys.mean(), 0]),
                  np.array([0, np.dot(xs, ys) / np.dot(xs, xs)])]
    if (raw >= 0).all():
        candidates.append(raw)
    best = min(candidates, key=lambda a: np.sum((design @ a - ys) ** 2))
    return dict(overhead_ms=float(best[0]), ms_per_byte=float(best[1]),
                effective_bytes_per_s=float(1000 / best[1]) if best[1] else None,
                raw_overhead_ms=float(raw[0]), raw_ms_per_byte=float(raw[1]),
                constrained=bool((raw < 0).any()),
                calibration_lengths=PREFIXES,
                calibration='independent microbenchmark medians, no TTFT fit')


def crossing(lengths, differences):
    """Return sampled intervals and bounds; never manufacture an exact crossing."""
    brackets = [[a, b] for a, b, x, y in zip(lengths, lengths[1:], differences,
                                             differences[1:]) if x * y < 0]
    if brackets:
        return dict(status='bracketed', intervals=brackets)
    if all(x < 0 for x in differences):
        return dict(status='reload_faster_at_all_sampled_lengths',
                    bound='if a monotone crossing exists, it is below the shortest sample',
                    shortest_sample=min(lengths))
    if all(x > 0 for x in differences):
        return dict(status='recompute_faster_at_all_sampled_lengths',
                    bound='no observed crossover; none inferred outside sampled range')
    return dict(status='tie_or_nonmonotone', differences=differences)


def analyze(source, destination):
    data = []
    for i, line in enumerate(source.read_text().splitlines(), 1):
        try:
            data.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f'Invalid JSONL at {source}:{i}') from e
    run_ids = {r['run_id'] for r in data}
    if len(run_ids) != 1:
        raise ValueError('Analyze each experimental run separately; do not pool runs')
    samples = [r for r in data if r['kind'] in ['ttft', 'prefill', 'bandwidth']]
    if any(not r.get('valid', False) for r in samples):
        raise ValueError('Invalid timing samples are present; inspect correctness failure')
    keys = [(r['kind'], r.get('prefix_tokens'), r.get('turn_tokens'),
             r['condition'], r['repeat']) for r in samples]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate sample keys; do not silently count repeats twice')
    groups = defaultdict(list)
    for r in samples:
        groups[(r['kind'], r['prefix_tokens'], r.get('turn_tokens'), r['condition'])].append(r)
    missing = []
    for length in PREFIXES:
        for turn in TURNS:
            for condition in CONDITIONS:
                g = groups[('ttft', length, turn, condition)]
                if len(g) < 10:
                    missing.append([length, turn, condition, len(g)])
        for kind, condition in [('prefill', 'prefix_only'), ('bandwidth', 'h2d_pinned'),
                                ('bandwidth', 'h2d_pageable'), ('bandwidth', 'file_read')]:
            if len(groups[(kind, length, None, condition)]) < 10:
                missing.append([kind, length, condition])
    reference_envs = [r['environment'] for r in data if r['kind'] == 'protocol']
    env = reference_envs[0] if reference_envs else data[0]['environment']
    derived = []

    def append(kind, **fields):
        derived.append(dict(schema_version=1, run_id=next(iter(run_ids)), kind=kind,
                            environment=env, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                            **fields))

    append('analysis_validation', complete=not missing, missing=missing,
           measured_sample_count=len(samples), invalid_sample_count=0,
           analysis_numpy_version=np.__version__, analysis_python=sys.version,
           bootstrap_resamples=10000, bootstrap_seed=SEED,
           bootstrap_method='percentile bootstrap of median, resample repeats')
    summaries = {}
    for key, group in groups.items():
        if not group:
            continue
        summary = interval([r['wall_ms'] for r in group])
        summaries[key] = summary
        append('summary', measurement_kind=key[0], prefix_tokens=key[1],
               turn_tokens=key[2], condition=key[3], unit='ms', **summary)
        if key[0] == 'bandwidth':
            bandwidth = interval([r['bytes_per_s'] for r in group])
            append('bandwidth_summary', prefix_tokens=key[1], condition=key[3],
                   unit='bytes/s', **bandwidth,
                   physical_read_bytes=[r.get('physical_read_bytes') for r in group])
    if not missing:
        fits = {}
        for name in ['h2d_pinned', 'h2d_pageable', 'file_read']:
            gs = [groups[('bandwidth', length, None, name)] for length in PREFIXES]
            fit = nonnegative_fit([g[0]['bytes'] for g in gs],
                                  [np.median([r['wall_ms'] for r in g]) for g in gs])
            fits[name] = fit
            append('rule_calibration', condition=name, **fit)
        layout = {r['prefix_tokens']: r for r in data if r['kind'] == 'cache_layout'}
        for turn in TURNS:
            for tier, copy_name in [('cpu_pinned', 'h2d_pinned'),
                                     ('cpu_pageable', 'h2d_pageable'), ('file', 'h2d_pageable')]:
                measured_deltas, predicted_deltas = [], []
                for length in PREFIXES:
                    gpu = summaries[('ttft', length, turn, 'gpu_hit')]['median']
                    recompute = summaries[('ttft', length, turn, 'recompute')]['median']
                    observed = summaries[('ttft', length, turn, tier)]['median']
                    fit = fits[copy_name]
                    load = fit['overhead_ms'] + fit['ms_per_byte'] * layout[length]['kv_bytes']
                    if tier == 'file':
                        disk = fits['file_read']
                        load += disk['overhead_ms'] + disk['ms_per_byte'] * layout[length]['file_bytes']
                    predicted = gpu + load
                    left = {r['repeat']: r['wall_ms'] for r in groups[('ttft', length, turn, tier)]}
                    right = {r['repeat']: r['wall_ms'] for r in groups[('ttft', length, turn, 'recompute')]}
                    if set(left) != set(right):
                        raise ValueError('Paired repeat sets differ')
                    delta_ci = interval([left[k] - right[k] for k in sorted(left)])
                    measured_deltas.append(observed - recompute)
                    predicted_deltas.append(predicted - recompute)
                    prefix_time = summaries[('prefill', length, None, 'prefix_only')]['median']
                    append('rule_prediction', prefix_tokens=length, turn_tokens=turn,
                           condition=tier, predicted_reload_ms=load,
                           measured_prefix_prefill_ms=prefix_time,
                           prefix_rule_predicts_reload=load < prefix_time,
                           predicted_ttft_ms=predicted, measured_ttft_ms=observed,
                           recompute_ttft_ms=recompute, gpu_hit_ttft_ms=gpu,
                           signed_relative_error=(predicted - observed) / observed,
                           measured_reload_increment_ms=observed - gpu,
                           residual_ms=observed - predicted,
                           decision_correct=(predicted < recompute) == (observed < recompute),
                           paired_delta_ms=delta_ci,
                           limitation='GPU-hit tail baseline measured at this shape; file deserialization omitted')
                append('crossover', turn_tokens=turn, condition=tier,
                       observed=crossing(PREFIXES, measured_deltas),
                       predicted=crossing(PREFIXES, predicted_deltas))
    model_record = next((r for r in data if r['kind'] == 'model_config'), None)
    for r in data + derived:
        r.setdefault('model', 'Qwen/Qwen2.5-1.5B')
        r.setdefault('concurrency', 1)
        r.setdefault('dtype', 'float16')
        if model_record:
            r.setdefault('model_revision', model_record.get('model_revision'))
            r.setdefault('kv_bytes_per_token_config', model_record['kv_bytes_per_token_config'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(''.join(json.dumps(r, allow_nan=False) + '\n' for r in data + derived))
    print(json.dumps(dict(complete=not missing, missing=missing,
                         measurements=len(samples), derived_rows=len(derived),
                         output=str(destination)), indent=2))
    return not missing


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=Path('outputs/results.jsonl'))
    args = parser.parse_args()
    analyze(args.source, args.output)
