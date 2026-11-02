"""Rebuild accepted results, diagnostics, the pilot report, and the budget ledger."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

from analyze_pilot import analyze
from report_pilot import generate

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'outputs/raw'
RESULTS = ROOT / 'outputs/results.jsonl'
REFERENCE = RAW / 'pilot-v1/pilot-output/results.jsonl'
PRODUCTION = RAW / 'production-v1/pilot-output/results.jsonl'


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    global RESULTS
    existing=read(RESULTS) if RESULTS.exists() else []
    saved_thresholds=[r for r in existing if r['kind']=='pilot_bstar']
    if (ROOT/'outputs/phase2_ledger.json').exists():
        RESULTS=ROOT/'outputs/pilot_results.jsonl'
    if not analyze(REFERENCE, RESULTS):
        raise RuntimeError('The reference grid is incomplete')
    rows = read(RESULTS)
    supplement = read(PRODUCTION)
    allowed = {'environment', 'subprocess', 'production_status', 'allocation_end',
               'production_smoke', 'fatal_error'}
    if any(r['kind'] not in allowed for r in supplement):
        raise ValueError('Do not pool timing samples from a supplemental GPU run')
    for r in supplement:
        r['source_file_sha256'] = hashlib.sha256(PRODUCTION.read_bytes()).hexdigest()
    rows.extend(supplement)
    env = next(r['environment'] for r in rows if r['kind'] == 'protocol')

    def append(kind, **fields):
        rows.append(dict(schema_version=1, run_id='pilot-review', kind=kind,
                         environment=env, **fields))

    metadata = json.loads((RAW / 'pilot-v1/source/kernel-metadata.json').read_text())
    append('submission_metadata', metadata=metadata,
           source_sha256=env['source_sha256'], kaggle_cli='2.2.4',
           reference_kernel_version=1, supplemental_kernel_version=1,
           reference_timeout_s=4800, supplemental_timeout_s=1500)

    timings = [r for r in rows if r['kind'] == 'ttft']
    predictions = [r for r in rows if r['kind'] == 'rule_prediction']
    append('analysis_review', all_first_tokens_equal=all(r['first_token_equal'] for r in timings),
           max_logits_relative_l2=max(r['logits_relative_l2'] for r in timings),
           maximum_peak_vram_bytes=max(r['peak_vram_bytes'] for r in timings),
           closest_reload_minus_recompute_ci95_upper_ms=max(r['paired_delta_ms']['ci95'][1]
                                                          for r in predictions),
           ordering_agreements=sum(r['decision_correct'] for r in predictions),
           ordering_comparisons=len(predictions),
           errors_by_tier={tier: dict(median_absolute_relative_error=statistics.median(
               abs(r['signed_relative_error']) for r in predictions if r['condition'] == tier),
               max_absolute_relative_error=max(abs(r['signed_relative_error']) for r in predictions
                                                if r['condition'] == tier))
               for tier in ['cpu_pinned', 'cpu_pageable', 'file']})
    trace_path = RAW / 'pilot-v1/pilot-output/reference-trace.json'
    events = json.loads(trace_path.read_text())['traceEvents']
    for scope in [e for e in events if e.get('cat') == 'user_annotation' and e.get('ph') == 'X']:
        inside = [e for e in events if e.get('ph') == 'X' and e.get('ts', -1) >= scope['ts']
                  and e.get('ts', 0) + e.get('dur', 0) <= scope['ts'] + scope['dur']]
        kernels = [e for e in inside if e.get('cat') == 'kernel']
        copies = [e for e in inside if e.get('cat') == 'gpu_memcpy' and 'HtoD' in e['name']]
        groups = Counter()
        for e in kernels:
            group = ('gemm' if any(s in e['name'] for s in ['gemm', 'gemvx']) else
                     'attention' if 'fmha' in e['name'] else 'other')
            groups[group] += e['dur'] / 1000
        append('profile_summary', condition=scope['name'], prefix_tokens=2048, turn_tokens=32,
               profiler_wall_ms=scope['dur'] / 1000,
               profiler_kernel_ms=sum(e['dur'] for e in kernels) / 1000,
               profiler_h2d_ms=sum(e['dur'] for e in copies) / 1000,
               profiler_h2d_bytes=sum(e['args'].get('bytes', 0) for e in copies),
               kernel_groups_ms=dict(groups),
               source_trace_sha256=hashlib.sha256(trace_path.read_bytes()).hexdigest(),
               excluded_from_timing_summaries=True,
               limitation='one instrumented round; file profile does not evict pages')
    allocations = [r for r in rows if r['kind'] == 'allocation_end']
    total = sum(r['allocated_gpu_hours'] for r in allocations)
    startup = next(r for r in rows if r['kind'] == 'subprocess' and r['name'] == 'production-venv')
    prod = [r for r in supplement if r['kind'] == 'production_status'][-1]
    troubleshoot = startup['allocated_gpu_hours'] + prod['allocated_gpu_hours']
    quota = {}
    for name in ['quota-before', 'quota-after-v1', 'quota-after-production']:
        text = (RAW / 'control' / (name + '.json')).read_text()
        values = json.loads(text[text.index('['):])
        quota[name] = next(r for r in values if r['resource'] == 'GPU')
    append('budget_ledger', conservative_allocated_gpu_hours=total,
           production_troubleshooting_gpu_hours=troubleshoot,
           quota_snapshots=quota,
           pilot_limit_gpu_hours=3, weekly_limit_gpu_hours=30,
           production_limit_gpu_hours=0.75,
           remaining_pilot_device_hours=3 - total,
           remaining_week_device_hours=30 - total,
           caution='process device-hours exclude provisioning/finalization; quota rounded to hundredths '
                   'and appears to count session hours; no other sessions submitted by this study')
    append('pilot_verdict', reference_feasibility='pass',
           production='unavailable_in_attempted_environment',
           gpu_kernel_compatibility='not_reached', crossover_validation='not_identifiable_on_sampled_grid',
           full_grid_authorized=False,
           statement='Reference pilot passes with limitations; proceed only after user approval of full grid.')
    rows.extend(saved_thresholds)
    RESULTS.write_text(''.join(json.dumps(r, allow_nan=False) + '\n' for r in rows))
    generate(RESULTS, ROOT / 'docs/PILOT_REPORT.md', ROOT / 'figures')
    lines = ['# GPU budget', '',
             'The user authorizes a weekly ceiling of 30 GPU-hours, a pilot ceiling of 3 GPU-hours, '
             'and at most 45 GPU-minutes for production troubleshooting. These are limits, not measurements.', '',
             '| Kernel and version | Outcome | Requested and observed hardware | Process seconds | Conservative device-hours |',
             '| --- | --- | --- | --- | --- |']
    for r in allocations:
        name = ('mohiachu/reload-or-recompute-pilot, v1' if r['run_id'] == 'pilot-t4-v1'
                else 'mohiachu/reload-or-recompute-production-pilot, v1')
        outcome = ('Reference complete; production venv bootstrap failed' if r.get('reference_success')
                   else 'Production package install rejected Python version')
        lines.append(f"| {name} | {outcome} | NvidiaTeslaT4; {r['gpu_count']} Tesla T4 devices | "
                     f"{r['duration_s']:.6f} | {r['allocated_gpu_hours']:.6f} |")
    lines.extend(['', f'Conservative pilot total: **{total:.6f} GPU-hours**. '
                  'Every visible GPU is charged, including the idle second device. '
                  'Installation, downloads, and idle time within the process lifetime are included.', '',
                  f'Production troubleshooting, including the first bootstrap failure: **{troubleshoot:.6f} GPU-hours**. '
                  'No additional production attempts are planned.', '',
                  f"Kaggle's final rounded quota snapshot reports {quota['quota-after-production']['used']} used "
                  f"and {quota['quota-after-production']['remaining']} remaining. "
                  'It appears to count session hours, unlike our two-device charge. '
                  'Provisioning and finalization are outside the process timestamps. '
                  'Both sources are retained in the canonical budget_ledger record.', '',
                  f'Remaining pilot allowance under the conservative process accounting: {3-total:.6f} GPU-hours. '
                  f'Remaining weekly allowance on that basis: {30-total:.6f} GPU-hours.', '',
                  'Source: allocation_end, subprocess, production_status, and budget_ledger records '
                  'in `outputs/results.jsonl`. Quota snapshots and run logs are retained in `outputs/raw`.', '',
                  'The full grid has not started and requires explicit user approval.'])
    budget_path=ROOT/'docs/BUDGET.md'
    if '\n## Phase two' not in budget_path.read_text():
        budget_path.write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
