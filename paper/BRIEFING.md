# Interview briefing

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
| A10Correct | 192 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| A10GCorrect | 398 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| A10GExtrapError | 5,873.459 | Native-limit baseline prediction/observation/error in ms. These values expose a failure of extrapolation, not an optimized serving comparison. | 10 |
| A10GExtrapObs | 13,914.555 | Native-limit baseline prediction/observation/error in ms. These values expose a failure of extrapolation, not an optimized serving comparison. | 10 |
| A10GExtrapPred | 8,041.096 | Native-limit baseline prediction/observation/error in ms. These values expose a failure of extrapolation, not an optimized serving comparison. | 10 |
| A10GMAE | 5.758 | Frozen per-board median absolute TTFT error in ms. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| A10GRatioTotal | 24 | Frozen throughput-ratio compatibility count over ratio-resolved shapes; it is neither an exact-equality estimate nor independent trials. | 11 |
| A10GRatioYes | 20 | Frozen throughput-ratio compatibility count over ratio-resolved shapes; it is neither an exact-equality estimate nor independent trials. | 11 |
| A10GResolved | 426 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| A10GUnresolved | 3 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| A10MAE | 2.040 | Frozen per-board median absolute TTFT error in ms. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| A10RatioTotal | 12 | Frozen throughput-ratio compatibility count over ratio-resolved shapes; it is neither an exact-equality estimate nor independent trials. | 11 |
| A10RatioYes | 11 | Frozen throughput-ratio compatibility count over ratio-resolved shapes; it is neither an exact-equality estimate nor independent trials. | 11 |
| A10Resolved | 206 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| A10Unresolved | 14 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| AdjustedCorrect | 1,237 | Same-session descriptive adjusted-rule agreements. | 5 |
| AmpereGeneration | 4 | Observed active PCIe generation on the Ampere allocations, not a GPU performance score. | 15 |
| AmpereSpreadLong | 22.664 | Median across matched lengths of the relative range of session medians, in percent. Ampere entries compare different boards/links. | 15 |
| AmpereSpreadShort | 23.611 | Median across matched lengths of the relative range of session medians, in percent. Ampere entries compare different boards/links. | 15 |
| AnomalyPairs | 4 | Interleaved phase-two anomaly comparisons. | 21 |
| Bootstraps | 10,000 | Bootstrap resampling count, not a number of additional GPU runs. | 3 |
| Boundary | 256 | Released token length or protocol setting for the scope indicated in NUMBERS.md: prefix or new-turn length present in coverage. | 3 |
| CI | 95 | Within-session nominal percentile coverage; not deployment-population coverage. | 3 |
| CalA10Seconds | 42.5 | Observed calibration function wall seconds on A10, not a recipe-duration guarantee. | 9 |
| CalL4Seconds | 63.4 | Observed calibration function wall seconds on L4, not a recipe-duration guarantee. | 9 |
| CalRepeats | 3 | Released token length or protocol setting for the scope indicated in NUMBERS.md: released measurement protocol / referenced canonical analysis metadata. | 3 |
| Cov0Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 1,792 | Exact completed coverage cell: row 0.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov0Sessions | 1 | Exact completed coverage cell: row 0.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov0Turn | 32 | Exact completed coverage cell: row 0.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov10Prefixes | 16, 32, 64, 128, 256, 512, 1,024 | Exact completed coverage cell: row 10.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov10Sessions | 1 | Exact completed coverage cell: row 10.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov10Turn | 256 | Exact completed coverage cell: row 10.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov11Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 1,792 | Exact completed coverage cell: row 11.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov11Sessions | 1 | Exact completed coverage cell: row 11.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov11Turn | 32 | Exact completed coverage cell: row 11.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov12Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 1,792 | Exact completed coverage cell: row 12.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov12Sessions | 1 | Exact completed coverage cell: row 12.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov12Turn | 256 | Exact completed coverage cell: row 12.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov13Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | Exact completed coverage cell: row 13.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov13Sessions | 1 | Exact completed coverage cell: row 13.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov13Turn | 32 | Exact completed coverage cell: row 13.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov14Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | Exact completed coverage cell: row 14.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov14Sessions | 1 | Exact completed coverage cell: row 14.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov14Turn | 256 | Exact completed coverage cell: row 14.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov15Prefixes | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | Exact completed coverage cell: row 15.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov15Sessions | 1 | Exact completed coverage cell: row 15.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov15Turn | 32 | Exact completed coverage cell: row 15.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov16Prefixes | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | Exact completed coverage cell: row 16.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov16Sessions | 1 | Exact completed coverage cell: row 16.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov16Turn | 256 | Exact completed coverage cell: row 16.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov17Prefixes | 64, 256, 512, 1,024, 2,016 | Exact completed coverage cell: row 17.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov17Sessions | 1 | Exact completed coverage cell: row 17.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov17Turn | 32 | Exact completed coverage cell: row 17.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov18Prefixes | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | Exact completed coverage cell: row 18.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov18Sessions | 1 | Exact completed coverage cell: row 18.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov18Turn | 32 | Exact completed coverage cell: row 18.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov19Prefixes | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | Exact completed coverage cell: row 19.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov19Sessions | 1 | Exact completed coverage cell: row 19.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov19Turn | 256 | Exact completed coverage cell: row 19.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov1Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 1,792 | Exact completed coverage cell: row 1.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov1Sessions | 1 | Exact completed coverage cell: row 1.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov1Turn | 256 | Exact completed coverage cell: row 1.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov20Prefixes | 64, 256, 512, 1,024, 32,736 | Exact completed coverage cell: row 20.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov20Sessions | 1 | Exact completed coverage cell: row 20.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov20Turn | 32 | Exact completed coverage cell: row 20.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov21Prefixes | 64, 256, 512, 1,024, 2,016 | Exact completed coverage cell: row 21.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov21Sessions | 1 | Exact completed coverage cell: row 21.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov21Turn | 32 | Exact completed coverage cell: row 21.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov22Prefixes | 64, 256, 512, 1,024 | Exact completed coverage cell: row 22.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov22Sessions | 1 | Exact completed coverage cell: row 22.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov22Turn | 32 | Exact completed coverage cell: row 22.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov23Prefixes | 1,024, 16,384 | Exact completed coverage cell: row 23.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov23Sessions | 1 | Exact completed coverage cell: row 23.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov23Turn | 32 | Exact completed coverage cell: row 23.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov24Prefixes | 64, 256, 512, 1,024, 2,016 | Exact completed coverage cell: row 24.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov24Sessions | 1 | Exact completed coverage cell: row 24.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov24Turn | 32 | Exact completed coverage cell: row 24.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov25Prefixes | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | Exact completed coverage cell: row 25.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov25Sessions | 2 | Exact completed coverage cell: row 25.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov25Turn | 32 | Exact completed coverage cell: row 25.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov26Prefixes | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | Exact completed coverage cell: row 26.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov26Sessions | 2 | Exact completed coverage cell: row 26.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov26Turn | 256 | Exact completed coverage cell: row 26.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov27Prefixes | 64, 256, 512, 1,024, 32,736 | Exact completed coverage cell: row 27.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov27Sessions | 1 | Exact completed coverage cell: row 27.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov27Turn | 32 | Exact completed coverage cell: row 27.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov28Prefixes | 64, 256, 512, 1,024, 2,016 | Exact completed coverage cell: row 28.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov28Sessions | 1 | Exact completed coverage cell: row 28.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov28Turn | 32 | Exact completed coverage cell: row 28.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov29Prefixes | 64, 256, 512, 1,024 | Exact completed coverage cell: row 29.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov29Sessions | 1 | Exact completed coverage cell: row 29.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov29Turn | 32 | Exact completed coverage cell: row 29.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov2Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192 | Exact completed coverage cell: row 2.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov2Sessions | 1 | Exact completed coverage cell: row 2.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov2Turn | 32 | Exact completed coverage cell: row 2.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov30Prefixes | 512, 2,048, 8,192 | Exact completed coverage cell: row 30.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov30Sessions | 1 | Exact completed coverage cell: row 30.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov30Turn | 32 | Exact completed coverage cell: row 30.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov31Prefixes | 512, 2,048, 8,192 | Exact completed coverage cell: row 31.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov31Sessions | 1 | Exact completed coverage cell: row 31.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov31Turn | 256 | Exact completed coverage cell: row 31.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov3Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192 | Exact completed coverage cell: row 3.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov3Sessions | 1 | Exact completed coverage cell: row 3.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov3Turn | 256 | Exact completed coverage cell: row 3.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov4Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 1,792, 2,048, 8,192 | Exact completed coverage cell: row 4.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov4Sessions | 1 | Exact completed coverage cell: row 4.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov4Turn | 32 | Exact completed coverage cell: row 4.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov5Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | Exact completed coverage cell: row 5.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov5Sessions | 3 | Exact completed coverage cell: row 5.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov5Turn | 32 | Exact completed coverage cell: row 5.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov6Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | Exact completed coverage cell: row 6.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov6Sessions | 3 | Exact completed coverage cell: row 6.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov6Turn | 256 | Exact completed coverage cell: row 6.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov7Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | Exact completed coverage cell: row 7.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov7Sessions | 1 | Exact completed coverage cell: row 7.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov7Turn | 32 | Exact completed coverage cell: row 7.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov8Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | Exact completed coverage cell: row 8.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov8Sessions | 1 | Exact completed coverage cell: row 8.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov8Turn | 256 | Exact completed coverage cell: row 8.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov9Prefixes | 16, 32, 64, 128, 256, 512, 1,024 | Exact completed coverage cell: row 9.prefixes. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov9Sessions | 1 | Exact completed coverage cell: row 9.sessions. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Cov9Turn | 32 | Exact completed coverage cell: row 9.turn_tokens. Prefix lists are tokens; session counts are separate allocations. | 3 |
| Example | 512 | Released token length or protocol setting for the scope indicated in NUMBERS.md: prefix or new-turn length present in coverage. | 3 |
| ExtrapLength | 32,736 | Native-limit baseline prediction/observation/error in ms. These values expose a failure of extrapolation, not an optimized serving comparison. | 3 |
| FullRepeats | 10 | Measured full-sweep rounds per condition, not independent sessions. | 3 |
| H100Cells | 26 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| H100Correct | 20 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| H100Missing | 52 | Registered H100 cells unfinished or unstarted, not timing failures imputed as losses. | 20 |
| H100RatioTotal | 1 | Frozen throughput-ratio compatibility count over ratio-resolved shapes; it is neither an exact-equality estimate nor independent trials. | 11 |
| H100RatioYes | 0 | Frozen throughput-ratio compatibility count over ratio-resolved shapes; it is neither an exact-equality estimate nor independent trials. | 11 |
| H100Resolved | 21 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| H100Unresolved | 1 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| HalfAdjusted | 2,442.265 | Adjusted B* in MB/s for that same example; the continuation budget changes the decision. | 6 |
| HalfPrefix | 226.626 | Prefix-only B* in MB/s for the small Qwen example. | 6 |
| KV0 | 12,288 | Verified fp16 KV bytes per token for Qwen/Qwen2.5-0.5B. | 4 |
| KV1 | 28,672 | Verified fp16 KV bytes per token for Qwen/Qwen2.5-1.5B. | 4 |
| KV2 | 36,864 | Verified fp16 KV bytes per token for Qwen/Qwen2.5-3B. | 4 |
| KV3 | 196,608 | Verified fp16 KV bytes per token for EleutherAI/pythia-1.4b. | 4 |
| KV4 | 196,608 | Verified fp16 KV bytes per token for facebook/opt-1.3b. | 4 |
| KV5 | 327,680 | Verified fp16 KV bytes per token for microsoft/phi-2. | 4 |
| KV6 | 114,688 | Verified fp16 KV bytes per token for unsloth/Llama-3.2-3B-Instruct. | 4 |
| KaggleFileSamples | 7,762 | All counted Kaggle phase-two file observations, including calibration and microbenchmarks. | 16 |
| KaggleMaxBytes | 1,879,052,288 | Range endpoint of process physical-read byte counters, not an identified device capacity or media speed. | 16 |
| KaggleMinBytes | 196,608 | Range endpoint of process physical-read byte counters, not an identified device capacity or media speed. | 16 |
| KaggleReads | 7,762 | Positive process physical-read counter observations on Kaggle. | 16 |
| L4Correct | 574 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| L4ExtrapError | 4,934.542 | Native-limit baseline prediction/observation/error in ms. These values expose a failure of extrapolation, not an optimized serving comparison. | 10 |
| L4ExtrapObs | 18,022.902 | Native-limit baseline prediction/observation/error in ms. These values expose a failure of extrapolation, not an optimized serving comparison. | 10 |
| L4ExtrapPred | 13,088.360 | Native-limit baseline prediction/observation/error in ms. These values expose a failure of extrapolation, not an optimized serving comparison. | 10 |
| L4MAE | 3.203 | Frozen per-board median absolute TTFT error in ms. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| L4RatioTotal | 27 | Frozen throughput-ratio compatibility count over ratio-resolved shapes; it is neither an exact-equality estimate nor independent trials. | 11 |
| L4RatioYes | 25 | Frozen throughput-ratio compatibility count over ratio-resolved shapes; it is neither an exact-equality estimate nor independent trials. | 11 |
| L4Resolved | 636 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| L4SpreadLong | 4.417 | Median across matched lengths of the relative range of session medians, in percent. Ampere entries compare different boards/links. | 14 |
| L4SpreadShort | 4.956 | Median across matched lengths of the relative range of session medians, in percent. Ampere entries compare different boards/links. | 14 |
| L4Unresolved | 13 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 9 |
| Long | 256 | Released token length or protocol setting for the scope indicated in NUMBERS.md: prefix or new-turn length present in coverage. | 3 |
| LongPrefix | 8,192 | Released token length or protocol setting for the scope indicated in NUMBERS.md: prefix or new-turn length present in coverage. | 3 |
| MainGrid | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | Exact token-length list for the stated scope; do not interpolate missing contexts as measurements. | 3 |
| Matched | 1,024 | Released token length or protocol setting for the scope indicated in NUMBERS.md: prefix or new-turn length present in coverage. | 3 |
| MaxMain | 16,384 | Released token length or protocol setting for the scope indicated in NUMBERS.md: prefix or new-turn length present in coverage. | 3 |
| MhaGrid | 64, 256, 512, 1,024 | Exact token-length list for the stated scope; do not interpolate missing contexts as measurements. | 18 |
| MicroRepeats | 5 | Released token length or protocol setting for the scope indicated in NUMBERS.md: released measurement protocol / referenced canonical analysis metadata. | 3 |
| ModalFileSamples | 4,575 | All counted Modal file observations, including the recovered partial run. | 17 |
| ModalReads | 0 | Positive physical-read counter observations in the virtualized Modal paths. | 17 |
| ModelCount | 7 | Count of measured model configurations, not equal coverage across models. | 3 |
| PhiHigh | 1598.4 | Achieved simulated-bandwidth bracket endpoint in MB/s at the stated matched repeated-text shape; it is not a physical-device bandwidth. | 7 |
| PhiLow | 799.2 | Achieved simulated-bandwidth bracket endpoint in MB/s at the stated matched repeated-text shape; it is not a physical-device bandwidth. | 7 |
| PilotMid | 2,048 | Released token length or protocol setting for the scope indicated in NUMBERS.md: pilot prefixes. | 1 |
| PilotRepeats | 12 | Measured pilot repeats per cell, distinct from later full sweeps. | 1 |
| PrefixCorrect | 1,017 | Same-session descriptive prefix-only rule agreements. | 5 |
| PythiaHigh | 1597.2 | Achieved simulated-bandwidth bracket endpoint in MB/s at the stated matched repeated-text shape; it is not a physical-device bandwidth. | 7 |
| PythiaLow | 798.9 | Achieved simulated-bandwidth bracket endpoint in MB/s at the stated matched repeated-text shape; it is not a physical-device bandwidth. | 7 |
| QwenMainHigh | 398.4 | Achieved simulated-bandwidth bracket endpoint in MB/s at the stated matched repeated-text shape; it is not a physical-device bandwidth. | 7 |
| QwenMainLow | 199.5 | Achieved simulated-bandwidth bracket endpoint in MB/s at the stated matched repeated-text shape; it is not a physical-device bandwidth. | 7 |
| QwenThreeHigh | 199.7 | Achieved simulated-bandwidth bracket endpoint in MB/s at the stated matched repeated-text shape; it is not a physical-device bandwidth. | 7 |
| QwenThreeLow | 99.9 | Achieved simulated-bandwidth bracket endpoint in MB/s at the stated matched repeated-text shape; it is not a physical-device bandwidth. | 7 |
| Rate100 | 100 | Target simulated bandwidth in decimal MB/s; use achieved-rate brackets for observations. | 12 |
| Rate1600 | 1,600 | Target simulated bandwidth in decimal MB/s; use achieved-rate brackets for observations. | 12 |
| Rate200 | 200 | Target simulated bandwidth in decimal MB/s; use achieved-rate brackets for observations. | 12 |
| Rate400 | 400 | Target simulated bandwidth in decimal MB/s; use achieved-rate brackets for observations. | 12 |
| Rate800 | 800 | Target simulated bandwidth in decimal MB/s; use achieved-rate brackets for observations. | 12 |
| Rates | 50, 100, 200, 400, 800, 1,600 | Target simulated bandwidth in decimal MB/s; use achieved-rate brackets for observations. | 3 |
| RawNewError | 3.086 | Descriptive T4 file-rule median absolute relative error in percent; old/new refer to omitting/including deserialization. | 19 |
| RawOldError | 3.107 | Descriptive T4 file-rule median absolute relative error in percent; old/new refer to omitting/including deserialization. | 19 |
| Score12Col2 | 574 / 636 | Appendix board/region/session correct/resolved decisions; scorecard table line 13, column 3. | 9 |
| Score12Col3 | 13 | Appendix board/region/session unresolved decisions; scorecard table line 13, column 4. | 9 |
| Score12Col4 | 767 | Appendix board/region/session complete timed cells; scorecard table line 13, column 5. | 9 |
| Score12Col5 | 3.203 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 13, column 6. | 9 |
| Score13Col2 | 246 / 248 | Appendix board/region/session correct/resolved decisions; scorecard table line 14, column 3. | 9 |
| Score13Col3 | 5 | Appendix board/region/session unresolved decisions; scorecard table line 14, column 4. | 9 |
| Score13Col4 | 299 | Appendix board/region/session complete timed cells; scorecard table line 14, column 5. | 9 |
| Score13Col5 | 2.822 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 14, column 6. | 9 |
| Score14Col2 | 231 / 289 | Appendix board/region/session correct/resolved decisions; scorecard table line 15, column 3. | 9 |
| Score14Col3 | 8 | Appendix board/region/session unresolved decisions; scorecard table line 15, column 4. | 9 |
| Score14Col4 | 351 | Appendix board/region/session complete timed cells; scorecard table line 15, column 5. | 9 |
| Score14Col5 | 2.981 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 15, column 6. | 9 |
| Score15Col2 | 97 / 99 | Appendix board/region/session correct/resolved decisions; scorecard table line 16, column 3. | 9 |
| Score15Col3 | 0 | Appendix board/region/session unresolved decisions; scorecard table line 16, column 4. | 9 |
| Score15Col4 | 117 | Appendix board/region/session complete timed cells; scorecard table line 16, column 5. | 9 |
| Score15Col5 | 4.007 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 16, column 6. | 9 |
| Score16Col2 | 193 / 201 | Appendix board/region/session correct/resolved decisions; scorecard table line 17, column 3. | 9 |
| Score16Col3 | 8 | Appendix board/region/session unresolved decisions; scorecard table line 17, column 4. | 9 |
| Score16Col4 | 247 | Appendix board/region/session complete timed cells; scorecard table line 17, column 5. | 9 |
| Score16Col5 | 1.506 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 17, column 6. | 9 |
| Score17Col2 | 188 / 216 | Appendix board/region/session correct/resolved decisions; scorecard table line 18, column 3. | 9 |
| Score17Col3 | 4 | Appendix board/region/session unresolved decisions; scorecard table line 18, column 4. | 9 |
| Score17Col4 | 260 | Appendix board/region/session complete timed cells; scorecard table line 18, column 5. | 9 |
| Score17Col5 | 3.681 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 18, column 6. | 9 |
| Score18Col2 | 193 / 219 | Appendix board/region/session correct/resolved decisions; scorecard table line 19, column 3. | 9 |
| Score18Col3 | 1 | Appendix board/region/session unresolved decisions; scorecard table line 19, column 4. | 9 |
| Score18Col4 | 260 | Appendix board/region/session complete timed cells; scorecard table line 19, column 5. | 9 |
| Score18Col5 | 3.654 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 19, column 6. | 9 |
| Score19Col2 | 192 / 206 | Appendix board/region/session correct/resolved decisions; scorecard table line 20, column 3. | 9 |
| Score19Col3 | 14 | Appendix board/region/session unresolved decisions; scorecard table line 20, column 4. | 9 |
| Score19Col4 | 260 | Appendix board/region/session complete timed cells; scorecard table line 20, column 5. | 9 |
| Score19Col5 | 2.040 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 20, column 6. | 9 |
| Score20Col2 | 59 / 63 | Appendix board/region/session correct/resolved decisions; scorecard table line 21, column 3. | 9 |
| Score20Col3 | 3 | Appendix board/region/session unresolved decisions; scorecard table line 21, column 4. | 9 |
| Score20Col4 | 78 | Appendix board/region/session complete timed cells; scorecard table line 21, column 5. | 9 |
| Score20Col5 | 2.275 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 21, column 6. | 9 |
| Score21Col2 | 96 / 105 | Appendix board/region/session correct/resolved decisions; scorecard table line 22, column 3. | 9 |
| Score21Col3 | 5 | Appendix board/region/session unresolved decisions; scorecard table line 22, column 4. | 9 |
| Score21Col4 | 130 | Appendix board/region/session complete timed cells; scorecard table line 22, column 5. | 9 |
| Score21Col5 | 2.308 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 22, column 6. | 9 |
| Score22Col2 | 37 / 38 | Appendix board/region/session correct/resolved decisions; scorecard table line 23, column 3. | 9 |
| Score22Col3 | 6 | Appendix board/region/session unresolved decisions; scorecard table line 23, column 4. | 9 |
| Score22Col4 | 52 | Appendix board/region/session complete timed cells; scorecard table line 23, column 5. | 9 |
| Score22Col5 | 1.341 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 23, column 6. | 9 |
| Score23Col2 | 192 / 206 | Appendix board/region/session correct/resolved decisions; scorecard table line 24, column 3. | 9 |
| Score23Col3 | 14 | Appendix board/region/session unresolved decisions; scorecard table line 24, column 4. | 9 |
| Score23Col4 | 260 | Appendix board/region/session complete timed cells; scorecard table line 24, column 5. | 9 |
| Score23Col5 | 2.040 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 24, column 6. | 9 |
| Score24Col2 | 398 / 426 | Appendix board/region/session correct/resolved decisions; scorecard table line 25, column 3. | 9 |
| Score24Col3 | 3 | Appendix board/region/session unresolved decisions; scorecard table line 25, column 4. | 9 |
| Score24Col4 | 507 | Appendix board/region/session complete timed cells; scorecard table line 25, column 5. | 9 |
| Score24Col5 | 5.758 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 25, column 6. | 9 |
| Score25Col2 | 178 / 187 | Appendix board/region/session correct/resolved decisions; scorecard table line 26, column 3. | 9 |
| Score25Col3 | 0 | Appendix board/region/session unresolved decisions; scorecard table line 26, column 4. | 9 |
| Score25Col4 | 221 | Appendix board/region/session complete timed cells; scorecard table line 26, column 5. | 9 |
| Score25Col5 | 5.094 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 26, column 6. | 9 |
| Score26Col2 | 170 / 185 | Appendix board/region/session correct/resolved decisions; scorecard table line 27, column 3. | 9 |
| Score26Col3 | 2 | Appendix board/region/session unresolved decisions; scorecard table line 27, column 4. | 9 |
| Score26Col4 | 221 | Appendix board/region/session complete timed cells; scorecard table line 27, column 5. | 9 |
| Score26Col5 | 5.511 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 27, column 6. | 9 |
| Score27Col2 | 50 / 54 | Appendix board/region/session correct/resolved decisions; scorecard table line 28, column 3. | 9 |
| Score27Col3 | 1 | Appendix board/region/session unresolved decisions; scorecard table line 28, column 4. | 9 |
| Score27Col4 | 65 | Appendix board/region/session complete timed cells; scorecard table line 28, column 5. | 9 |
| Score27Col5 | 8.371 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 28, column 6. | 9 |
| Score28Col2 | 193 / 209 | Appendix board/region/session correct/resolved decisions; scorecard table line 29, column 3. | 9 |
| Score28Col3 | 0 | Appendix board/region/session unresolved decisions; scorecard table line 29, column 4. | 9 |
| Score28Col4 | 247 | Appendix board/region/session complete timed cells; scorecard table line 29, column 5. | 9 |
| Score28Col5 | 5.031 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 29, column 6. | 9 |
| Score29Col2 | 205 / 217 | Appendix board/region/session correct/resolved decisions; scorecard table line 30, column 3. | 9 |
| Score29Col3 | 3 | Appendix board/region/session unresolved decisions; scorecard table line 30, column 4. | 9 |
| Score29Col4 | 260 | Appendix board/region/session complete timed cells; scorecard table line 30, column 5. | 9 |
| Score29Col5 | 6.433 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 30, column 6. | 9 |
| Score30Col2 | 20 / 21 | Appendix board/region/session correct/resolved decisions; scorecard table line 31, column 3. | 9 |
| Score30Col3 | 1 | Appendix board/region/session unresolved decisions; scorecard table line 31, column 4. | 9 |
| Score30Col4 | 26 | Appendix board/region/session complete timed cells; scorecard table line 31, column 5. | 9 |
| Score30Col5 | 6.579 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 31, column 6. | 9 |
| Score31Col2 | 11 / 11 | Appendix board/region/session correct/resolved decisions; scorecard table line 32, column 3. | 9 |
| Score31Col3 | 0 | Appendix board/region/session unresolved decisions; scorecard table line 32, column 4. | 9 |
| Score31Col4 | 13 | Appendix board/region/session complete timed cells; scorecard table line 32, column 5. | 9 |
| Score31Col5 | 0.332 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 32, column 6. | 9 |
| Score32Col2 | 9 / 10 | Appendix board/region/session correct/resolved decisions; scorecard table line 33, column 3. | 9 |
| Score32Col3 | 1 | Appendix board/region/session unresolved decisions; scorecard table line 33, column 4. | 9 |
| Score32Col4 | 13 | Appendix board/region/session complete timed cells; scorecard table line 33, column 5. | 9 |
| Score32Col5 | 9.999 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 33, column 6. | 9 |
| Score33Col2 | 20 / 21 | Appendix board/region/session correct/resolved decisions; scorecard table line 34, column 3. | 9 |
| Score33Col3 | 1 | Appendix board/region/session unresolved decisions; scorecard table line 34, column 4. | 9 |
| Score33Col4 | 26 | Appendix board/region/session complete timed cells; scorecard table line 34, column 5. | 9 |
| Score33Col5 | 6.579 | Appendix board/region/session median absolute TTFT error in ms; scorecard table line 34, column 6. | 9 |
| SessionsL4 | 2 | Released token length or protocol setting for the scope indicated in NUMBERS.md: released measurement protocol / referenced canonical analysis metadata. | 3 |
| SessionsT4 | 3 | Released token length or protocol setting for the scope indicated in NUMBERS.md: released measurement protocol / referenced canonical analysis metadata. | 3 |
| Short | 32 | Released token length or protocol setting for the scope indicated in NUMBERS.md: prefix or new-turn length present in coverage. | 3 |
| ShortGrid | 16, 64, 128, 256 | Exact token-length list for the stated scope; do not interpolate missing contexts as measurements. | 13 |
| T4Held2Correct | 148 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 8 |
| T4Held2Resolved | 149 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 8 |
| T4Held3Correct | 146 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 8 |
| T4Held3Resolved | 150 | Frozen per-board decision or complete-cell count. Coverage differs across boards; keep the denominator and unresolved count visible. | 8 |
| T4Invalid | 0 | Invalid full-sweep observations; this does not erase failed setup/calibration attempts. | 3 |
| T4Resolved | 1,258 | Resolved simulated-rate comparisons for the descriptive rule test. | 5 |
| T4Sessions | 10 | Full sweep sessions across all T4 models; not all main-model repeats. | 3 |
| T4SpreadLong | 14.847 | Median across matched lengths of the relative range of session medians, in percent. Ampere entries compare different boards/links. | 14 |
| T4SpreadShort | 12.341 | Median across matched lengths of the relative range of session medians, in percent. Ampere entries compare different boards/links. | 14 |
| T4Timings | 26,040 | Accepted full-sweep timing observations, not independent conversations. | 3 |
| TorchNewError | 3.097 | Descriptive T4 file-rule median absolute relative error in percent; old/new refer to omitting/including deserialization. | 19 |
| TorchOldError | 11.78 | Descriptive T4 file-rule median absolute relative error in percent; old/new refer to omitting/including deserialization. | 19 |
