"""Write interview notes and a complete index of the draft's numerical uses."""
from pathlib import Path
import json,re,subprocess
P=Path(__file__).resolve().parents[1];R=P.parent
n=json.loads((P/'generated/number_registry.json').read_text());a=json.loads((P/'generated/number_audit.json').read_text())
brief='''# Interview briefing

This explains the draft rather than adding results. The only experimental evidence is v0.1.0-data and its claim inventory. The motivation placeholder is for the author; it is not an invented personal account.

## The explanation to give first

A saved conversation cache can save prefix computation, but bringing it back and continuing the turn also costs time. Compare the complete time until the next first token, not just bytes divided by bandwidth. A short local calibration predicts most resolved decisions on the measured allocations. It fails in important cases, and this is a measurement study rather than a new serving system.

The four contributions are the released reference measurements, the complete TTFT accounting rule, frozen prediction checks on new allocations, and concrete operator-facing limits. None claims to invent KV reuse, offload, break-even thresholds, or compute-versus-load scheduling. py-kvcache is especially close prior work; Cake already overlaps compute and load.

## Introduction

The operator is serving small models and must choose what to do when a conversation returns. The experiment assumes a saved cache already exists. It does not decide whether creating or retaining that cache was worthwhile: persistence also needs write costs, capacity and return probability. This distinction prevents turning a conditional latency result into an unevaluated cache-admission policy.

The title's “across commodity GPUs” means locally calibrated tests on the observed allocations. It does not mean a T4-only fit predicts arbitrary hardware with no new-hardware calibration. A10 and A10G are separately observed names, links and workloads.

## The decision rule

`KV_bytes` is the full prefix payload. `T_recompute` includes the prefix and new turn through first-token selection. `T_GPU_hit` is the returning-turn latency with the old cache already on the GPU. The difference is the time budget available to pay fixed overhead, transfer, and CPU work.

`B*` is the bandwidth that just spends that saving budget. For a positive denominator, faster effective transfer favors reload. A nonpositive denominator predicts no finite threshold under this model; it is not a theorem about every implementation. Near zero, tiny baseline errors move B* greatly, so unresolved decisions should remain unresolved.

Read, deserialization and H2D movement must be counted once. If the bandwidth term represents H2D, file CPU work goes into the other legs. If a different transfer leg supplies the bandwidth term, H2D belongs among the other legs. Mixing the staged-read CPU path with direct torch loading gives the wrong decomposition.

The prefix-only formula removes the returning-turn baseline and fixed costs. It can underprice reuse. Descriptive T4 agreement checks that accounting; the frozen transfer test additionally asks whether the baselines can be predicted from short calibration. These are different tests and must never share an accuracy label.

## Setup

The pilot established feasibility and found lower reload medians at its sampled contexts, but did not locate a crossover length. The redesign therefore swept simulated bandwidth and added short prefixes, model families, file-leg measurements and separate sessions. The later phase calibrated each new GPU allocation, committed predictions, and only then ran the sweep.

Weights and caches are fp16. The main model uses frozen synthetic UltraChat; long inputs may stitch conversations. The other model comparisons use repeated text. These inputs isolate timings; they do not measure conversation quality or a real distribution of return events. The full coverage table shows missing native limits and budget reductions.

The measured endpoint is a first token available to the host. Cache creation, packing, pinning, writes, tokenization, input-ID placement and request queueing are outside this return-time measurement. A reference copy must actually be consumed by the resumed transformer and checked against a resident continuation and recomputed first token. Otherwise a fast copy could be meaningless.

The rate limiter simulates blocking bandwidth. It does not emulate a real device, network tail latency or an asynchronous pipeline. Target and achieved rates differ and are both retained. Allocation participates in the pacing budget, which is why an additive fixed-cost approximation can miss short contexts.

Paired rounds compare conditions on the same round. A resolved decision means the paired bootstrap interval for path-minus-recompute excludes zero. A cell with an interval covering zero is not silently declared a win or loss. Correct/resolved counts exclude it. They are correlated cells, not a binomial experiment. The TTFT-error median includes baselines too, so its denominator differs from decision accuracy.

Within-session CIs describe repeated timing rounds. Session spread describes different session medians. A narrow CI does not imply that another allocation will reproduce that median. Telemetry is sampled too sparsely to explain every short trial and cannot establish thermal causality.

Kaggle file reads were physical according to positive process counters. This does not identify the media or rule out host/storage caches. Modal's were page-cache resident, with physical reads not observed; this is the operational interpretation of zero virtualized counters, not a cache-eviction ablation. Do not call the two platforms an equal physical-file-read comparison.

## Frozen-transfer headline and Figure 1

Figure 1 reports per-board correct/resolved decisions and median absolute TTFT error. A10 has the main model only; A10G and L4 include auxiliary controls. H100 has only complete recovered main-model cells. Unequal coverage means the bars are not a fair ranking of GPU prediction difficulty.

Calibration did not time the combined real reload or simulated-bandwidth TTFT conditions. Later paths test whether independent baselines and cost legs compose. A good score therefore supports local calibration, but it does not isolate baseline-fit quality from overhead approximation or allocation variation. The appendix separates anchors, interpolation, extrapolation and sessions.

## Bandwidth shifts and Figure 2

Figure 2 compares the main model at matched prefix lengths and a fixed new turn. Each session keeps its own point. The vertical bars are adjacent achieved simulated-rate endpoints, not CIs for an exactly measured B*. Points inside them are harmonic interpolation, not an extra benchmark. Crosses have an unresolved endpoint. A triangle is only a bound.

The directional claim is supported at the matched context in the paper. Faster allocations shift the useful reload boundary upward. CPU, driver, and link differences prevent assigning the entire shift causally to GPU compute. The H100 short-context threshold is censored rather than a known finite value. Blank panels reflect missing or incomplete observations.

## Returning-turn costs

The stronger descriptive agreement of the adjusted T4 rule does not establish out-of-sample hardware prediction. The small Qwen example shows why KV bytes alone do not determine the answer: continuation and fixed work consume much of the recompute-saving budget. The separate held-out T4 checks hold the first session's calibration fixed, but still use the same model, text and GPU type.

## Short contexts and Figure 3

The matrix compares the real unthrottled chunked pinned path with fresh recomputation. Orange is resolved recompute, blue is resolved reload, and gray is unresolved. Rows are sessions, not shuffled repeats. The turn-length panels are separate.

L4 extends the sampled recompute-favored region compared with T4. This is not a universal assertion that every faster board extends it equally. A10 and A10G differ at the boundary, and turn size changes the saving budget. No continuous crossover length can be inferred from this sparse prefix grid.

## Supporting observations

The selected MHA controls have larger KV payloads and higher simulated crossover brackets than selected GQA controls at the stated matched T4 shape. They are different models with different widths, parameter counts and kernels. Never say the experiment isolates the causal benefit of GQA.

Adding the deserialization leg improves the torch-file residual on T4, but barely changes the raw-format residual. This is an accounting correction for a particular CPU path, not evidence that every file format becomes faster or that the corrected rule was independently frozen there.

The former Ampere “session spread” compares A10 at x16 with A10G at x8. Allocation differences are its likely source, with host and board effects confounded. In particular, do not claim that halving PCIe width causes the observed recompute slowdown: fresh prefill is not a bulk H2D-transfer benchmark. There is only one main session per observed Ampere board.

## What fails and Figure 4

Long native-context errors are real failures of the short calibration's time-shape extrapolation. Median error can look small while that tail is poor. Do not generalize those extrapolations from the aggregate score.

Figure 4 uses the same released observations and predictions, reflowed for readable single-column print. The dotted prefix-only line is an accounting identity using KV bytes/token and throughput. The test is whether observed independent crossovers support the frozen throughput-ratio expectation. Broad bracket compatibility does not establish exact equality, and a censored threshold does not produce an exact ratio. Frozen-fit uncertainty was not propagated.

The MHA file outcome is not uniform across T4, L4 and A10G. Phi-2 already has direct-file wins on T4, so “MHA always loses on T4” would be wrong. Matched-prefix comparisons in CLAIMS.md prevent confusing changed turn coverage with a hardware effect. Different physical-read conditions remain another confound.

The pilot anomaly did not recur as a resolved reversal, but no historical cause was identified. A warmup, clock, or implementation explanation would be speculation. Say unexplained, not fixed.

## Practical guidance

The one-minute box is a proposed calibration checklist, not a runtime SLA or a new evaluated system. The actual released calibration function times provide its scale but do not guarantee this recipe's duration. Load and warm the intended model, measure representative recompute/resident baselines and independent legs, apply the positive-denominator rule, then validate close decisions in paired rounds. Native-limit extrapolation and unknown file cache state are reasons to stop trusting the quick estimate.

An engine builder must repeat the measurements on the engine's critical path. Overlap, batching, preallocation, compression and scheduler-aware prefetch can change it. Cake splits compute and load; our study did not test that overlap and cannot claim to beat it.

## Related work

LMCache, vLLM and HiCache already supply KV reuse and offload mechanisms. CacheGen changes the bytes/quality trade-off with compression; CacheBlend addresses cached-chunk fusion. Cake overlaps compute and load. py-kvcache already studies hardware-dependent break-even behavior and external fetching. The storage-observability paper explains hidden buffered reads; KVServe and ShadowServe add service adaptation and interference concerns.

The bibliography uses verified arXiv revisions and official documentation. It does not invent conference venues, publication dates, or named authors for living documentation. CITATIONS.md records the title discrepancy in the file-observability reference and the exact versions used.

## Limitations and conclusion

The H100 run is partial; its Pythia calibration is not a completed Pythia sweep. Missing cells remain missing. P100, quantization, bf16, concurrency scaling, serving throughput and production LMCache/vLLM performance are not supported. No application-quality or natural-return-distribution result is present. Small session counts and unpropagated fit uncertainty restrict prediction confidence.

The conclusion is conditional: local TTFT accounting predicts most resolved decisions in the measured scope. It is not a universal cache policy. Keep unresolved outcomes, measure the whole path, and recalibrate after changes.

## Appendix and reproduction

The coverage table gives complete cells only, with all prefixes and turns rather than a balanced-grid implication. Model abbreviations refer back to full checkpoint IDs. The scorecard table separates A10 and A10G and reports different calibration regions and sessions. The reproduction commands rebuild released statistics on CPU; they do not launch GPU jobs. Standard pdfLaTeX/BibTeX builds the manuscript. No submission or posting is part of this draft task.

## Numerical defense index

Every source-mapped number or compound table cell used by the paper appears below. The entries include all table prefix lists and per-board scorecard values, not only the headline. NUMBERS.md gives exact release selectors and every TeX location; generated/number_audit.json records the machine audit. Identifier digits, bibliography metadata and layout settings are separately classified in NUMBERS.md.

| Key | Printed value | How to explain it | Claim |
| --- | --- | --- | --- |
'''
base={
 'ModelCount':'Count of measured model configurations, not equal coverage across models.',
 'T4Timings':'Accepted full-sweep timing observations, not independent conversations.',
 'T4Invalid':'Invalid full-sweep observations; this does not erase failed setup/calibration attempts.',
 'T4Sessions':'Full sweep sessions across all T4 models; not all main-model repeats.',
 'AdjustedCorrect':'Same-session descriptive adjusted-rule agreements.',
 'PrefixCorrect':'Same-session descriptive prefix-only rule agreements.',
 'T4Resolved':'Resolved simulated-rate comparisons for the descriptive rule test.',
 'KaggleReads':'Positive process physical-read counter observations on Kaggle.',
 'KaggleFileSamples':'All counted Kaggle phase-two file observations, including calibration and microbenchmarks.',
 'ModalReads':'Positive physical-read counter observations in the virtualized Modal paths.',
 'ModalFileSamples':'All counted Modal file observations, including the recovered partial run.',
 'HalfPrefix':'Prefix-only B* in MB/s for the small Qwen example.',
 'HalfAdjusted':'Adjusted B* in MB/s for that same example; the continuation budget changes the decision.',
 'H100Missing':'Registered H100 cells unfinished or unstarted, not timing failures imputed as losses.',
 'CalA10Seconds':'Observed calibration function wall seconds on A10, not a recipe-duration guarantee.',
 'CalL4Seconds':'Observed calibration function wall seconds on L4, not a recipe-duration guarantee.',
 'Bootstraps':'Bootstrap resampling count, not a number of additional GPU runs.',
 'CI':'Within-session nominal percentile coverage; not deployment-population coverage.',
 'PilotRepeats':'Measured pilot repeats per cell, distinct from later full sweeps.',
 'FullRepeats':'Measured full-sweep rounds per condition, not independent sessions.',
 'AnomalyPairs':'Interleaved phase-two anomaly comparisons.',
 'AnomalyReversals':'Anomaly comparisons with a resolved positive reversal; zero does not prove a historical cause.',
 'AmpereGeneration':'Observed active PCIe generation on the Ampere allocations, not a GPU performance score.'}
for key in sorted(a['uses']):
 r=n[key];explanation=base.get(key)
 if key.startswith('Cov'):
  explanation='Exact completed coverage cell: '+r['selector']+'. Prefix lists are tokens; session counts are separate allocations.'
 elif key.startswith('Score'):
  col=int(key.rsplit('Col',1)[1]);meaning={2:'correct/resolved decisions',3:'unresolved decisions',4:'complete timed cells',5:'median absolute TTFT error in ms'}[col];explanation='Appendix board/region/session '+meaning+'; '+r['selector']+'.'
 elif key.startswith('KV'):explanation='Verified fp16 KV bytes per token for '+r['selector'].split('kv_bytes_per_token.')[-1]+'.'
 elif 'Extrap' in key:explanation='Native-limit baseline prediction/observation/error in ms. These values expose a failure of extrapolation, not an optimized serving comparison.'
 elif 'Spread' in key:explanation='Median across matched lengths of the relative range of session medians, in percent. Ampere entries compare different boards/links.'
 elif 'Ratio' in key:explanation='Frozen throughput-ratio compatibility count over ratio-resolved shapes; it is neither an exact-equality estimate nor independent trials.'
 elif key.endswith(('Correct','Resolved','Unresolved','Cells','MAE')) and not explanation:explanation='Frozen per-board '+('median absolute TTFT error in ms' if key.endswith('MAE') else 'decision or complete-cell count')+'. Coverage differs across boards; keep the denominator and unresolved count visible.'
 elif 'Error' in key:explanation='Descriptive T4 file-rule median absolute relative error in percent; old/new refer to omitting/including deserialization.'
 elif key.endswith(('Low','High')):explanation='Achieved simulated-bandwidth bracket endpoint in MB/s at the stated matched repeated-text shape; it is not a physical-device bandwidth.'
 elif key.startswith('Rate') or key=='Rates':explanation='Target simulated bandwidth in decimal MB/s; use achieved-rate brackets for observations.'
 elif key in ['MainGrid','ShortGrid','MhaGrid']:explanation='Exact token-length list for the stated scope; do not interpolate missing contexts as measurements.'
 elif key.endswith('Bytes'):explanation='Range endpoint of process physical-read byte counters, not an identified device capacity or media speed.'
 elif not explanation:explanation='Released token length or protocol setting for the scope indicated in NUMBERS.md: '+r['selector']+'.'
 brief+='| '+key+' | '+r['rendered'].replace('|','/')+' | '+explanation.replace('|','/')+' | '+str(r['claim'])+' |\n'
(P/'BRIEFING.md').write_text(brief)
print('Wrote section/figure explanations and',len(a['uses']),'numerical defense entries')
