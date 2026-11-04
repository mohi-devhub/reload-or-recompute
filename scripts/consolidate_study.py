"""Build a bounded claim inventory and paper-ready views from the canonical archive, CPU only."""
import argparse
from collections import Counter,defaultdict
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from study_hardware import separate,display,hardware
from report_phase2 import label
MAIN='Qwen/Qwen2.5-1.5B'
MHA=['EleutherAI/pythia-1.4b','microsoft/phi-2']
COLORS={'T4':'#555555','L4':'#0072b2','A10':'#d55e00','A10G':'#aa4499','H100!':'#009e73'}


def dump(value):return json.dumps(value,indent=2,allow_nan=False)+'\n'
def median(values):return statistics.median(values)
def short(model):return model.split('/')[-1]
def sha(payload):return hashlib.sha256(payload).hexdigest()


def load_archive():
    manifest=json.loads((ROOT/'outputs/results_archive.json').read_text());compressed=(ROOT/manifest['archive_path']).read_bytes()
    assert sha(compressed)==manifest['compressed_sha256'],'Archive checksum mismatch'
    payload=gzip.decompress(compressed);assert sha(payload)==manifest['uncompressed_sha256'],'Canonical checksum mismatch'
    lines=payload.splitlines(keepends=True)
    base=[(line,json.loads(line)) for line in lines if line.strip()]
    base=[(line,r) for line,r in base if r.get('phase')!='consolidation']
    return [r for _,r in base],b''.join(line for line,_ in base)


def derive(rows):
    phase3=separate([r for r in rows if r.get('phase')=='phase3' and r.get('record_origin')=='analysis'],rows)
    phase2=[r for r in rows if r.get('phase')=='phase2'];by_kind=defaultdict(list)
    for r in rows:by_kind[r['kind']].append(r)
    audit=[]
    for phase in ['pilot','phase2','phase3']:
        groups=defaultdict(list)
        for r in rows:
            if r.get('phase','pilot')!=phase or not isinstance(r.get('physical_read_bytes'),(int,float)):continue
            if r.get('condition','').startswith('file') and r['kind'] in ['measurement','microbenchmark','ttft','bandwidth']:groups[r['kind'],r['condition']].append(r)
        for (kind,condition),values in groups.items():
            ratios=[r['physical_read_bytes']/r.get('file_bytes',r.get('bytes')) for r in values if r.get('file_bytes',r.get('bytes'))]
            audit.append(dict(phase=phase,kind=kind,condition=condition,samples=len(values),positive=sum(r['physical_read_bytes']>0 for r in values),zero=sum(r['physical_read_bytes']==0 for r in values),minimum_bytes=min(r['physical_read_bytes'] for r in values),maximum_bytes=max(r['physical_read_bytes'] for r in values),median_physical_to_file_ratio=median(ratios) if ratios else None,
                min_prefix=min(r['prefix_tokens'] for r in values),max_prefix=max(r['prefix_tokens'] for r in values),models=sorted({r.get('model',MAIN) for r in values})))
    scorecards=[r for r in phase3 if r['kind']=='phase3_scorecard' and r['scope']=='all']
    scores=[r for r in phase3 if r['kind']=='phase3_prediction_score']
    file_wins=[]
    for gpu in ['T4','L4','A10','A10G','H100!']:
        for model in MHA:
            for path in ['file_raw_staged','file_torch_direct']:
                if gpu=='T4':
                    values=[r for r in phase2 if r['kind']=='return_path_comparison' and r['model']==model and r['condition']==path]
                    decisions=[r['path_faster'] for r in values]
                else:
                    values=[r for r in scores if r['gpu']==gpu and r['model']==model and r['condition']==path]
                    decisions=[r['observed_reload'] for r in values]
                if not values:continue
                for comparison,selected in [('all observed',values),('matched prefix and turn',[r for r in values if r['prefix_tokens'] in [64,256,512,1024] and r['turn_tokens']==32])]:
                    decisions=[r['path_faster'] if gpu=='T4' else r['observed_reload'] for r in selected]
                    file_wins.append(dict(gpu=gpu,model=model,condition=path,comparison=comparison,wins=sum(d is True for d in decisions),resolved=sum(d is not None for d in decisions),unresolved=sum(d is None for d in decisions),prefixes=sorted({r['prefix_tokens'] for r in selected}),turns=sorted({r['turn_tokens'] for r in selected})))
    cross=[]
    for r in rows:
        if r.get('phase')=='phase2' and r['kind']=='bandwidth_crossover':
            row=dict(r,gpu='T4',predicted_bstar_mb_s=r['predicted_ttft_bstar_mb_s'],prediction_kind='descriptive same-session T4 rule')
            pref=next(p for p in phase2 if p['kind']=='phase2_summary' and all(p[k]==r[k] for k in ['run_id','model','workload','prefix_tokens','turn_tokens']) and p['condition']=='prefix_only')
            row['measured_prefill_tokens_s']=pref['prefill_tokens_s'];cross.append(row)
    cross += [dict(r,prediction_kind='frozen calibration-only prediction') for r in phase3 if r['kind']=='phase3_bandwidth_crossover']
    short_regimes=[r for r in phase3 if r['kind']=='phase3_short_regime']
    hypotheses=[]
    for gpu in COLORS:
        values=[r for r in phase3 if r['kind']=='phase3_hypothesis_score' and r['gpu']==gpu]
        if not values:continue
        resolved=[r for r in values if r['compatible'] is not None]
        hypotheses.append(dict(gpu=gpu,resolved=len(resolved),compatible_any=sum(r['compatible'] for r in resolved),compatible_all=sum(r['compatible_all'] for r in resolved),unresolved=len(values)-len(resolved)))
    configs={r['model']:r['kv_bytes_per_token'] for r in by_kind['model_config'] if r.get('phase')=='phase2' and 'kv_bytes_per_token' in r}
    coverage=defaultdict(list)
    for r in rows:
        if r.get('phase')=='phase3':continue  # use the board-separated view below
        if r['kind']=='phase2_summary' and r['purpose']=='sweep' and r['condition']=='recompute' and r['publication_repeat_count_met']:
            coverage[('phase2','T4',r['model'],r['workload'],r['turn_tokens'])].append(r)
        elif r['kind']=='summary' and r.get('measurement_kind')=='ttft' and r['condition']=='recompute':
            coverage[('pilot','T4',MAIN,'repeated_control',r['turn_tokens'])].append(r)
    for r in phase3:
        if r['kind']=='phase3_summary' and r['purpose']=='sweep' and r['condition']=='recompute' and r['complete']:
            coverage[('phase3',r['gpu'],r['model'],r['workload'],r['turn_tokens'])].append(r)
    coverage=[dict(phase=k[0],gpu=k[1],hardware=display(k[1]),model=k[2],workload=k[3],turn_tokens=k[4],
                   prefixes=sorted({r['prefix_tokens'] for r in values}),sessions=sorted({r['run_id'] for r in values})) for k,values in sorted(coverage.items())]
    return dict(file_observability=audit,scorecards=scorecards,file_wins=file_wins,crossovers=cross,short_regimes=short_regimes,hypotheses=hypotheses,phase3=phase3,configs=configs,coverage=coverage)


def claims(rows,d):
    cs=[]
    def add(title,strength,numbers,scope,sources,caveat=''):
        cs.append(dict(id=len(cs)+1,title=title,strength=strength,numbers=numbers,scope=scope,sources=sources,caveat=caveat))
    pilot=[r for r in rows if r['kind']=='summary' and r.get('measurement_kind')=='ttft'];pilot_wins=[]
    for r in pilot:
        if r['condition'] in ['cpu_pinned','cpu_pageable','file']:
            rec=next(p for p in pilot if p['condition']=='recompute' and p['prefix_tokens']==r['prefix_tokens'] and p['turn_tokens']==r['turn_tokens']);pilot_wins.append(r['median']<rec['median'])
    add('The pilot found reload faster at every sampled prefix, without locating a crossover length.','supported',f"{sum(pilot_wins)}/{len(pilot_wins)} reload-path median comparisons favor reload; prefixes 512, 2048, 8192; turns 32 and 256; 12 repeats per cell.",'Kaggle T4; Qwen2.5-1.5B; repeated text; pinned, pageable and file paths.',['summary / measurement_kind=ttft','docs/PILOT_REPORT.md'], 'Median ordering is descriptive; the pilot does not establish a universal crossover length.')
    bs=[r for r in rows if r['kind']=='pilot_bstar']
    add('The pilot prefix-only bandwidth threshold is measured, not assumed.','supported','; '.join(f"L={r['prefix_tokens']}: {r['prefix_bstar_bytes_s']/1e6:.3f} MB/s" for r in bs),'Pilot T4, Qwen2.5-1.5B; prefix-only threshold, independent of later TTFT adjustment.',['pilot_bstar','docs/NOTES.md'],'These values do not include returning-turn or fixed costs.')
    totals=next(r for r in rows if r['kind']=='phase2_report_totals')
    add('The redesigned T4 data cover seven fp16 models with no invalid accepted sweep timings.','strong',f"{totals['accepted_measurements']} accepted timings; {totals['invalid_measurements']} invalid; {len(d['configs'])} measured model configurations; {totals['full_sessions']} full sweep sessions.",'T4; prefixes and new-turn coverage are enumerated per run in the phase-two report.',['phase2_report_totals','docs/PHASE2_REPORT.md#model-coverage-and-kv-size'],'Native context and budget exclusions prevent a balanced full grid.')
    add('Verified KV size differs substantially across the measured attention layouts.','strong','; '.join(f"{short(m)} = {b} bytes/token" for m,b in sorted(d['configs'].items())),'Seven fp16 model configurations on T4; the five transfer models match their cache tensors on Modal.',['model_config + cache_layout','docs/PHASE2_REPORT.md#model-coverage-and-kv-size'],'Models also differ in size and kernels; this is not an isolated GQA/MHA architecture intervention.')
    rule=totals['rule_counts']
    add('Adding the resident-turn baseline improves descriptive T4 rule agreement.','supported',f"TTFT-adjusted {rule['ttft_rule_agreements']}/{rule['resolved_comparisons']}; prefix-only {rule['prefix_rule_agreements']}/{rule['resolved_comparisons']} resolved simulated-rate decisions.",'T4, seven models and observed lengths; all simulated rates; same-session measured baselines.',['phase2_report_totals.rule_counts','docs/PHASE2_REPORT.md#findings'],'This is descriptive agreement, not preregistered hardware transfer or independent Bernoulli trials.')
    half=next(r for r in d['crossovers'] if r['model']=='Qwen/Qwen2.5-0.5B' and r['prefix_tokens']==512 and r['turn_tokens']==32)
    add('Returning-turn and fixed costs can dominate a small KV footprint.','supported',f"Qwen2.5-0.5B at L=512, N=32: prefix-only B* {half['predicted_prefix_bstar_mb_s']:.3f} MB/s; adjusted B* {half['predicted_bstar_mb_s']:.3f} MB/s; observed {label(half['measured'])} MB/s.",'T4, Qwen2.5-0.5B repeated-text control.',['bandwidth_crossover','docs/PHASE2_REPORT.md#findings'],'Use B* = KV_bytes / (T_recompute - T_GPU_hit - fixed_overhead - other_CPU_and_transfer_legs), only for a positive denominator. Count read, deserialization and H2D costs once; the prefix-only formula is insufficient here.')
    family=[]
    for model in ['Qwen/Qwen2.5-1.5B','Qwen/Qwen2.5-3B',*MHA]:
        r=next(r for r in d['crossovers'] if r['gpu']=='T4' and r['model']==model and r['workload']=='repeated_control' and r['prefix_tokens']==512 and r['turn_tokens']==32)
        family.append(f"{short(model)}: {label(r['measured'])} MB/s")
    add('The selected MHA controls require higher simulated bandwidth than the selected GQA controls.','supported','; '.join(family),'T4 repeated text, prefix 512 and new turn 32; Qwen2.5-1.5B/3B versus Pythia-1.4B and Phi-2.',['bandwidth_crossover','docs/PHASE2_REPORT.md#findings'],'Descriptive model comparison. Model size, prefill kernels and cache layout all differ; this does not isolate the causal effect of GQA.')
    held=[r for r in rows if r['kind']=='heldout_session_score']
    add('A fixed first-session T4 calibration predicts later main-model sessions reasonably well.','supported','; '.join(f"{r['run_id']}: {r['agreements']}/{r['resolved_cells']} correct, median relative TTFT error {100*r['median_absolute_relative_ttft_error']:.3f}%" for r in held),'T4; Qwen2.5-1.5B UltraChat; common grid; calibration stays fixed.',['heldout_session_score','docs/PHASE2_REPORT.md'],'Same hardware type and input; no claim about unseen GPU types.')
    scores=d['scorecards']
    add('Frozen calibration transfers to most resolved cells on each observed board.','supported','; '.join(f"{display(r['gpu'])}: {r['correct_decisions']}/{r['resolved_decisions']} correct, {r['unresolved_decisions']} unresolved, median absolute TTFT error {r['median_absolute_ttft_error_ms']:.3f} ms" for r in scores),'L4: main and four control models; A10: main only; A10G: main and four controls; H100: complete main-model cells only.',['consolidated_scorecard in outputs/consolidated_results.jsonl','figures/paper/frozen-scorecard.pdf','docs/PHASE3_REPORT.md#frozen-prediction-scorecard'],'Coverage differs across boards. H100 is partial. Unresolved paired intervals are excluded from decision accuracy.')
    errors=sorted([r for r in d['phase3'] if r['kind']=='phase3_prediction_score'],key=lambda r:r['absolute_error_ms'],reverse=True)[:3]
    add('Short calibration does not reliably extrapolate TTFT to the largest native contexts.','strong','; '.join(f"{display(r['gpu'])}, {short(r['model'])}, L={r['prefix_tokens']}, N={r['turn_tokens']}, {r['condition']}: predicted {r['predicted_ttft_ms']:.3f} vs observed {r['observed_ttft_ms']:.3f} ms, absolute error {r['absolute_error_ms']:.3f} ms" for r in errors),'Observed Qwen2.5-3B native-limit extrapolation on L4 and A10G.',['phase3_prediction_score sorted by absolute_error_ms','docs/PHASE3_REPORT.md#frozen-prediction-scorecard'],'Median errors conceal these tails; a low median cannot justify universal long-context prediction.')
    add('Exact proportional scaling of crossover bandwidth with prefill throughput is not established.','not supported','; '.join(f"{display(r['gpu'])}: {r['compatible_any']}/{r['resolved']} ratio-resolved shapes compatible with at least one matched T4 bracket; {r['unresolved']} not ratio-resolved" for r in d['hypotheses']),'Five transfer models where complete simulated-rate shapes and matched T4 observations exist.',['consolidated_hypothesis_score','figures/paper/bstar-vs-prefill.pdf','docs/PHASE3_REPORT.md#crossover-bandwidth-and-the-throughput-hypothesis'],'Compatibility is a broad-bracket test using frozen calibration throughput, not an equality test. Fixed overhead, new-turn cost and extrapolation error matter.')
    matched=[r for r in d['crossovers'] if r['model']==MAIN and r['workload']=='ultrachat' and r['prefix_tokens']==1024 and r['turn_tokens']==32]
    add('At a matched main-model context, the faster GPU allocations shift crossover bandwidth upward.','supported','; '.join(f"{display(r['gpu'])} / {r['run_id']}: {label(r['measured'])} MB/s; prefill {r['measured_prefill_tokens_s']:.1f} tokens/s" for r in matched),'Qwen2.5-1.5B, UltraChat, L=1024, N=32; T4, L4, A10, A10G, H100.',['consolidated_crossovers.csv','figures/paper/bstar-vs-gpu.pdf'],'Only adjacent simulated-rate brackets or censored bounds are observed; host and driver also change. This is an allocation comparison, not isolated GPU causality.')
    regimes=[r for r in d['short_regimes'] if r['turn_tokens']==32]
    add('L4 extends the sampled short-context recompute-favored regime relative to T4.','supported','; '.join(f"{display(r['gpu'])} / {r['run_id']}: recompute {r['recompute_wins']}, reload {r['reload_wins']}, unresolved {r['unresolved']}" for r in regimes),'Qwen2.5-1.5B UltraChat, prefixes 16, 64, 128, 256, new turn 32; real unthrottled pinned path.',['phase3_short_regime','figures/paper/short-context-regime.pdf'],'No continuous crossover length is identified. A10 and A10G have separate allocations and boundaries.')
    spread=[]
    for gpu,kind,field in [('T4','session_spread','relative_range'),('L4','phase3_session_spread','range_over_median')]:
        source=rows if gpu=='T4' else d['phase3']
        for turn in [32,256]:
            vals=[r[field] for r in source if r['kind']==kind and (gpu=='T4' or r.get('gpu')==gpu) and r['condition']=='recompute' and r['turn_tokens']==turn]
            spread.append(f"{gpu}, N={turn}: median {100*median(vals):.3f}%, maximum {100*max(vals):.3f}%")
    paired=[r for r in d['phase3'] if r['kind']=='phase3_summary' and r['gpu']=='L4' and r['purpose']=='sweep' and r['model']==MAIN and r['prefix_tokens']==8192 and r['turn_tokens']==32 and r['condition']=='recompute']
    example='; '.join(f"{r['run_id']}: {r['median']:.3f} ms, within-session 95% CI [{r['ci95'][0]:.3f}, {r['ci95'][1]:.3f}]" for r in paired)
    add('Session variability remains larger than some within-session intervals.','supported','; '.join(spread)+'; L4 example L=8192, N=32: '+example,'Main UltraChat model; three T4 sessions and two L4 sessions, all measured lengths, recompute.',['session_spread + phase3_session_spread','docs/PHASE3_REPORT.md#session-spread-and-clock-drift'],'Range over median is descriptive; small session counts do not estimate a population confidence interval.')
    allocations=[r for r in d['phase3'] if r['kind']=='phase3_allocation_spread' and r['condition']=='recompute']
    add('The earlier A10 service-tier spread compares different boards and PCIe widths.','limited','A10: PCIe 4 x16, one main session; A10G: PCIe 4 x8, one main session; '+ '; '.join(f"N={turn}: median matched-cell relative range {100*median([r['range_over_median'] for r in allocations if r['turn_tokens']==turn]):.3f}%" for turn in [32,256]),'Matched Qwen2.5-1.5B UltraChat cells on A10 and A10G.',['consolidated_allocation_spread','outputs/phase3_ledger.json','docs/PHASE3_REPORT.md#session-spread-and-clock-drift'],'This service-tier difference is confounded by board, host and link changes. No cause is identified, and each board has only one main session.')
    for phase in ['phase2','phase3']:
        selected=[r for r in d['file_observability'] if r['phase']==phase];n=sum(r['samples'] for r in selected);positive=sum(r['positive'] for r in selected)
        add('Kaggle file counters report physical reads.' if phase=='phase2' else 'Modal file counters do not report physical reads.', 'strong' if phase=='phase2' else 'limited',f"{positive}/{n} recorded file observations have positive physical_read_bytes; byte-counter range {min(r['minimum_bytes'] for r in selected)} to {max(r['maximum_bytes'] for r in selected)}.",('Kaggle T4, all recorded phase-two file measurements and microbenchmarks, including calibration.' if phase=='phase2' else 'L4, A10, A10G, and the recovered H100 observations; file measurements and microbenchmarks.'),['consolidated_file_observability','docs/FILE_API_AUDIT.md'],('These are process I/O counters, not physical-device traces. Page-cache-only interpretation is contradicted; underlying device and host cache remain unidentified.' if phase=='phase2' else 'Use local file API path (physical reads not observed). Page-cache residency is one interpretation of zero counters; the cache layer is unverified.'))
    add('MHA file-path outcomes do not transfer uniformly from T4 to A10G.','supported','; '.join(f"{display(r['gpu'])}, {short(r['model'])}, {r['condition']}: {r['wins']}/{r['resolved']} reload wins, {r['unresolved']} unresolved" for r in d['file_wins'] if r['comparison']=='matched prefix and turn'),'Pythia-1.4B and Phi-2 repeated text; matched prefixes 64, 256, 512, 1024, new turn 32; T4, L4 and A10G. A10 x16 has no MHA sweep.',['outputs/consolidated_file_wins.csv','docs/FILE_API_AUDIT.md','docs/PHASE3_REPORT.md#real-file-paths-and-short-contexts'],'Phi-2 already has direct-file wins on T4, so a blanket claim that all MHA file paths lose there is false. Host file paths and read-counter behavior differ, so changes cannot be attributed to GPU speed alone. No MHA performance claim is available for A10 x16 or H100.')
    e=totals['file_errors'];add('Including deserialization improves the descriptive torch-file rule residual on T4.','supported',f"Torch median absolute relative error {100*e['torch']['old_median_ape']:.3f}% to {100*e['torch']['new_median_ape']:.3f}%; raw-format error {100*e['raw']['old_median_ape']:.3f}% to {100*e['raw']['new_median_ape']:.3f}%.",'T4, seven models, full observed file cells; independently measured CPU legs and same-session baselines.',['phase2_report_totals.file_errors','docs/PHASE2_REPORT.md'],'The raw path barely changes. This is descriptive residual analysis, not frozen cross-GPU validation.')
    h=next(r for r in d['scorecards'] if r['gpu']=='H100!');missing=[r for r in rows if r['kind']=='phase3_missing_prediction_cell' and r['gpu']=='H100!'];hs=[r for r in d['crossovers'] if r['gpu']=='H100!']
    add('The H100 point is incomplete and cannot validate the full fast-GPU or MHA hypothesis.','limited',f"{h['complete_cells']} complete timing cells; {len(missing)} unfinished registered cells; complete main-model prefixes {sorted(r['prefix_tokens'] for r in hs)}; Pythia sweep timings 0.",'One H100 allocation; Qwen2.5-1.5B UltraChat complete cells only.',['phase3_audit + phase3_missing_prediction_cell','outputs/phase3_dropped_cells.json','docs/PHASE3_REPORT.md'],'Provider cancellation signal; initiating actor unknown; no second allocation. Partial cells are retained but excluded from scoring.')
    anomaly=[r for r in rows if r['kind']=='prefill_anomaly_pair'];npositive=sum(r['prefix_minus_prefix_plus_turn_ms']['ci95'][0]>0 for r in anomaly)
    add('The pilot prefill reversal has no established cause and did not repeat as a resolved reversal.','limited',f"{npositive}/{len(anomaly)} phase-two anomaly comparisons have a positive prefix-only-minus-prefix-plus-turn interval lower endpoint.",'Qwen2.5-1.5B at prefix 8192 on repeated text and UltraChat; observed turn sizes.',['prefill_anomaly_pair','docs/PHASE2_REPORT.md'],'Non-reproduction does not identify the historical cause.')
    production=[r for r in rows if r['kind']=='production_status'];successful=sum(r.get('valid') is True for r in production)
    add('Production-serving, concurrency, quantization and P100 conclusions are not supported.','not supported',f"Successful recorded production-status observations: {successful}; accepted full sweep timings use concurrency {sorted({r['concurrency'] for r in rows if r['kind']=='measurement' and r['valid']})}; dtypes {sorted({r['dtype'] for r in rows if r['kind']=='measurement' and r['valid']})}.",'Reference Hugging Face path only; allocated T4, L4, A10, A10G and partial H100.',['production_status + measurement.environment','docs/NOTES.md'],'No measured vLLM/LMCache speedup, P100 transfer, multi-request scaling, 4-bit model comparison or bf16 claim.')
    add('A novelty claim for the basic reload-versus-recompute idea is not supported.','not supported','No novelty claim is made for KV reuse, cache offload or choosing compute versus load.','Novelty boundary, not a measured performance effect.',['docs/RELATED_WORK.md'],'The permissible angle is this bounded older/commodity-GPU experiment, the calibrated rule and its measured transfer limits.')
    return cs


def claims_markdown(cs):
    lines=['# Claims supported by the data release','','This is the complete claim inventory for paper planning, not a paper draft. Strength labels apply only to the stated scope. '
           '`strong` means directly established by the archived observations; `supported` means an empirical pattern with stated caveats; '
           '`limited` means sparse, confounded or incomplete evidence; `not supported` rejects a broader conclusion.','','All numeric evidence is generated from `outputs/results.jsonl.gz`. '
           '`python3 scripts/consolidate_study.py --check` verifies this file and its evidence tables from that archive without GPU work. '
           'Historical preregistrations remain unchanged; observed A10 and A10G results are never pooled here. '
           'The [coverage table](../outputs/consolidated_coverage.csv) enumerates exact complete prefixes, turns, models, workloads and sessions for each phase and observed board. '
           'Each claim below further restricts that coverage. File-counter counts separately include calibration and partial records.','']
    for c in cs:
        lines.extend([f"{c['id']}. **{c['title']}** Strength: **{c['strength']}**.",'',
          '   Supporting evidence: '+c['numbers'],'',
          '   Source: '+', '.join(f'[{s}]({"../" if s.startswith(("outputs/","figures/")) else "../" if s.startswith("docs/") else "../outputs/claims_evidence.json"}{s if s.startswith(("outputs/","figures/","docs/")) else ""})' for s in c['sources'])+'.','',
          '   Scope: '+c['scope'],'','   Limit: '+c['caveat'],''])
    return '\n'.join(lines)


def tables(d):
    out={}
    def csvtable(name,fields,rows):
        stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader()
        for r in rows:writer.writerow({k:r.get(k) for k in fields})
        out['outputs/'+name]=stream.getvalue()
    csvtable('consolidated_scorecard.csv',['gpu','hardware','scope','correct_decisions','resolved_decisions','unresolved_decisions','complete_cells','median_absolute_ttft_error_ms','median_absolute_relative_ttft_error'],[dict(r,hardware=display(r['gpu'])) for r in d['scorecards']])
    csvtable('consolidated_file_observability.csv',['phase','kind','condition','samples','positive','zero','minimum_bytes','maximum_bytes','median_physical_to_file_ratio','min_prefix','max_prefix'],d['file_observability'])
    csvtable('consolidated_coverage.csv',['phase','gpu','hardware','model','workload','turn_tokens','prefixes','sessions'],d['coverage'])
    csvtable('consolidated_file_wins.csv',['gpu','model','condition','comparison','wins','resolved','unresolved','prefixes','turns'],d['file_wins'])
    csvtable('consolidated_crossovers.csv',['gpu','hardware','run_id','model','workload','prefix_tokens','turn_tokens','prediction_kind','predicted_bstar_mb_s','measured_prefill_tokens_s','observed'],[dict(r,hardware=display(r['gpu']),observed=label(r['measured'])) for r in d['crossovers']])
    return out


def file_doc(d):
    lines=['# Local file API observability','','The Modal tier is the **local file API path (physical reads not observed)**. '
      'Physical reads were not observed. Page-cache residency is one interpretation of the zero process counters; the cache layer is unverified. '
      'Kaggle uses the **local file API path (positive process physical-read counters; underlying storage and host cache unidentified)**. '
      'Applying the Modal parenthetical to Kaggle would contradict the recorded counters. Neither platform identifies a physical device or establishes a storage-device benchmark.','',
      'Counts below include every recorded file observation, including calibration and the recovered partial H100 run. '
      'They describe I/O accounting and do not turn incomplete timings into scored cells.','',
      '| Phase | Record kind | Path | Positive / observations | Counter range, bytes | Median physical-read / file-byte ratio |',
      '| --- | --- | --- | --- | --- | --- |']
    for r in d['file_observability']:
        ratio=f"{r['median_physical_to_file_ratio']:.6f}" if r['median_physical_to_file_ratio'] is not None else 'Not recorded'
        lines.append(f"| {r['phase']} | {r['kind']} | {r['condition']} | {r['positive']} / {r['samples']} | {r['minimum_bytes']} to {r['maximum_bytes']} | {ratio} |")
    lines.extend(['','Global cache dropping was denied on Kaggle. Per-file eviction advice is advisory on both platforms. '
       'Positive Kaggle process counters support reads beyond the kernel page cache; they do not identify device media or rule out host/storage caches. '
       'The zero Modal counters and virtualized filesystem prevent the same conclusion there. No cached-versus-uncached ablation was performed.','',
       '| GPU / PCIe width | Model | Path | Comparison scope | Reload wins / resolved | Unresolved | Prefixes | New turns |',
       '| --- | --- | --- | --- | --- | --- | --- | --- |'])
    for r in d['file_wins']:lines.append(f"| {display(r['gpu'])} | {short(r['model'])} | {r['condition']} | {r['comparison']} | {r['wins']} / {r['resolved']} | {r['unresolved']} | {r['prefixes']} | {r['turns']} |")
    lines.extend(['','A10 at PCIe x16 has no MHA sweep. The MHA Modal controls ran on A10G at PCIe x8. '
      'The comparison has different short-length grids and new-turn coverage across phases; it is not a matched factorial storage experiment. '
      'Sources: `consolidated_file_observability.csv`, `consolidated_file_wins.csv` and their underlying canonical records.',''])
    return '\n'.join(lines)


def captions():
    return '''# Figure caption drafts

All panels use fp16, one inference request, the Hugging Face reference path and pre-existing cache contents. Paced rates are simulated bandwidth. Error bars show achieved-rate bracket endpoints, not confidence intervals for a fitted threshold. The measured per-cell paired bootstrap intervals determine whether a bracket endpoint is resolved.

1. **Break-even bandwidth by observed GPU.** Qwen2.5-1.5B on frozen UltraChat at matched prefixes, with a new turn of 32 tokens. Each marker retains its session. Filled markers have resolved bracket endpoints; crosses have an unresolved endpoint. Triangles are censored median bounds. Hollow squares show the frozen calibration-only threshold on new hardware and the descriptive same-session rule on T4. The plotted point within a bracket is an inverse-bandwidth interpolation, not a directly measured threshold. Missing H100 panels are unmeasured or incomplete. A10 at PCIe x16 and A10G at x8 remain separate. Source: `outputs/consolidated_crossovers.csv`. Files: [PDF](../figures/paper/bstar-vs-gpu.pdf), [PNG](../figures/paper/bstar-vs-gpu.png).

2. **Frozen prediction decisions and TTFT error by observed board.** Correct decisions divided by paired-interval-resolved decisions; unresolved decisions are listed and excluded from accuracy. Median absolute TTFT error includes baselines and reload conditions. Coverage differs: A10 x16 has the main model only; A10G x8 includes the main model and controls. H100 includes only complete recovered main-model cells. T4 had no comparable preregistered new-hardware test and is omitted. Counts are descriptive, correlated cells, not independent Bernoulli trials. Source: `outputs/consolidated_scorecard.csv`. Files: [PDF](../figures/paper/frozen-scorecard.pdf), [PNG](../figures/paper/frozen-scorecard.png).

3. **Short-context decisions across allocations.** Main-model UltraChat returning-turn TTFT compares full recompute with the real unthrottled chunked pinned-copy path at common prefixes. Each row is a separate session. Colors use the archived paired-round bootstrap interval: recompute, reload, or unresolved. White cells are unmeasured. The two new-turn lengths are separate panels. A10 x16 and A10G x8 are different boards and links, so their difference is not within-board session spread. Source: `phase3_short_regime` and `outputs/consolidated_results.jsonl`. Files: [PDF](../figures/paper/short-context-regime.pdf), [PNG](../figures/paper/short-context-regime.png).

4. **Break-even bandwidth versus measured prefix-only throughput.** Five models compare T4 with L4, separate A10 x16 and A10G x8 allocations, and the partial H100 main-model point; all panels use a 32-token new turn. Vertical bars span adjacent achieved simulated rates. Filled circles require resolved endpoint decisions; crosses indicate median-only brackets. Triangles indicate censoring. Dashed curves are frozen TTFT-adjusted predictions, without refitting; the dotted line is KV bytes/token times prefix throughput. T4 observations are descriptive historical comparisons. A large gap to the unthrottled endpoint limits threshold precision, and model families differ in kernels and size. H100 provides no MHA sweep result. Source: `outputs/consolidated_crossovers.csv` and the immutable prediction manifests. Files: [PDF](../figures/paper/bstar-vs-prefill.pdf), [PNG](../figures/paper/bstar-vs-prefill.png).
'''


def savefig(fig,name):
    folder=ROOT/'figures/paper';folder.mkdir(exist_ok=True)
    fig.savefig(folder/(name+'.pdf'),bbox_inches='tight',metadata={'CreationDate':None,'ModDate':None})
    fig.savefig(folder/(name+'.png'),dpi=300,bbox_inches='tight')


def figures(d):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.colors import ListedColormap,BoundaryNorm
    from matplotlib.ticker import ScalarFormatter,LogLocator,NullFormatter
    plt.rcParams.update({'font.size':9,'axes.titlesize':10,'axes.labelsize':9,'legend.fontsize':8,'pdf.fonttype':42,'ps.fonttype':42,'savefig.facecolor':'white'})
    boards=list(COLORS)
    main=[r for r in d['crossovers'] if r['model']==MAIN and r['workload']=='ultrachat' and r['turn_tokens']==32]
    fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained',sharey=True)
    for ax,L in zip(axes.flat,[256,1024,8192,16384]):
        for j,gpu in enumerate(boards):
            group=[r for r in main if r['gpu']==gpu and r['prefix_tokens']==L]
            if not group:ax.text(j,70,'No complete\ncell',ha='center',fontsize=7,color='#666666')
            for i,r in enumerate(group):
                x=j+(i-(len(group)-1)/2)*.13;obs=r['measured'];color=COLORS[gpu]
                for b in obs.get('brackets',[]):
                    lo,hi=sorted(b['achieved_mb_s']);y=b['interpolated_mb_s']
                    ax.errorbar(x,y,yerr=[[y-lo],[hi-y]],fmt='o' if b['paired_ci_resolved'] else 'x',color=color,ms=4,lw=.8)
                if obs['status']=='recompute_faster_at_all_tested_simulated_rates':ax.scatter(x,obs['largest_achieved_mb_s'],marker='^',facecolors='none',edgecolors=color,s=30)
                if obs['status']=='reload_faster_at_all_tested_simulated_rates':
                    point=min(r['points'],key=lambda p:p['target_mb_s'] if p['target_mb_s'] is not None else float('inf'));ax.scatter(x,point['achieved_mb_s'],marker='v',facecolors='none',edgecolors=color,s=30)
                if r['predicted_bstar_mb_s'] is not None:ax.scatter(x+.035,r['predicted_bstar_mb_s'],marker='s',facecolors='none',edgecolors=color,s=25)
        ax.set_title(f'Prefix {L} tokens');ax.set_yscale('log');ax.set_ylim(35,90000);ax.set_xlim(-.4,4.4);ax.set_xticks(range(5),['T4','L4','A10\nx16','A10G\nx8','H100']);ax.set_ylabel('Break-even bandwidth (MB/s)');ax.grid(axis='y',alpha=.2)
    handles=[Line2D([],[],marker='o',color='black',ls='',label='Resolved observed bracket'),Line2D([],[],marker='x',color='black',ls='',label='Median-only bracket'),Line2D([],[],marker='^',markerfacecolor='none',color='black',ls='',label='Censored bound'),Line2D([],[],marker='s',markerfacecolor='none',color='black',ls='',label='Rule prediction (T4 descriptive)')]
    fig.legend(handles=handles,loc='outside lower center',ncol=2);savefig(fig,'bstar-vs-gpu');plt.close(fig)
    cards=d['scorecards'];fig,axes=plt.subplots(1,2,figsize=(9,3.6),layout='constrained');xs=list(range(len(cards)));labels=[r['gpu'].rstrip('!')+(' x16' if r['gpu']=='A10' else ' x8' if r['gpu']=='A10G' else '') for r in cards]
    bars=axes[0].bar(xs,[100*r['correct_decisions']/r['resolved_decisions'] for r in cards],color=[COLORS[r['gpu']] for r in cards]);axes[0].set_ylim(0,112);axes[0].set_ylabel('Correct resolved decisions (%)');axes[0].set_title('Frozen decisions')
    for bar,r in zip(bars,cards):axes[0].text(bar.get_x()+bar.get_width()/2,bar.get_height()+2,f"{r['correct_decisions']}/{r['resolved_decisions']}\n{r['unresolved_decisions']} unresolved",ha='center',fontsize=8)
    axes[1].bar(xs,[r['median_absolute_ttft_error_ms'] for r in cards],color=[COLORS[r['gpu']] for r in cards]);axes[1].set_ylabel('Median absolute TTFT error (ms)');axes[1].set_title('All complete timed conditions')
    for i,r in enumerate(cards):axes[1].text(i,r['median_absolute_ttft_error_ms']+.08,f"{r['median_absolute_ttft_error_ms']:.2f}",ha='center',fontsize=8)
    for ax in axes:ax.set_xticks(xs,labels);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    savefig(fig,'frozen-scorecard');plt.close(fig)
    regimes=d['short_regimes'];sessions=sorted({(r['gpu'],r['run_id']) for r in regimes if r['gpu']!='H100!'},key=lambda x:(boards.index(x[0]),x[1]));lengths=[16,64,128,256]
    cmap=ListedColormap(['#eeeeee','#d55e00','#0072b2','#aaaaaa']);norm=BoundaryNorm([-.5,.5,1.5,2.5,3.5],4)
    fig,axes=plt.subplots(1,2,figsize=(10,4.5),layout='constrained',sharey=True)
    import numpy as np
    for ax,N in zip(axes,[32,256]):
        arr=np.zeros((len(sessions),len(lengths)))
        for i,(gpu,run) in enumerate(sessions):
            r=next((r for r in regimes if r['run_id']==run and r['turn_tokens']==N),None)
            if not r:continue
            for j,L in enumerate(lengths):arr[i,j]=1 if L in r['recompute_wins'] else 2 if L in r['reload_wins'] else 3 if L in r['unresolved'] else 0
        ax.pcolormesh(np.arange(len(lengths)+1)-.5,np.arange(len(sessions)+1)-.5,arr,cmap=cmap,norm=norm,shading='flat');ax.set_ylim(len(sessions)-.5,-.5);ax.set_xticks(range(len(lengths)),lengths);ax.set_xlabel('Prefix tokens');ax.set_title(f'New turn {N} tokens');ax.set_yticks(range(len(sessions)),[display(gpu)+' / '+run.split('session-')[-1] if gpu=='T4' else display(gpu)+' / '+run.rsplit('-',1)[-1] for gpu,run in sessions]);ax.set_xticks(np.arange(-.5,len(lengths),1),minor=True);ax.set_yticks(np.arange(-.5,len(sessions),1),minor=True);ax.grid(which='minor',color='white',lw=2);ax.tick_params(which='minor',bottom=False,left=False)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=c,label=l) for c,l in [('#d55e00','Recompute wins'),('#0072b2','Reload wins'),('#aaaaaa','Unresolved'),('#eeeeee','Unmeasured')]],loc='outside lower center',ncol=4);savefig(fig,'short-context-regime');plt.close(fig)
    # Reuse the historical plot's observations, now split by actual board and rendered to both formats.
    import report_phase3
    original=[r for r in load_archive()[0] if r.get('phase')=='phase2' and r['kind']=='bandwidth_crossover']
    report_phase3.figure([r for r in d['crossovers'] if r['gpu']!='T4'],original)
    import shutil
    for extension in ['pdf','png']:shutil.copyfile(ROOT/'figures'/('phase3_bstar_vs_prefill.'+extension),ROOT/'figures/paper'/('bstar-vs-prefill.'+extension))


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--figures',action='store_true');args=p.parse_args()
    rows,base=load_archive();d=derive(rows);cs=claims(rows,d)
    evidence=dict(scorecards=d['scorecards'],file_observability=d['file_observability'],file_wins=d['file_wins'],hypothesis_scorecards=d['hypotheses'],kv_bytes_per_token=d['configs'],short_regimes=d['short_regimes'],coverage=d['coverage'])
    for kind in ['pilot_bstar','phase2_report_totals','heldout_session_score','prefill_anomaly_pair']:
        evidence[kind]=[r for r in rows if r['kind']==kind]
    evidence['pilot_ttft_summaries']=[{k:r[k] for k in ['prefix_tokens','turn_tokens','condition','median','ci95','n']} for r in rows if r['kind']=='summary' and r.get('measurement_kind')=='ttft']
    evidence['largest_frozen_errors']=sorted([r for r in d['phase3'] if r['kind']=='phase3_prediction_score'],key=lambda r:r['absolute_error_ms'],reverse=True)[:3]
    outputs=tables(d);outputs.update({'docs/CLAIMS.md':claims_markdown(cs),'outputs/claims_evidence.json':dump(dict(source='outputs/results.jsonl.gz',base_records_sha256=sha(base),claims=cs,evidence=evidence)),
      'docs/FILE_API_AUDIT.md':file_doc(d),'docs/FIGURE_CAPTIONS.md':captions()})
    records=[]
    for key,kind in [('scorecards','consolidated_scorecard'),('file_observability','consolidated_file_observability'),('file_wins','consolidated_file_wins'),('hypotheses','consolidated_hypothesis_score'),('coverage','consolidated_coverage')]:
        records.extend(dict(r,phase='consolidation',source_phase=r.get('phase'),kind=kind) for r in d[key])
    records.extend(dict(r,phase='consolidation',kind='consolidated_allocation_spread') for r in d['phase3'] if r['kind']=='phase3_allocation_spread')
    records.append(dict(phase='consolidation',kind='claim_inventory',base_records_sha256=sha(base),claims=cs))
    outputs['outputs/consolidated_results.jsonl']=''.join(json.dumps(r,allow_nan=False,separators=(',',':'))+'\n' for r in records)
    if args.check:
        differences=[path for path,text in outputs.items() if not (ROOT/path).exists() or (ROOT/path).read_text()!=text]
        archived=[r for r in [json.loads(l) for l in gzip.decompress((ROOT/'outputs/results.jsonl.gz').read_bytes()).splitlines()] if r.get('phase')=='consolidation']
        if archived!=records:differences.append('canonical consolidation records')
        assert not differences,'Archive reconstruction differs: '+', '.join(differences)
        print(dump(dict(verified=True,claims=len(cs),generated_text_artifacts=len(outputs),base_records_sha256=sha(base))))
    else:
        for path,text in outputs.items():(ROOT/path).write_text(text)
        (ROOT/'outputs/results.jsonl').write_bytes(base+outputs['outputs/consolidated_results.jsonl'].encode())
        print(f'Generated {len(cs)} scoped claims from canonical records; repack before --check')
    if args.figures:figures(d)


if __name__=='__main__':main()
