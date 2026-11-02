"""Write the phase-two report and figures from fetched, session-separated observations."""
from collections import defaultdict
import json
from pathlib import Path
import statistics

import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def label(measured):
    if measured['status']=='bracketed':
        return '; '.join('['+str(b['target_mb_s'][0])+', '+
                         (str(b['target_mb_s'][1]) if b['target_mb_s'][1] else 'unthrottled')+']'
                         +f" target / [{b['achieved_mb_s'][0]:.1f}, {b['achieved_mb_s'][1]:.1f}] achieved"
                         +('' if b['paired_ci_resolved'] else ' (median only)')
                         for b in measured['brackets'])+('; nonmonotone' if measured.get('nonmonotone') else '')
    if measured['status']=='reload_faster_at_all_tested_simulated_rates':
        return '<= '+str(measured['upper_bound_target_mb_s'])+' (bound only)'
    if measured['status']=='recompute_faster_at_all_tested_simulated_rates':
        return 'above tested achieved rates (bound only)'
    return measured['status']


def number(value):
    return f'{value:.1f}' if value is not None else 'No positive denominator'


def report():
    path=ROOT/'outputs/phase2_results.jsonl'
    rows=[json.loads(x) for x in path.read_text().splitlines()]
    ledger=json.loads((ROOT/'outputs/phase2_ledger.json').read_text())
    plan_path=ROOT/'configs/phase2_queue.json'
    planned=json.loads(plan_path.read_text()) if plan_path.exists() else []
    recorded={r['name'] for r in ledger['runs']}
    unscheduled=[r['name'] for r in planned if r['name'] not in recorded]
    complete=not unscheduled and all(r['status']=='fetched' for r in ledger['runs'])
    totals=sum(r.get('actual_gpu_hours',r['reserved_gpu_hours']) for r in ledger['runs'])
    summaries=[r for r in rows if r['kind']=='phase2_summary' and r['purpose']=='sweep' and r['publication_repeat_count_met']]
    crossings=[r for r in rows if r['kind']=='bandwidth_crossover']
    files=[r for r in rows if r['kind']=='file_rule_residual']
    configs={r['model']:r for r in rows if r['kind']=='model_config'}
    errors=[r for r in rows if r['kind']=='model_failed']
    sweeps={r['specification']['run_id']:r for r in ledger['runs'] if r['purpose']=='sweep'}
    full_measurements=[r for r in rows if r['kind']=='measurement' and r['run_id'] in sweeps]
    accepted=[r for r in full_measurements if r['repeat']>=0 and r['valid']]
    invalid=[r for r in full_measurements if not r['valid']]
    run_complete={r['run_id'] for r in rows if r['kind']=='run_complete'}
    incomplete=[k for k in sweeps if k not in run_complete]
    stats=dict(schema_version=2,kind='phase2_report_totals',phase='phase2',
               phase2_conservative_gpu_hours=totals,phase2_limit_gpu_hours=10,
               accepted_measurements=len(accepted),invalid_measurements=len(invalid),
               full_sessions=len(sweeps),incomplete_sweep_run_ids=incomplete,
               unscheduled_run_names=unscheduled,
               rule_counts={field:sum(r[field] for r in rows if r['kind']=='phase2_rule_classification')
                            for field in ['resolved_comparisons','prefix_rule_agreements','ttft_rule_agreements']},
               file_errors={fmt:dict(old_median_ape=statistics.median(abs(r['old_signed_relative_error'])
                                                                      for r in files if r['format']==fmt),
                                    new_median_ape=statistics.median(abs(r['new_signed_relative_error'])
                                                                      for r in files if r['format']==fmt))
                            for fmt in ['torch','raw'] if any(r['format']==fmt for r in files)})
    stats['model_file_errors']={}
    for model in sorted({r['model'] for r in files}):
        stats['model_file_errors'][model]={}
        for fmt in ['torch','raw']:
            values=[r for r in files if r['model']==model and r['format']==fmt]
            if not values:continue
            stats['model_file_errors'][model][fmt]=dict(cells=len(values),
                old_median_ape=statistics.median(abs(r['old_signed_relative_error']) for r in values),
                new_median_ape=statistics.median(abs(r['new_signed_relative_error']) for r in values))
    rows=[r for r in rows if r['kind']!='phase2_report_totals']+[stats]
    path.write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in rows))
    lines=['# Phase two: simulated bandwidth crossovers','',
           ('Redesigned run queue finished.' if complete else 'Partial report: experiments are still active.'),
           'All bandwidth-sweep rates and crossover intervals below are **simulated transport bandwidth**. '
           'They do not measure a physical storage device at those rates.','',
           f"Accepted full-sweep timing samples: {len(accepted)}. Invalid full-sweep samples: {len(invalid)}. "
           f"Conservative phase usage: {totals:.6f} GPU-hours against the authorized cap of 10. "
           f"Incomplete sweep sessions: {len(incomplete)}. Unsubmitted queued runs: {len(unscheduled)}.",'',
           '## What was measured','',
           'The reference path uses fp16, one inference request, synchronized wall-clock TTFT through first-token selection, '
           'and ten interleaved measured rounds after warmup. Prefix-only prefill is randomized in those rounds. '
           'Reload transfers a packed cache in chunks with cumulative rate deadlines. Target and achieved transport '
           'bandwidth, sleep time, and bytes are stored separately. All full measurements are retained in the JSONL. '
           'Calibration timings have fewer repeats and are excluded from publication summaries.','',
           'The primary main-model workload is frozen public UltraChat generated dialogue. Long contexts stitch distinct '
           'conversations and are marked accordingly. Three independent sessions use that same frozen input. '
           'A separate repeated-text main-model run with a 32-token new turn at the common short lengths and the anomaly length supplies the matched control used for the model-family comparison. '
           'The remaining models use that repeated-text control. This is not a human-conversation trace or a quality evaluation.','',
           '## Model coverage and KV size','',
           '| Model | Family | Verified KV bytes/token | Native total context | Completed sweep sessions |',
           '| --- | --- | --- | --- | --- |']
    for model,cfg in configs.items():
        completed=sum(r['model']==model and r.get('completed',False) and r['run_id'] in sweeps
                      for r in rows if r['kind']=='model_complete')
        lines.append(f"| {model} | {cfg['attention_family']} | {cfg['kv_bytes_per_token']} | "
                     f"{cfg['config'].get('max_position_embeddings')} | {completed} |")
    if any('meta-llama' in r['model'] for r in errors):
        lines.append('| meta-llama/Llama-3.2-3B | GQA, requested | Unverified: gated access failed | Unmeasured | Unmeasured |')
    lines.extend(['','KV configuration arithmetic must equal the sum of observed tensor bytes. Native context includes '
                  'the new turn, so the short-context MHA models do not silently run the long-context grid. '
                  'The extra near-limit prefix leaves room for the longest requested new turn. '
                  'Environment, revision, shapes, and actual source hashes accompany observations.','',
                  '## Measured runtime and provenance','',
                  '| Runtime field | Observed values in accepted measurements |',
                  '| --- | --- |'])
    for field in ['gpu_names','gpu_count','python','torch','cuda_runtime','transformers','vllm']:
        values=sorted({json.dumps(r['environment'][field]) for r in accepted})
        lines.append(f"| {field} | {'; '.join(values)} |")
    lines.extend(['','The runtime table uses the environment inside the timed worker after dependency installation. '
                  'The startup log also records the pre-install environment. Kaggle allocates two T4 devices per '
                  'session here; inference uses one, while the conservative ledger charges both.','',
                  '| Fetched run | Saved source matches executed source | Private kernel verified | Saved container image |',
                  '| --- | --- | --- | --- |'])
    for run in ledger['runs']:
        if run['status']!='fetched':continue
        saved=run.get('saved_kernel_metadata',{})
        lines.append(f"| {run['name']} | {run.get('saved_source_matches_execution','Unavailable')} | "
                     f"{saved.get('is_private','Unavailable')} | {saved.get('docker_image','Unavailable')} |")
    lines.extend(['',
                  '## Independent bandwidth microbenchmarks','',
                  'These are measured unthrottled bandwidths, rather than simulated-rate results. '
                  'File bandwidth includes buffer allocation in the read API leg. The table selects prefix 512; '
                  'the JSONL contains every measured length and separate read, deserialization, and H2D intervals.','',
                  '| Model/session | Workload | Path | Median MB/s | Bootstrap 95% CI, MB/s |',
                  '| --- | --- | --- | --- | --- |'])
    for r in rows:
        if r['kind']=='phase2_micro_summary' and r['purpose']=='sweep' and r['publication_repeat_count_met'] and r['prefix_tokens']==512:
            v=r['bandwidth_mb_s']
            lines.append(f"| {r['model']}/{r['run_id']} | {r['workload']} | {r['condition']} | "
                         f"{v['median']:.1f} | [{v['ci95'][0]:.1f}, {v['ci95'][1]:.1f}] |")
    lines.extend(['',
                  '## Crossover bandwidths by model and length','',
                  '`B*_prefix = KV bytes / prefix-prefill seconds`. The overhead-adjusted TTFT prediction is '
                  '`B*_TTFT = KV bytes / (full-recompute TTFT - GPU-hit new-turn TTFT - fixed overhead)`. '
                  'The fixed overhead is calibrated from independent unthrottled H2D microbenchmarks. '
                  'A nonpositive denominator predicts no beneficial finite reload bandwidth under this additive model.','',
                  'Intervals use adjacent tested nominal simulated rates whose median TTFT ordering changes. '
                  'The label "median only" means endpoint paired confidence intervals do not both resolve the sign. '
                  'Achieved-rate endpoints and harmonic interpolation estimates are retained separately in JSONL. '
                  'Interpolation is not an additional measured bandwidth point.',''])
    controls=[r for r in crossings if r['workload']=='repeated_control']
    for model in sorted(set(r['model'] for r in controls)):
        lines.extend(['### '+model,'',
                      '| Prefix | Predicted prefix B*, MB/s | Predicted TTFT B*, turn 32 | Observed simulated bracket, turn 32 | Predicted TTFT B*, turn 256 | Observed simulated bracket, turn 256 |',
                      '| --- | --- | --- | --- | --- | --- |'])
        by=defaultdict(dict)
        for r in controls:
            if r['model']==model:
                by[r['prefix_tokens']][r['turn_tokens']]=r
        for length,values in sorted(by.items()):
            a,b=values.get(32),values.get(256)
            first=a or b
            lines.append(f"| {length} | {first['predicted_prefix_bstar_mb_s']:.1f} | "
                         f"{number(a['predicted_ttft_bstar_mb_s']) if a else 'Missing'} | "
                         f"{label(a['measured']) if a else 'Missing'} | "
                         f"{number(b['predicted_ttft_bstar_mb_s']) if b else 'Not scheduled / unavailable'} | "
                         f"{label(b['measured']) if b else 'Not scheduled / unavailable'} |")
        lines.append('')
    lines.extend(['## Main model on varied multi-turn text','',
                  '| Prefix | Session | New-turn tokens | Predicted TTFT B*, MB/s | Observed simulated bandwidth bracket, MB/s |',
                  '| --- | --- | --- | --- | --- |'])
    for r in sorted([r for r in crossings if r['workload']=='ultrachat'],key=lambda r:(r['prefix_tokens'],r['turn_tokens'],r['run_id'])):
        lines.append(f"| {r['prefix_tokens']} | {r['run_id']} | {r['turn_tokens']} | "
                     f"{number(r['predicted_ttft_bstar_mb_s'])} | {label(r['measured'])} |")
    lines.extend(['','### Rule decisions at resolved simulated-rate cells','',
                  '| Model | Workload | Resolved rate cells | Prefix-only rule agrees | TTFT-adjusted rule agrees |',
                  '| --- | --- | --- | --- | --- |'])
    for r in rows:
        if r['kind']=='phase2_rule_classification':
            lines.append(f"| {r['model']} | {r['workload']} | {r['resolved_comparisons']} | "
                         f"{r['prefix_rule_agreements']} | {r['ttft_rule_agreements']} |")
    lines.append('These are descriptive counts over correlated model/length/session cells with resolved paired confidence intervals, not independent generalization trials.')
    comparison={r['model']:r for r in controls if r['prefix_tokens']==512 and r['turn_tokens']==32}
    lines.extend(['','### Matched-size repeated-text comparison at prefix 512, new turn 32','',
                  '| MHA model | GQA comparison | KV-byte ratio, MHA/GQA | MHA simulated crossover | GQA simulated crossover |',
                  '| --- | --- | --- | --- | --- |'])
    for mha,gqa in [('EleutherAI/pythia-1.4b','Qwen/Qwen2.5-1.5B'),
                    ('facebook/opt-1.3b','Qwen/Qwen2.5-1.5B'),
                    ('microsoft/phi-2','Qwen/Qwen2.5-3B')]:
        if mha in comparison and gqa in comparison:
            a,b=comparison[mha],comparison[gqa]
            lines.append(f"| {mha} | {gqa} | {a['kv_bytes_per_token']/b['kv_bytes_per_token']:.3f} | "
                         f"{label(a['measured'])} | {label(b['measured'])} |")
    lines.extend(['','## GQA versus MHA and short lengths','',
                  'Compare the matched repeated-text runs at the common native lengths. The table reports both measured '
                  'cache size and bandwidth crossovers. Differences across models combine attention architecture, '
                  'parameter count, prefill throughput, and kernels; this is an association, not an isolated GQA treatment. '
                  'The short-length rows expose fixed-overhead regimes where prefix-only and resumed-TTFT thresholds '
                  'can disagree. A censored threshold is not assigned an exact crossover value.','',
                  'These short-context cutoffs belong to this Transformers reference path, including cache construction '
                  'and continuation kernels. They are not established cutoffs for an unmeasured serving engine.','',
                  'The following short-context table gives the paired unthrottled-copy TTFT minus recompute TTFT. '
                  'A positive interval favors recompute; an interval containing zero is unresolved. '
                  'It includes tensor-view construction and cache reconstruction inside TTFT. '
                  'The microbenchmark overhead fit captures the transfer path, so it need not explain every '
                  'Python or shape-dependent cost at very short lengths.','',
                  '| Model | Workload/session | Prefix | New turn | Unthrottled copy minus recompute, ms (paired 95% CI) |',
                  '| --- | --- | --- | --- | --- |'])
    for r in sorted(crossings,key=lambda r:(r['model'],r['run_id'],r['turn_tokens'],r['prefix_tokens'])):
        if r['prefix_tokens'] not in [16,32,64,128]:continue
        point=next((p for p in r['points'] if p['condition']=='simulated_unthrottled'),None)
        if point:
            delta=point['paired_delta']
            lines.append(f"| {r['model']} | {r['workload']}/{r['run_id']} | {r['prefix_tokens']} | "
                         f"{r['turn_tokens']} | {delta['median']:.3f} [{delta['ci95'][0]:.3f}, {delta['ci95'][1]:.3f}] |")
    lines.extend(['',
                  '### Additivity diagnostic','',
                  'The next table subtracts the measured transfer leg and a same-round resident-hit TTFT from '
                  'the simulated 50 MB/s reload TTFT at prefix 64 with a 256-token new turn. A negative resolved '
                  'residual contradicts a constant resident-hit baseline for that condition; it does not mean '
                  'a negative copy cost. This post-transfer remainder also includes view construction and host '
                  'dispatch, so it is not isolated GPU kernel time.','',
                  '| Model/session | Workload | Post-transfer minus resident hit, ms (paired 95% CI) |',
                  '| --- | --- | --- |'])
    for r in rows:
        if r['kind']=='post_transfer_baseline_residual' and r['prefix_tokens']==64 and r['turn_tokens']==256 and r['condition']=='simulated_50_MBps':
            v=r['post_transfer_minus_gpu_hit_ms']
            lines.append(f"| {r['model']}/{r['run_id']} | {r['workload']} | "
                         f"{v['median']:.3f} [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}] |")
    lines.extend(['','A paced copy changes the device activity preceding the new turn. Clock or power-state changes '
                  'are possible explanations for a changing remainder, but the one-Hz samples cannot resolve '
                  'the subsecond mechanism. These residuals remain evidence against exact additivity, not a fitted-away correction.','',
                  '## File-tier decomposition and predictive residuals','',
                  'Staged torch serialization and raw fp16 bytes use separate raw-read and CPU-deserialization timers, '
                  'followed by actual H2D copies. Direct torch.load remains an additional baseline. '
                  'The old estimate omits deserialization; the new estimate adds it. Each prediction uses independent '
                  'microbenchmark medians plus the GPU-hit new-turn baseline. '
                  'The raw-read API leg includes buffer allocation, and the BytesIO materialization belongs '
                  'to the torch deserialization leg; neither is advertised as pure physical-media bandwidth.','',
                  '| Format | Median absolute relative TTFT error, old rule | Median absolute relative TTFT error, with deserialization |',
                  '| --- | --- | --- |'])
    for fmt,v in stats['file_errors'].items():
        lines.append(f"| {fmt} | {v['old_median_ape']:.1%} | {v['new_median_ape']:.1%} |")
    lines.extend(['','The overall median weights each completed model/length/turn/session cell equally. '
                  'The replicated main model therefore contributes more cells; per-model residuals follow.','',
                  '| Model | Format | Cells | Old median absolute relative error | With deserialization |',
                  '| --- | --- | --- | --- | --- |'])
    for model,formats in stats['model_file_errors'].items():
        for fmt,v in formats.items():
            lines.append(f"| {model} | {fmt} | {v['cells']} | {v['old_median_ape']:.1%} | {v['new_median_ape']:.1%} |")
    lines.extend(['','Adding a measured leg does not guarantee lower residuals: host dispatch, overlapping copies, '
                  'allocation, cold-read patterns, and GPU clock state can make independently measured costs nonadditive. '
                  'The raw-byte view avoids tensor deserialization but still performs the file read and GPU transfer. '
                  'Physical-read accounting and advisory eviction status remain in the records. '
                  'Phase two uses per-file DONTNEED advice, without a privileged global page-cache flush; '
                  'advice alone does not guarantee a cold physical device.','',
                  '## Clocks, drift, and the pilot anomaly','',
                  'Telemetry samples SM and memory clocks, temperature, power, utilization, and active throttle reasons '
                  'at approximately one Hz. Subsecond timing joins use nearby samples where needed; they cannot '
                  'identify exact clocks for each individual GPU kernel. Timing-specific joined summaries are retained.','',
                  '| Session | GPU-0 telemetry samples | Effective Hz | SM clock range, MHz | Temperature range, C | Power range, W | Throttle masks observed |',
                  '| --- | --- | --- | --- | --- | --- | --- |'])
    for r in rows:
        if r['kind']=='telemetry_summary':
            m=r['metrics']
            lines.append(f"| {r['run_id']} | {r['samples']} | {r['effective_sample_hz']:.3f} | {m['clocks.sm']['minimum']}–{m['clocks.sm']['maximum']} | "
                         f"{m['temperature.gpu']['minimum']}–{m['temperature.gpu']['maximum']} | "
                         f"{m['power.draw']['minimum']}–{m['power.draw']['maximum']} | {', '.join(r['throttle_reason_values'])} |")
    lines.extend(['','These whole-session ranges include loading and idle intervals. They are not proof of thermal '
                  'throttling during a particular measurement. The phase-two Torch CUDA build differs from the pilot; '
                  'cross-phase timing changes are not attributed solely to drift. '
                  'The observed 0x4 event bit denotes software power capping in '
                  '[NVIDIA\'s NVML definitions](https://nvidia.github.io/cuda-python/cuda-bindings/13.4.4/module/generated/cuda.bindings.nvml.ClocksEventReasons.html). '
                  'Joined long-prefill clock samples accompany the timings; these associations are not a controlled causal clock experiment.','',
                  '| Session | Startup-reported power cap, W | Samples above that cap | Maximum raw reported draw, W |',
                  '| --- | --- | --- | --- |'])
    for r in rows:
        if r['kind']=='telemetry_power_quality':
            lines.append(f"| {r['run_id']} | {r['startup_reported_power_cap_w']:.1f} | {r['samples_above_cap']} | {r['maximum_reported_power_w']:.2f} |")
    lines.extend(['','Some power-draw samples exceed the cap shown by the startup display. These readings are '
                  'retained without correction and are not used to calculate energy or establish instantaneous '
                  'physical power. No independent power instrument was available.','',
                  '| Main-model session and workload | Prefix-only median at 8192, ms | Prefix + 32 recompute median, ms | Prefix-only matched SM MHz | Prefix + 32 matched SM MHz |',
                  '| --- | --- | --- | --- | --- |'])
    anomaly=defaultdict(dict)
    for r in summaries:
        if r['model']=='Qwen/Qwen2.5-1.5B' and r['prefix_tokens']==8192 and r['turn_tokens']==32 and r['condition'] in ['prefix_only','recompute']:
            anomaly[(r['run_id'],r['workload'])][r['condition']]=r['median']
    for key,v in sorted(anomaly.items()):
        clocks={r['condition']:r['median_sm_mhz'] for r in rows if r['kind']=='timing_clock_summary'
                and r['run_id']==key[0] and r['workload']==key[1] and r['prefix_tokens']==8192 and r['turn_tokens']==32}
        lines.append(f"| {key[0]}, {key[1]} | {number(v.get('prefix_only'))} | {number(v.get('recompute'))} | "
                     f"{clocks.get('prefix_only','Unavailable')} | {clocks.get('recompute','Unavailable')} |")
    profiles=[r for r in rows if r['kind']=='anomaly_shape_profile']
    if profiles:
        lines.extend(['','| Excluded profile input tokens | Wall, ms | GPU kernels, ms | GEMM kernels, ms |',
                      '| --- | --- | --- | --- |'])
        for r in profiles:
            lines.append(f"| {r['length']} | {r['wall_ms']:.3f} | {r['gpu_kernel_ms']:.3f} | {r['gemm_ms']:.3f} |")
        lines.append('')
        lines.append('Input-shape-specific GEMM kernel names and durations are preserved in the profile summaries. '
                     'The profile is a separate instrumented pass, so its timings do not enter benchmark confidence intervals. '
                     'A matrix-shape or clock explanation for the original pilot must be distinguished from a proved historical cause.')
    lines.extend(['','## Across-session uncertainty','',
                  'Session-to-session spread is the range of separate session medians. Each accompanying CI is '
                  'a within-session percentile bootstrap interval. The session medians are not pooled into one '
                  'artificially narrow interval. The following table selects a short turn and representative conditions; '
                  'all conditions and both new-turn lengths are in the results.','',
                  '| Prefix | Condition | Sessions | Separate session medians, ms | Range / median | Within-session 95% CIs, ms |',
                  '| --- | --- | --- | --- | --- | --- |'])
    for r in rows:
        if r['kind']=='session_spread' and r['turn_tokens']==32 and r['condition'] in ['recompute','simulated_200_MBps','file_raw_staged']:
            lines.append(f"| {r['prefix_tokens']} | {r['condition']} | {r['sessions']} | "
                         f"{', '.join(f'{x:.3f}' for x in r['session_medians_ms'])} | {r['relative_range']:.1%} | "
                         f"{'; '.join(f'[{a:.3f}, {b:.3f}]' for a,b in r['within_session_ci95_ms'])} |")
    lines.extend(['','### Fixed-calibration check in later sessions','',
                  'This check fixes the first main session\'s recompute, GPU-hit, and transfer calibration. '
                  'It predicts later-session decisions without refitting their TTFT baselines. '
                  'It tests session transfer on the same GPU type and input, not transfer to another GPU type.','',
                  '| Later session | Resolved simulated-rate cells | Correct decisions using first-session calibration | Median absolute TTFT prediction error |',
                  '| --- | --- | --- | --- |'])
    for r in rows:
        if r['kind']=='heldout_session_score':
            lines.append(f"| {r['run_id']} | {r['resolved_cells']} | {r['agreements']} | {r['median_absolute_relative_ttft_error']:.1%} |")
    lines.extend(['','## Correctness, unavailable coverage, and budget','',
                  'Every accepted restore must preserve the resident-cache continuation under a stricter same-shape '
                  'comparison, agree on the full-recompute first token, and produce the expected cache length. '
                  'Full-versus-cached fp16 logit differences are reported separately. The first MHA calibration '
                  'failed the pilot elementwise check; recalibration tests restoration against an independently '
                  'computed resident continuation and retains layerwise KV and logit differences.','',
                  ('The original Meta Llama base-model access was gated. The user-authorized ungated Llama-Instruct '
                   'mirror is a distinct weight checkpoint; its observed config and KV layout are verified above. '
                   if 'unsloth/Llama-3.2-3B-Instruct' in configs else
                   'The original Llama base-model access was gated. Any attempted substitute is identified by its actual model ID above. ')
                  + 'The P100 request returned T4s and aborted '
                  'at the allocation check. That attempt provides no P100 measurements. '
                  'Consequently, transfer of the rule across GPU types and the slower-versus-faster GPU hypothesis remain untested. '
                  'Production work was optional and was omitted to prioritize this reference study. '
                  'NOTES.md records the exact deviations, and BUDGET.md records every submitted kernel.','',
                  '## Updated rule of thumb','',
                  'For a calibrated additive estimate, reload when effective bandwidth exceeds `B* = transfer_bytes / (recompute_TTFT - GPU_hit_new_turn_TTFT - overhead - deserialization - other_transfer_legs)` '
                  'with a positive denominator, and recompute otherwise.','',
                  'This report ends the redesigned phase. Further experiments require a new user instruction.'])
    counts=stats['rule_counts']
    findings=['## Findings','',
              f"The TTFT-adjusted rule agrees with {counts['ttft_rule_agreements']} of "
              f"{counts['resolved_comparisons']} resolved simulated-rate cells; the prefix-only rule agrees with "
              f"{counts['prefix_rule_agreements']}. These use measured same-session recompute and GPU-hit baselines; "
              'the fixed-calibration later-session test below is the separate check of prediction across sessions.','']
    main=[r for r in crossings if r['workload']=='ultrachat' and r['turn_tokens']==32]
    main_runs={r['run_id'] for r in main}
    short=[]
    for length in [16,32,64,128]:
        points=[p for r in main if r['prefix_tokens']==length for p in r['points']
                if p['condition']=='simulated_unthrottled']
        if len(points)==len(main_runs) and points and all(p['paired_delta']['ci95'][0]>0 for p in points):
            short.append(length)
    if short:
        findings.extend([f"At prefixes {', '.join(map(str,short))} with a 32-token new turn, "
                         'recompute beats the unthrottled chunked-copy control in every completed main-model session '
                         'with resolved paired intervals. The prefix-only bandwidth threshold is insufficient in this regime.',''])
    for mha in ['EleutherAI/pythia-1.4b','facebook/opt-1.3b']:
        gqa='Qwen/Qwen2.5-1.5B'
        if mha in comparison and gqa in comparison:
            findings.extend([f"At prefix 512 and new turn 32 on matched repeated text, {mha} has simulated crossover "
                             f"{label(comparison[mha]['measured'])} MB/s, versus "
                             f"{label(comparison[gqa]['measured'])} MB/s for {gqa}. "
                             'This model comparison includes prefill-kernel and model-size differences as well as KV layout.',''])
    findings.extend(['The pilot anomaly is assessed with interleaved measurements and a separate excluded profile. '
                     'A failure to reproduce it does not establish its historical cause. P100 transfer remains untested '
                     'because the requested allocation returned T4 hardware.',''])
    findings.extend(['Figures: [main-model TTFT](../figures/phase2-ttft-qwen2.5-1.5b.png), '
                     '[crossover bandwidth versus length](../figures/phase2-crossover-bandwidth-by-length.png), '
                     '[predicted versus interpolated crossover](../figures/phase2-predicted-simulated-crossover.png), '
                     'and [file-rule residuals](../figures/phase2-file-residuals.png).',''])
    position=lines.index('## What was measured')
    lines[position:position]=findings
    (ROOT/'docs/PHASE2_REPORT.md').write_text('\n'.join(lines)+'\n')
    plots(summaries,crossings,files)
    print('Wrote docs/PHASE2_REPORT.md and phase-two figures')


def plots(summaries,crossings,files):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=ROOT/'figures';folder.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(8,5),constrained_layout=True)
    for model in sorted(set(r['model'] for r in crossings if r['workload']=='repeated_control')):
        values=[r for r in crossings if r['model']==model and r['workload']=='repeated_control'
                and r['prefix_tokens']==512 and r['turn_tokens']==32]
        if not values:continue
        r=values[0]
        points=sorted(r['points'],key=lambda p:p['achieved_mb_s'])
        ax.plot([p['achieved_mb_s'] for p in points],[p['delta_ms'] for p in points],marker='o',label=model.split('/')[-1])
    ax.axhline(0,color='black',lw=1)
    ax.set_yscale('symlog',linthresh=5)
    ax.set(xscale='log',xlabel='Achieved simulated transport bandwidth (MB/s)',
           ylabel='Reload TTFT minus recompute TTFT (ms)',title='Simulated-bandwidth sweep: prefix 512, new turn 32')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.savefig(folder/'phase2-simulated-bandwidth.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,5),constrained_layout=True)
    for family in ['GQA','MHA']:
        values=[r for r in crossings if r['workload']=='repeated_control' and r['turn_tokens']==32
                and r['attention_family']==family and r['predicted_ttft_bstar_mb_s'] is not None
                and r['measured']['status']=='bracketed' and not r['measured'].get('nonmonotone')]
        for resolved,marker in [(True,'o'),(False,'x')]:
            selected=[r for r in values if r['measured']['brackets'][0]['paired_ci_resolved']==resolved]
            xs=[r['predicted_ttft_bstar_mb_s'] for r in selected]
            ys=[r['measured']['brackets'][0]['interpolated_mb_s'] for r in selected]
            if xs:ax.scatter(xs,ys,label=family+(' resolved' if resolved else ' median only'),marker=marker,alpha=.7)
    lim=ax.get_xlim();low=max(1,min(lim));high=max(lim)
    ax.plot([low,high],[low,high],color='gray',ls='--')
    ax.set(xscale='log',yscale='log',xlabel='Predicted TTFT break-even bandwidth (MB/s)',
           ylabel='Interpolated simulated crossover (MB/s)',title='Simulated transport: predictions and bracket interpolations')
    ax.legend();ax.grid(alpha=.2)
    fig.savefig(folder/'phase2-predicted-simulated-crossover.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5),sharey=True,constrained_layout=True)
    for ax,family in zip(axes,['GQA','MHA']):
        values=[r for r in crossings if r['workload']=='repeated_control' and r['turn_tokens']==32
                and r['attention_family']==family]
        for model in sorted({r['model'] for r in values}):
            points=sorted([r for r in values if r['model']==model],key=lambda r:r['prefix_tokens'])
            predicted=[r for r in points if r['predicted_ttft_bstar_mb_s'] is not None]
            line,=ax.plot([r['prefix_tokens'] for r in predicted],
                          [r['predicted_ttft_bstar_mb_s'] for r in predicted],
                          ls='--',lw=1,label=model.split('/')[-1])
            color=line.get_color()
            for r in points:
                measured=r['measured'];length=r['prefix_tokens']
                if measured['status']=='bracketed':
                    for bracket in measured['brackets']:
                        low,high=sorted(bracket['achieved_mb_s'])
                        center=bracket['interpolated_mb_s']
                        ax.errorbar(length,center,yerr=[[center-low],[high-center]],fmt='o',ms=4,
                                    color=color,capsize=3,alpha=1 if bracket['paired_ci_resolved'] else .4)
                elif measured['status']=='reload_faster_at_all_tested_simulated_rates':
                    ax.scatter(length,measured['upper_bound_target_mb_s'],marker='v',color=color,s=25)
                elif measured['status']=='recompute_faster_at_all_tested_simulated_rates':
                    ax.scatter(length,measured['largest_achieved_mb_s'],marker='^',color=color,s=25)
        ax.set(xscale='log',yscale='log',xlabel='Prefix tokens',title=family+', repeated text, new turn 32')
        ax.grid(alpha=.2)
        if ax.get_legend_handles_labels()[0]:ax.legend(fontsize=8)
    axes[0].set_ylabel('Simulated break-even transport bandwidth (MB/s)')
    fig.suptitle('T4: observed brackets and harmonic estimates; dashed: TTFT prediction\n'
                 'Faint bars: unresolved endpoint CIs; triangles: bounds only',fontsize=10)
    fig.savefig(folder/'phase2-crossover-bandwidth-by-length.png',dpi=180)
    fig.savefig(folder/'phase2-crossover-bandwidth-by-length.pdf',metadata={'CreationDate':None,'ModDate':None})
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4),constrained_layout=True)
    formats=['torch','raw'];old=[];new=[]
    for fmt in formats:
        values=[r for r in files if r['format']==fmt]
        old.append(statistics.median(abs(r['old_signed_relative_error'])*100 for r in values) if values else 0)
        new.append(statistics.median(abs(r['new_signed_relative_error'])*100 for r in values) if values else 0)
    x=np.arange(len(formats));ax.bar(x-.18,old,.36,label='Read + H2D + new turn')
    ax.bar(x+.18,new,.36,label='Read + deserialize + H2D + new turn')
    ax.set_xticks(x,formats);ax.set(ylabel='Median absolute TTFT prediction error (%)',title='Measured file paths: predictive residuals')
    ax.legend(fontsize=8)
    fig.savefig(folder/'phase2-file-residuals.png',dpi=180);plt.close(fig)
    selected=['recompute','gpu_hit','simulated_50_MBps','simulated_200_MBps',
              'simulated_1600_MBps','simulated_unthrottled','file_torch_direct','file_raw_staged']
    pretty={'recompute':'Recompute','gpu_hit':'Resident GPU control',
            'simulated_50_MBps':'Simulated 50 MB/s','simulated_200_MBps':'Simulated 200 MB/s',
            'simulated_1600_MBps':'Simulated 1600 MB/s','simulated_unthrottled':'Unthrottled chunked-copy control',
            'file_torch_direct':'Local file: torch.load','file_raw_staged':'Local file: raw bytes'}
    from matplotlib.ticker import NullLocator,ScalarFormatter
    for model in sorted(set(r['model'] for r in summaries)):
        workload='ultrachat' if model=='Qwen/Qwen2.5-1.5B' else 'repeated_control'
        values=[r for r in summaries if r['model']==model and r['workload']==workload]
        if not values:continue
        fig,axes=plt.subplots(1,2,figsize=(12,4.5),constrained_layout=True)
        for ax,turn in zip(axes,[32,256]):
            for condition in selected:
                points=defaultdict(list)
                for r in values:
                    if r['turn_tokens']==turn and r['condition']==condition:points[r['prefix_tokens']].append(r)
                if not points:continue
                lengths=sorted(points)
                medians=np.array([statistics.median(r['median'] for r in points[length]) for length in lengths])
                # Main-model band is the range of independent session medians; other models show bootstrap CIs.
                low=np.array([min(r['median'] for r in points[length]) if len(points[length])>1
                              else points[length][0]['ci95'][0] for length in lengths])
                high=np.array([max(r['median'] for r in points[length]) if len(points[length])>1
                               else points[length][0]['ci95'][1] for length in lengths])
                line,=ax.plot(lengths,medians,marker='o',ms=3,label=pretty[condition])
                ax.fill_between(lengths,low,high,color=line.get_color(),alpha=.12)
            ax.set(xscale='log',yscale='log',xlabel='Prefix tokens',ylabel='TTFT (ms)',
                   title=model.split('/')[-1]+f', new turn {turn}')
            available=[r['prefix_tokens'] for r in values if r['turn_tokens']==turn]
            ax.set_xticks([x for x in [16,64,256,1024,4096,16384] if available and x<=max(available)])
            ax.xaxis.set_major_formatter(ScalarFormatter());ax.xaxis.set_minor_locator(NullLocator())
            ax.grid(alpha=.2)
        axes[-1].legend(fontsize=7,loc='upper left')
        fig.suptitle('Simulated transport and measured file paths; '+
                     ('bands: range of session medians' if workload=='ultrachat' else 'bands: within-session bootstrap 95% CIs'),fontsize=10)
        stem='phase2-ttft-'+model.split('/')[-1].lower()
        fig.savefig(folder/(stem+'.png'),dpi=180)
        fig.savefig(folder/(stem+'.pdf'),metadata={'CreationDate':None,'ModDate':None})
        plt.close(fig)


if __name__=='__main__':
    report()
