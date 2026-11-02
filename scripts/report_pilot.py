"""Generate the pilot report from validated results, including planning assumptions."""
import argparse
import json
from pathlib import Path
import statistics

import numpy as np

TIERS = ['recompute', 'cpu_pinned', 'cpu_pageable', 'file', 'gpu_hit']
LENGTHS = [512, 2048, 8192]
TURNS = [32, 256]


def generate(results, report, figures):
    rows = [json.loads(line) for line in results.read_text().splitlines()]
    validation = next(r for r in rows if r['kind'] == 'analysis_validation')
    protocol = next((r for r in rows if r['kind'] == 'protocol'), None)
    env = protocol['environment'] if protocol else rows[0]['environment']
    summaries = {(r['measurement_kind'], r['prefix_tokens'], r.get('turn_tokens'), r['condition']): r
                 for r in rows if r['kind'] == 'summary'}
    allocations = [r for r in rows if r['kind'] == 'allocation_end']
    prod = [r for r in rows if r['kind'] == 'production_status']
    successful = validation['complete'] and any(r['kind'] == 'reference_complete' for r in rows)
    lines = ['# Pilot report: Reload or Recompute', '',
             ('Reference measurements complete. Scientific interpretation and production logs still require review.'
              if successful else 'Pilot incomplete. No crossover or speedup conclusion is accepted.'), '',
             'This report is generated from `outputs/results.jsonl`. Configuration values describe the requested experiment; '
             'all observed values below come from its records. The full grid has not been started.', '',
             '## Environment', '',
             f"- Requested GPU: `{env['requested_gpu']}`. Observed: " +
             ', '.join(f"`{g['name']}`" for g in env['gpus']) + '.',
             f"- Allocated devices: {env['gpu_count']}. Reference inference uses one device.",
             f"- Torch: `{env['torch']}`. CUDA runtime: `{env['cuda_runtime']}`. "
             f"Transformers: `{env['transformers']}`. vLLM in the reference environment: `{env['vllm']}`.",
             f"- GPU and driver query: `{env['gpu_query']['output'].strip()}`.",
             f"- CPU cores: {env['cpu_count']}. Load average at process startup: `{env['load_average']}`.",
             '- CPU memory and initial free disk bytes are preserved verbatim in each source environment record.', '',
             '## Raw timing summaries', '',
             'Wall-clock TTFT ends when a greedy first token is available on the CPU. Tokenization, cache creation, '
             'offload writes, queueing, and transport are excluded. Cache acquisition and the new turn are included. '
             'CUDA events and synchronization accompany wall timing. See PROTOCOL.md.', '']
    for turn in TURNS:
        lines.extend([f'### New turn: {turn} tokens', '',
                      '| Prefix tokens | Condition | Median TTFT, ms | Bootstrap 95% CI, ms | Range, ms | Repeats |',
                      '| --- | --- | --- | --- | --- | --- |'])
        for length in LENGTHS:
            for tier in TIERS:
                r = summaries.get(('ttft', length, turn, tier))
                if r:
                    lines.append(f"| {length} | {tier} | {r['median']:.3f} | "
                                 f"[{r['ci95'][0]:.3f}, {r['ci95'][1]:.3f}] | "
                                 f"{r['minimum']:.3f}–{r['maximum']:.3f} | {r['n']} |")
                else:
                    lines.append(f'| {length} | {tier} | Missing | Missing | Missing | Missing |')
        lines.append('')
    lines.extend(['The interval is a percentile bootstrap of the median over measured rounds. '
                  'It measures within-session repeat variability, not across-session uncertainty.', '',
                  '## Prefix prefill and bandwidth', '',
                  '| Prefix tokens | Prefix-only median, ms | Prefill tokens/s from median latency |',
                  '| --- | --- | --- |'])
    for length in LENGTHS:
        r = summaries.get(('prefill', length, None, 'prefix_only'))
        if r:
            lines.append(f"| {length} | {r['median']:.3f} | {length * 1000 / r['median']:.1f} |")
    lines.extend(['', '| Prefix tokens | Transfer | Median effective GB/s | Bootstrap 95% CI, GB/s |',
                  '| --- | --- | --- | --- |'])
    for r in rows:
        if r['kind'] == 'bandwidth_summary':
            lines.append(f"| {r['prefix_tokens']} | {r['condition']} | {r['median']/1e9:.3f} | "
                         f"[{r['ci95'][0]/1e9:.3f}, {r['ci95'][1]/1e9:.3f}] |")
    configs = [r for r in rows if r['kind'] == 'model_config']
    if configs:
        r = configs[0]
        lines.extend(['', f"KV bytes per token from configuration: {r['kv_bytes_per_token_config']}. "
                      'The script requires exact agreement with the observed tensor byte count.',
                      f"Model revision: `{r.get('model_revision')}`."])
    controls = [r for r in rows if r['kind'] == 'disk_cache_control']
    if controls:
        lines.extend(['', 'Page-cache control: `' + controls[-1]['global_drop_caches'] + '`. '
                      'Per-file DONTNEED is advisory. File timings include deserialization and pageable H2D.'])
    disk = [r for r in rows if r['kind'] in ['bandwidth', 'ttft'] and
            r.get('condition') in ['file_read', 'file']]
    if disk:
        ratios = [r['physical_read_bytes'] / r['bytes'] for r in disk
                  if 'bytes' in r and r.get('physical_read_bytes') is not None]
        if ratios:
            lines.extend(['', f'Raw file microbenchmark physical-read/file-byte ratio: '
                          f'median {statistics.median(ratios):.3f}, '
                          f'range [{min(ratios):.3f}, {max(ratios):.3f}]. '
                          'These counters are process I/O accounting, not a trace of the underlying storage device.'])
    lines.extend(['', '## Crossovers and predictive rule', '',
                  '`T_reload(L) = overhead + L × kv_bytes_per_token / effective_bandwidth`. '
                  'The bandwidth and overhead fit uses microbenchmark medians independently of TTFT. '
                  'The file prediction adds file-read and pageable-copy legs. '
                  'The resumed-TTFT prediction adds the GPU-hit new-turn baseline. '
                  'File deserialization remains an omitted cost and is part of the residual.', ''])
    for r in rows:
        if r['kind'] == 'rule_calibration':
            bw = r['effective_bytes_per_s']
            lines.append(f"- {r['condition']}: overhead {r['overhead_ms']:.3f} ms; "
                         + (f'bandwidth {bw/1e9:.3f} GB/s' if bw else 'bandwidth unresolved')
                         + f"; nonnegative constraint active: {r['constrained']}.")
    lines.extend(['', '| New-turn tokens | Tier | Observed ordering or crossing | Predicted ordering or crossing |',
                  '| --- | --- | --- | --- |'])
    for r in rows:
        if r['kind'] == 'crossover':
            def label(value):
                if value['status'] == 'bracketed':
                    return str(value['intervals'])
                return value['status'].replace('_', ' ')
            lines.append(f"| {r['turn_tokens']} | {r['condition']} | {label(r['observed'])} | {label(r['predicted'])} |")
    lines.extend(['', '| Prefix | Turn | Tier | Predicted TTFT, ms | Measured TTFT, ms | Signed error | Correct median ordering |',
                  '| --- | --- | --- | --- | --- | --- | --- |'])
    for r in rows:
        if r['kind'] == 'rule_prediction':
            lines.append(f"| {r['prefix_tokens']} | {r['turn_tokens']} | {r['condition']} | "
                         f"{r['predicted_ttft_ms']:.3f} | {r['measured_ttft_ms']:.3f} | "
                         f"{r['signed_relative_error']:.1%} | {r['decision_correct']} |")
    lines.extend(['', 'A crossing is reported only between sampled lengths with opposite median ordering. '
                  'Reload winning at every sampled length gives no exact crossover. '
                  'Inspect the paired-difference intervals in the JSONL before treating a close median ordering as decisive. '
                  'The GPU-hit baseline is measured at each shape, so this is a transfer-cost test, '
                  'not a fully independent predictor of an unseen hardware configuration.', '',
                  '## Production path', ''])
    if prod:
        r = prod[-1]
        lines.extend([f"Status: `{r['status']}`. Exit code: `{r.get('returncode', 'not recorded')}`.", '',
                      f"Allocated-device time for this attempt: {r.get('allocated_gpu_hours', 0):.6f} GPU-hours.", '',
                      'Exact install and runtime logs are retained under `outputs/raw`. '
                      'The reviewed error and implications belong in NOTES.md. '
                      'A compatibility failure is evidence about this package and runtime combination, '
                      'not proof that every LMCache release fails on T4.'])
    else:
        lines.append('No completed production attempt is recorded.')
    lines.extend(['', '## GPU budget and full-grid projection', ''])
    for r in allocations:
        lines.append(f"Kernel process lifetime: {r['duration_s']:.3f} seconds. "
                     f"Conservative allocated-device charge: {r['allocated_gpu_hours']:.6f} GPU-hours. "
                     'Kaggle provisioning and finalization may add time; reconcile against the quota ledger.')
    if successful:
        full_lengths = np.array([256, 512, 1024, 2048, 4096, 8192, 16384])
        total_ms = 0.0
        for turn in TURNS:
            for tier in TIERS:
                y = [summaries[('ttft', length, turn, tier)]['median'] for length in LENGTHS]
                # Interpolate inside the pilot; proportional extrapolation outside.
                projected = np.interp(full_lengths, LENGTHS, y)
                projected[full_lengths < min(LENGTHS)] = y[0] * full_lengths[full_lengths < min(LENGTHS)] / min(LENGTHS)
                projected[full_lengths > max(LENGTHS)] = y[-1] * full_lengths[full_lengths > max(LENGTHS)] / max(LENGTHS)
                total_ms += float(projected.sum()) * (protocol['repeats'] + protocol['warmups'])
        proxy = total_ms / 1000 / 3600 * env['gpu_count']
        planning = dict(schema_version=1, run_id=rows[0]['run_id'], kind='planning_projection',
                        environment=env, model=protocol['model'],
                        requested_full_prefix_lengths=full_lengths.tolist(),
                        one_pilot_model_full_length_grid_gpu_hours=proxy,
                        five_identical_cost_models_gpu_hours=proxy * 5,
                        allocated_gpu_count=env['gpu_count'],
                        assumption='linear interpolation and proportional endpoint extrapolation; '
                        'pilot model timing for all models; warmups included; setup, profiling, '
                        'cache preparation, microbenchmarks, larger-model scaling and memory failures excluded')
        if not any(r['kind'] == 'planning_projection' for r in rows):
            with results.open('a') as f:
                f.write(json.dumps(planning) + '\n')
        lines.extend([f'Timing-only proxy for one pilot-model sweep over the full requested length grid: '
                      f'{proxy:.6f} allocated GPU-hours. Repeating that cost for every requested model gives '
                      f'{proxy*5:.6f} allocated GPU-hours.', '',
                      'This is a conditional service-time proxy, not a credible total cost forecast. '
                      'It uses linear interpolation and proportional extrapolation outside the pilot lengths, '
                      'assumes every model costs the same as the pilot model, and includes warmups. '
                      'It excludes setup, model downloads, profiling, cache preparation, bandwidth runs, '
                      'memory failures, and differences in model architecture and quantization. '
                      'P100 runtime and additional hardware cannot be forecast from this pilot. '
                      'Use the observed kernel allocation as the setup baseline and calibrate each new model '
                      'before authorizing a large sweep. The present data do not certify that the entire grid fits the remaining quota.'])
    else:
        lines.append('A full-grid cost cannot be projected from an incomplete reference pilot.')
    lines.extend(['', '## Limitations and review', '',
                  '- The pilot measures within-session latency for a controlled repeated-text conversation.',
                  '- It cannot test cross-GPU transfer or a GQA-versus-MHA causal hypothesis.',
                  '- File-cache hints and process read counters do not identify the physical storage medium.',
                  '- The profile is collected separately from reported timings. Inspect it before assigning a limiter.',
                  '- The production smoke is not a production throughput benchmark or a verified external-hit comparison.',
                  '- No full-grid work is authorized by this report.'])
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text('\n'.join(lines) + '\n')
    if successful and figures:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        figures.mkdir(parents=True, exist_ok=True)
        fig, axes = plt.subplots(1, len(TURNS), figsize=(11, 4), constrained_layout=True)
        for ax, turn in zip(axes, TURNS):
            for tier in TIERS:
                values = [summaries[('ttft', length, turn, tier)] for length in LENGTHS]
                medians = np.array([r['median'] for r in values])
                errors = np.array([[r['median'] - r['ci95'][0] for r in values],
                                   [r['ci95'][1] - r['median'] for r in values]])
                ax.errorbar(LENGTHS, medians, yerr=errors, marker='o', label=tier, capsize=3)
            ax.set(xscale='log', yscale='log', xlabel='Prefix tokens', ylabel='TTFT (ms)',
                   title=f"{env['gpus'][0]['name']}, new turn {turn} tokens")
            ax.grid(alpha=0.2)
        axes[-1].legend(fontsize=8)
        fig.savefig(figures / 'pilot-ttft.png', dpi=180)
        fig.savefig(figures / 'pilot-ttft.pdf')
        plt.close(fig)
    print(f'Wrote {report}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, default=Path('outputs/results.jsonl'))
    parser.add_argument('--report', type=Path, default=Path('docs/PILOT_REPORT.md'))
    parser.add_argument('--figures', type=Path, default=Path('figures'))
    args = parser.parse_args()
    generate(args.results, args.report, args.figures)
