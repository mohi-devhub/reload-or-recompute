"""Render the hardware-transfer report and figure from archived analysis rows."""
from collections import defaultdict
import csv
import json
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from phase3_plan import MAIN,MODELS
from report_phase2 import label,number


def median(values):return statistics.median(values) if values else None
def fmt(x):return f'{x:.2f}' if x is not None else 'Unidentified'
def short(m):return m.split('/')[-1]


def report():
    rows=[json.loads(l) for l in (ROOT/'outputs/phase3_analysis.jsonl').read_text().splitlines()]
    ledger=json.loads((ROOT/'outputs/phase3_ledger.json').read_text())
    t4=json.loads((ROOT/'configs/phase3_t4_reference.json').read_text())['observations']
    scorecards=[r for r in rows if r['kind']=='phase3_scorecard']
    scores=[r for r in rows if r['kind']=='phase3_prediction_score']
    crosses=[r for r in rows if r['kind']=='phase3_bandwidth_crossover']
    summaries=[r for r in rows if r['kind']=='phase3_summary' and r['purpose']=='sweep' and r['complete']]
    micros=[r for r in rows if r['kind']=='phase3_micro_summary']
    audit=next(r for r in rows if r['kind']=='phase3_audit')
    lines=['# Phase three: preregistered transfer across GPUs','',
           'Predictions were frozen from short, independent calibration before each GPU sweep. '
           'No coefficient was refitted from sweep results. All paced rates below are **simulated bandwidth**, '
           'using the unchanged phase-two reference timing functions.','',
           f"Timing records: {audit['measurements']}; invalid: {audit['invalid_measurements']}; "
           f"missing registered cells: {audit['missing_prediction_cells']}. "
           f"Conservative main cost including reservations: ${audit['main_cost_estimate_and_reservation_usd']:.4f}; "
           f"optional H100: ${audit['h100_cost_estimate_and_reservation_usd']:.4f}. "
           'These are list-price estimates including CPU, capped memory, initialization and infrastructure, not an invoice.','',
           '## Frozen prediction scorecard','',
           '| Requested tier / allocated name | Region or session | Correct / resolved decisions | Unresolved | Complete timing cells | Median absolute TTFT error, ms | Median absolute relative error |',
           '| --- | --- | --- | --- | --- | --- | --- |']
    for r in scorecards:
        lines.append(f"| {r['gpu']} / {', '.join(r['allocated_gpu_names'])} | {r['scope']} | {r['correct_decisions']} / {r['resolved_decisions']} | {r['unresolved_decisions']} | {r['complete_cells']} | {r['median_absolute_ttft_error_ms']:.3f} | {100*r['median_absolute_relative_ttft_error']:.1f}% |")
    lines.extend(['','Resolved decisions require the paired-round bootstrap interval for path-minus-recompute TTFT to exclude zero. '
                  'Errors include prefix-only, recompute and resident-hit baselines; decisions include resident hit and reload paths. '
                  'The unthrottled pinned path is counted once. Cell counts are descriptive and are not independent trials. '
                  'Anchor/interpolation/extrapolation refer to the calibration length range.','',
                  'Largest absolute TTFT prediction errors (all conditions, without refitting):','',
                  '| Requested GPU | Model | Prefix / new turn | Condition | Predicted / observed, ms | Region |',
                  '| --- | --- | --- | --- | --- | --- |'])
    for r in sorted(scores,key=lambda s:s['absolute_error_ms'],reverse=True)[:5]:
        lines.append(f"| {r['gpu']} | {short(r['model'])} | {r['prefix_tokens']} / {r['turn_tokens']} | {r['condition']} | {r['predicted_ttft_ms']:.2f} / {r['observed_ttft_ms']:.2f} | {r['calibration_region']} |")
    lines.extend(['',
                  '## Hardware and provenance','',
                  '| Run | Allocated GPU / capability | Driver and PCIe snapshot | Torch / Transformers | Wall seconds |',
                  '| --- | --- | --- | --- | --- |'])
    for r in ledger['runs']:
        if r.get('environment'):
            e=r['environment'];lines.append(f"| {r['name']} | {', '.join(e['gpu_names'])} / {e['compute_capability']} | {e['gpu_query']} | {e['torch']} / {e['transformers']} | {r['duration_s']:.1f} |")
    lines.extend(['','Modal names its Ampere request `A10`; the actual GPU name above is authoritative. '
                  'A10 and A10G names within that service tier are retained separately in the session scorecards. '
                  'GPU UUIDs, exact driver/runtime versions, clocks, CPU/RAM and disk capacity are retained per run. '
                  'All measurements use fp16 and efficient/math SDPA, with FlashAttention disabled. '
                  'The full scheduling difference and protected function hashes are in `outputs/phase3_provenance.json`; '
                  'each executed source and adapter hash is also in the canonical records.','',
                  '## Crossover bandwidth and the throughput hypothesis','',
                  'The complete per-session, per-model, per-length predictions and observed brackets are in '
                  '[phase3_crossovers.csv](../outputs/phase3_crossovers.csv). Brackets are measured adjacent simulated-rate cells; '
                  'interpolation is supplementary and assumes local inverse-bandwidth linearity. '
                  'A “median only” bracket has an unresolved endpoint interval.','',
                  '| GPU / session | Model | Prefix / new turn | Predicted B*, MB/s | Observed simulated-bandwidth bracket, MB/s | Prefill tokens/s | Pinned / pageable H2D, MB/s |',
                  '| --- | --- | --- | --- | --- | --- | --- |'])
    def bandwidth(run,model,L,c):
        selected=[r for r in micros if r['run_id']==run and r['model']==model and r['prefix_tokens']==L and r['condition']==c]
        return selected[0]['bandwidth_mb_s']['median'] if selected else None
    for r in crosses:
        if r['prefix_tokens']!=1024 or r['turn_tokens']!=32:continue
        pin=bandwidth(r['run_id'],r['model'],1024,'h2d_pinned');page=bandwidth(r['run_id'],r['model'],1024,'h2d_pageable')
        lines.append(f"| {r['gpu']} / {r['run_id']} | {short(r['model'])} | 1024 / 32 | {fmt(r['predicted_bstar_mb_s'])} | {label(r['measured'])} | {r['measured_prefill_tokens_s']:.1f} | {fmt(pin)} / {fmt(page)} |")
    # The historical T4 observations are descriptive, not preregistered new-GPU predictions.
    for r in t4:
        if r['kind']!='bandwidth_crossover' or r['prefix_tokens']!=1024 or r['turn_tokens']!=32:continue
        if r['model']==MAIN and r['workload']!='ultrachat':continue
        pref=[s for s in t4 if s['kind']=='phase2_summary' and s['run_id']==r['run_id'] and s['model']==r['model'] and s['prefix_tokens']==1024 and s['turn_tokens']==32 and s['condition']=='prefix_only']
        if not pref:continue
        h2d={s['condition']:s['bandwidth_mb_s']['median'] for s in t4 if s['kind']=='phase2_micro_summary' and s['run_id']==r['run_id'] and s['model']==r['model'] and s['prefix_tokens']==1024}
        lines.append(f"| T4 / {r['run_id']} | {short(r['model'])} | 1024 / 32 | {fmt(r['predicted_ttft_bstar_mb_s'])} (descriptive) | {label(r['measured'])} | {pref[0]['prefill_tokens_s']:.1f} | {fmt(h2d.get('h2d_pinned'))} / {fmt(h2d.get('h2d_pageable'))} |")
    lines.extend(['','| GPU | Compatible with at least one / all matched T4 sessions | Not ratio-resolved |',
                  '| --- | --- | --- |'])
    for gpu in sorted({r['gpu'] for r in crosses}):
        hs=[r for r in rows if r['kind']=='phase3_hypothesis_score' and r['gpu']==gpu]
        resolved=[r for r in hs if r['compatible'] is not None]
        lines.append(f"| {gpu} | {sum(r['compatible'] for r in resolved)} / {len(resolved)} at least one; {sum(r['compatible_all'] for r in resolved)} / {len(resolved)} all | {sum(r['compatible'] is None for r in hs)} |")
    lines.extend(['','The frozen hypothesis ratio is calibration-predicted new-GPU prefill throughput divided by matched T4 throughput. '
                  'Compatibility compares it against resolved achieved-bandwidth crossover-ratio brackets, rather than dividing '
                  'two formula outputs. Broad brackets and censored thresholds limit this test; compatibility does not establish equality. '
                  'The adjusted threshold also depends on the new-turn baseline and fixed overhead, so an exact throughput ratio is not guaranteed.','',
                  '![Break-even bandwidth versus prefill throughput](../figures/phase3_bstar_vs_prefill.png)','',
                  '## Real file paths and short contexts','',
                  '| GPU | Model | Real path | Reload wins / resolved cells | Unresolved | Median signed prediction error, ms |',
                  '| --- | --- | --- | --- | --- | --- |'])
    for gpu in sorted({r['gpu'] for r in scores}):
        for model in MODELS:
            for condition in ['file_raw_staged','file_torch_direct']:
                values=[s for s in scores if s['gpu']==gpu and s['model']==model and s['condition']==condition]
                if not values:continue
                resolved=[s for s in values if s['observed_reload'] is not None]
                lines.append(f"| {gpu} | {short(model)} | {condition} | {sum(s['observed_reload'] for s in resolved)} / {len(resolved)} | {len(values)-len(resolved)} | {median([s['signed_error_ms'] for s in values]):.3f} |")
    lines.extend(['','File predictions include independent read/deserialization/H2D legs, or the direct torch-load CPU leg plus H2D. '
                  'Files are on local container scratch; advisory eviction and physical-read ratios do not prove a uniformly cold physical device. '
                  'These host/storage paths differ from Kaggle, so changes in file wins cannot be assigned solely to GPU speed.','',
                  '| GPU | Main model, prefixes through 128 | Recompute wins / resolved pinned-path cells | Unresolved |',
                  '| --- | --- | --- | --- |'])
    for gpu in sorted({r['gpu'] for r in scores}):
        values=[s for s in scores if s['gpu']==gpu and s['model']==MAIN and s['prefix_tokens']<=128 and s['condition']=='simulated_unthrottled']
        resolved=[s for s in values if s['observed_reload'] is not None]
        lines.append(f"| {gpu} | Separate turns and sessions | {sum(not s['observed_reload'] for s in resolved)} / {len(resolved)} | {len(values)-len(resolved)} |")
    lines.extend(['','Short-prefix decisions can be dominated by host dispatch, allocation and the resident-hit baseline. '
                  'The full score records retain every short-length decision and its paired interval; the sparse length grid '
                  'cannot establish a continuous crossover length.','',
                  '## Session spread and clock drift','',
                  '| GPU | New turn | Median / maximum relative range of recompute session medians |',
                  '| --- | --- | --- |'])
    for gpu in sorted({r['gpu'] for r in crosses}):
        for turn in [32,256]:
            values=[r['range_over_median'] for r in rows if r['kind']=='phase3_session_spread' and r['gpu']==gpu and r['turn_tokens']==turn and r['condition']=='recompute']
            if values:lines.append(f"| {gpu} | {turn} | {100*median(values):.1f}% / {100*max(values):.1f}% |")
    old=[r for r in t4 if r['kind']=='session_spread' and r['condition']=='recompute']
    if old:
        lines.append('')
        for turn in [32,256]:
            values=[r['relative_range'] for r in old if r['turn_tokens']==turn]
            if values:lines.append(f"T4 new turn {turn}: median recompute session range {100*median(values):.1f}%, maximum {100*max(values):.1f}%.")
    lines.extend(['','| GPU / session | Prefix / new turn | Recompute median and within-session 95% CI, ms | Across-session range / median |',
                  '| --- | --- | --- | --- |'])
    spreads={(r['gpu'],r['prefix_tokens'],r['turn_tokens']):r for r in rows if r['kind']=='phase3_session_spread' and r['condition']=='recompute'}
    for r in summaries:
        if r['model']!=MAIN or r['prefix_tokens'] not in [1024,8192] or r['condition']!='recompute':continue
        spread=spreads.get((r['gpu'],r['prefix_tokens'],r['turn_tokens']))
        if spread:lines.append(f"| {r['gpu']} / {r['run_id']} | {r['prefix_tokens']} / {r['turn_tokens']} | {r['median']:.3f} [{r['ci95'][0]:.3f}, {r['ci95'][1]:.3f}] | {100*spread['range_over_median']:.1f}% |")
    lines.extend(['','| Run | Samples during timed intervals | SM MHz | Memory MHz | Temperature C | Power W | PCIe gen / width | Throttle reason bitmasks |',
                  '| --- | --- | --- | --- | --- | --- | --- | --- |'])
    for r in rows:
        if r['kind']=='phase3_telemetry_summary':
            v=r['timing_ranges'];lines.append(f"| {r['run_id']} | {r['timing_sample_count']} | {v.get('clocks.sm')} | {v.get('clocks.mem')} | {v.get('temperature.gpu')} | {v.get('power.draw')} | {v.get('pcie.link.gen.current')} / {v.get('pcie.link.width.current')} | {', '.join(r['timing_throttle_reasons'])} |")
    lines.extend(['','Telemetry is sampled at approximately one-second intervals and can miss brief short-context trials. '
                  'Randomized within-round condition order reduces ordering bias; telemetry association does not prove a cause '
                  'for latency differences. GPU UUIDs in the ledger distinguish independent allocations from reused physical cards.','',
                  'Bitmask `0x4` denotes software power-cap limiting, per the '
                  '[NVIDIA NVML definitions](https://docs.nvidia.com/deploy/archive/R535/nvml-api/group__nvmlClocksEventReasons.html). '
                  'Per-condition clock sample counts and medians are archived separately, since pooled timed intervals include rate-limiter sleeps.','',
                  '## Rule of thumb and limits','',
                  'Reload when `KV_bytes / effective_bandwidth + CPU_read_and_deserialization + fixed_overhead + resident_new_turn_TTFT < full_recompute_TTFT`; '
                  'otherwise recompute, using locally calibrated baselines and treating near-zero savings as unresolved.','',
                  'This is a single-request fp16 reference experiment, not a serving-throughput benchmark. It excludes cache creation, '
                  'tokenization, network transfer and queueing; CPU caches and files already exist. The paced copy path simulates '
                  'bandwidth and does not emulate network/storage latency distributions. Calibration extrapolation, '
                  'host CPU differences, CUDA/driver differences, per-file eviction limits, two-session sampling and '
                  'unpropagated calibration-fit uncertainty, '
                  'model-specific context limits restrict transfer claims. Full configuration drops are in `configs/phase3_plan.json` '
                  'and deviations are in `docs/NOTES.md`. No production-path claim is made.',''])
    (ROOT/'docs/PHASE3_REPORT.md').write_text('\n'.join(lines))
    csvpath=ROOT/'outputs/phase3_crossovers.csv'
    fields=['gpu','allocated_gpu_name']+['run_id','model','workload','prefix_tokens','turn_tokens','kv_bytes_per_token','predicted_bstar_mb_s','measured_prefill_tokens_s','t4_prefill_tokens_s','measured_prefill_ratio_to_t4','hypothesis_prefill_ratio_to_t4','observed_bracket','observed_harmonic_estimate_mb_s']
    with csvpath.open('w') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in crosses:writer.writerow({**{k:r[k] for k in fields if k not in ['observed_bracket','observed_harmonic_estimate_mb_s']},
                                         'observed_bracket':label(r['measured']),
                                         'observed_harmonic_estimate_mb_s':';'.join(str(b['interpolated_mb_s']) for b in r['measured'].get('brackets',[]))})
    figure(crosses,t4)


def figure(crosses,t4):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors={'T4':'#707070','L4':'#0072b2','A10':'#d55e00','H100!':'#009e73'}
    fig,axes=plt.subplots(2,3,figsize=(15,9),layout='constrained')
    for ax,model in zip(axes.flat,MODELS):
        plotted=[]
        for r in crosses:
            if r['model']!=model or r['turn_tokens']!=32:continue
            plotted.append(dict(gpu=r['gpu'],session=r['run_id'],x=r['measured_prefill_tokens_s'],
                                length=r['prefix_tokens'],px=r['predicted_prefill_tokens_s'],pred=r['predicted_bstar_mb_s'],measured=r['measured']))
        for r in t4:
            if r['kind']!='bandwidth_crossover' or r['model']!=model or r['turn_tokens']!=32:continue
            if model==MAIN and r['workload']!='ultrachat':continue
            prefix=r['kv_bytes_per_token']*r['prefix_tokens']/r['predicted_prefix_bstar_mb_s']/1000
            plotted.append(dict(gpu='T4',session=r['run_id'],x=r['prefix_tokens']*1000/prefix,px=None,pred=None,measured=r['measured']))
        sessions=defaultdict(list)
        for r in plotted:
            if r['pred'] is not None and r['px'] is not None:sessions[(r['gpu'],r['session'])].append(r)
            for b in r['measured'].get('brackets',[]):
                lo,hi=sorted(b['achieved_mb_s']);y=b['interpolated_mb_s']
                if y is None:continue
                ax.errorbar(r['x'],y,yerr=[[y-lo],[hi-y]],fmt='o' if b['paired_ci_resolved'] else 'x',
                            color=colors[r['gpu']],alpha=.65,markersize=4,linewidth=.7)
        for (gpu,session),values in sessions.items():
            values=sorted(values,key=lambda r:r['length'])
            ax.plot([r['px'] for r in values],[r['pred'] for r in values],color=colors[gpu],linestyle='--',alpha=.6)
        if plotted:
            config=json.loads((ROOT/'configs/phase3_t4_reference.json').read_text())['configs'][model]
            xs=[min(r['x'] for r in plotted),max(r['x'] for r in plotted)]
            ax.plot(xs,[config['kv_bytes_per_token']*x/1e6 for x in xs],color='#777777',linestyle=':',linewidth=1)
        ax.set_title(short(model));ax.set_xlabel('Prefix-only prefill tokens/s');ax.set_ylabel('Break-even bandwidth, MB/s')
        ax.set_xscale('log');ax.set_yscale('log');ax.grid(alpha=.2)
    axes.flat[-1].axis('off')
    from matplotlib.lines import Line2D
    handles=[Line2D([0],[0],marker='o',color=c,label=gpu) for gpu,c in colors.items() if any(r.get('gpu')==gpu for r in crosses) or gpu=='T4']
    handles.extend([Line2D([0],[0],color='black',linestyle='--',label='Frozen adjusted-rule prediction'),
                    Line2D([0],[0],color='#777777',linestyle=':',label='Prefix-only KV bytes/token × tokens/s'),
                    Line2D([0],[0],color='black',marker='x',linestyle='',label='Median-only bracket')])
    axes.flat[-1].legend(handles=handles,loc='center',frameon=False)
    axes.flat[-1].text(.05,.1,'Points: harmonic interpolation within observed\nachieved-rate brackets; bars: bracket endpoints.\nDashed: calibration-only predictions, no refit.\nOnly bracketed thresholds shown; censoring retained\nin the CSV and canonical records.',transform=axes.flat[-1].transAxes,fontsize=10)
    fig.suptitle('Simulated-bandwidth crossovers versus prefill throughput (new turn 32)')
    folder=ROOT/'figures';folder.mkdir(exist_ok=True);fig.savefig(folder/'phase3_bstar_vs_prefill.png',dpi=170);plt.close(fig)


if __name__=='__main__':report()
