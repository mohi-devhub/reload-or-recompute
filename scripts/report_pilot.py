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
    review = next((r for r in rows if r['kind'] == 'analysis_review'), None)
    ledger = next((r for r in rows if r['kind'] == 'budget_ledger'), None)
    verdict = next((r for r in rows if r['kind'] == 'pilot_verdict'), None)
    successful = validation['complete'] and any(r['kind'] == 'reference_complete' for r in rows)
    lines = ['# Pilot report: Reload or Recompute', '',
             ('Reference pilot passes with limitations. Reload wins throughout the sampled grid; '
              'the crossover is not identified. The production installation failed on the Python version. '
              'The full grid awaits approval.' if verdict else
              'Reference measurements complete. Scientific interpretation and production logs still require review.'
              if successful else 'Pilot incomplete. No crossover or speedup conclusion is accepted.'), '',
             'This report is generated from `outputs/results.jsonl`. Configuration values describe the requested experiment; '
             'all observed values below come from its records. The full grid has not been started.', '',
             '## Environment', '',
             f"- Requested GPU: `{env['requested_gpu']}`. Observed: " +
             ', '.join(f"`{g['name']}`" for g in env['gpus']) + '.',
             f"- Allocated devices: {env['gpu_count']}. Reference inference uses one device.",
             f"- Torch: `{env['torch']}`. CUDA runtime: `{env['cuda_runtime']}`. "
             f"Transformers: `{env['transformers']}`. vLLM in the reference environment: `{env['vllm']}`.",
             '- GPU and driver query: ' + '; '.join(env['gpu_query']['output'].strip().splitlines()) + '.',
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
    memory_total = next(line.split()[1] for line in env['cpu_ram'].splitlines()
                        if line.startswith('MemTotal:'))
    lines.extend(['', f"CPU RAM: {int(memory_total) * 1024 / 2**30:.3f} GiB. "
                  'Initial free disk, bytes: ' + ', '.join(f'`{k}` = {v}' for k, v in env['free_disk_bytes'].items()) + '.'])
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
                      'The first setup failed in ensurepip. The supplemental install reached pip and rejected '
                      '`vllm==0.9.0`: `Requires-Python >=3.9,<3.13`; Kaggle provided Python 3.13. '
                      'LMCache native kernels, CPU reuse, and disk reuse were not reached. '
                      'No sm_75 compatibility claim or production performance result is made. '
                      'Both setup failures and the package choice are recorded in NOTES.md.'])
    else:
        lines.append('No completed production attempt is recorded.')
    lines.extend(['', '## GPU budget and full-grid projection', ''])
    for r in allocations:
        lines.append(f"Kernel process lifetime: {r['duration_s']:.3f} seconds. "
                     f"Conservative allocated-device charge: {r['allocated_gpu_hours']:.6f} GPU-hours. "
                     'Kaggle provisioning and finalization may add time; reconcile against the quota ledger.')
    if ledger:
        lines.extend(['', f"Total conservative process device-hours: {ledger['conservative_allocated_gpu_hours']:.6f}. "
                      f"Production troubleshooting: {ledger['production_troubleshooting_gpu_hours']:.6f} GPU-hours. "
                      'See BUDGET.md for both kernel rows and the rounded Kaggle quota snapshot.'])
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
    if review:
        lines.extend(['', '## Findings and surprises', '',
                      f"All {review['ordering_comparisons']} reload-versus-recompute median orderings agree with the simple rule. "
                      'This is an easy classification regime: every tested prefix favours reload. '
                      'A numerical crossover prediction error cannot be computed without a measured crossing.', '',
                      '| Tier | Median absolute TTFT prediction error | Maximum absolute TTFT prediction error |',
                      '| --- | --- | --- |'])
        for tier, value in review['errors_by_tier'].items():
            lines.append(f"| {tier} | {value['median_absolute_relative_error']:.1%} | "
                         f"{value['max_absolute_relative_error']:.1%} |")
        lines.extend(['', f"Every generated first token matches recomputation. Maximum relative logit L2 error is "
                      f"{review['max_logits_relative_l2']:.6f}. Peak allocated VRAM is "
                      f"{review['maximum_peak_vram_bytes']} bytes. The closest reload-minus-recompute paired "
                      f"confidence-interval upper endpoint is {review['closest_reload_minus_recompute_ci95_upper_ms']:.3f} ms, "
                      'so the reload advantage is resolved within this session.', '',
                      'Pinned reload and a GPU-resident hit overlap in latency at the shorter contexts. '
                      'Do not interpret the occasional lower pinned median as faster than the resident-cache bound. '
                      'Host dispatch, asynchronous copies, and within-session variation make independently measured '
                      'copy cost imperfectly additive with the GPU-hit baseline.', '',
                      'Prefix-only prefill at the longest length is slower than recomputing the prefix plus the short turn. '
                      'These are different matrix shapes and were measured at different times. '
                      'Kernel selection and session drift are possible explanations; this pilot does not isolate the cause. '
                      'The rule therefore uses actual measured prefill and reports its residuals without forcing monotonicity.', '',
                      'The file-read fit needs a nonnegative constraint on its overhead, and the longest file-TTFT '
                      'prediction overestimates observed latency. The raw read microbenchmark, torch.load read pattern, '
                      'CPU allocation, and host dispatch differ. A single effective-bandwidth term does not explain '
                      'all file latency in this pilot.', '',
                      'The separate profile shows recompute dominated by GPU kernel execution, chiefly GEMMs. '
                      'Reload profiles show substantial host dispatch and execution gaps beyond the copy itself. '
                      'This establishes which operations dominate the instrumented path; it does not prove hardware '
                      'FLOP or PCIe saturation. The profile file read was not evicted and is excluded from storage timing claims.'])
    lines.extend(['', '## Provisional rule of thumb', '',
                  'Reload when measured prefix prefill exceeds `fixed_overhead + L × kv_bytes_per_token / effective_bandwidth`, '
                  'adding the disk-read leg for files. Recompute when that cost is larger; include the new-turn baseline '
                  'for TTFT and recalibrate for each model, GPU, and storage path.', '',
                  'This pilot favours reload at every sampled length, so it cannot locate the threshold or validate '
                  'the rule on a different model or GPU.', '', '## Limitations and review', '',
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
        from matplotlib.ticker import NullLocator, ScalarFormatter
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
            ax.set_xticks(LENGTHS)
            ax.xaxis.set_major_formatter(ScalarFormatter())
            ax.xaxis.set_minor_locator(NullLocator())
            ax.grid(alpha=0.2)
        axes[-1].legend(fontsize=8)
        fig.savefig(figures / 'pilot-ttft.png', dpi=180)
        fig.savefig(figures / 'pilot-ttft.pdf', metadata={'CreationDate': None, 'ModDate': None})
        plt.close(fig)
    print(f'Wrote {report}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, default=Path('outputs/results.jsonl'))
    parser.add_argument('--report', type=Path, default=Path('docs/PILOT_REPORT.md'))
    parser.add_argument('--figures', type=Path, default=Path('figures'))
    args = parser.parse_args()
    generate(args.results, args.report, args.figures)
