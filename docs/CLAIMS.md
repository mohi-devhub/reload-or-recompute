# Claims supported by the data release

This is the complete claim inventory for paper planning, not a paper draft. Strength labels apply only to the stated scope. `strong` means directly established by the archived observations; `supported` means an empirical pattern with stated caveats; `limited` means sparse, confounded or incomplete evidence; `not supported` rejects a broader conclusion.

All numeric evidence is generated from `outputs/results.jsonl.gz`. `python3 scripts/consolidate_study.py --check` verifies this file and its evidence tables from that archive without GPU work. Historical preregistrations remain unchanged; observed A10 and A10G results are never pooled here. The [coverage table](../outputs/consolidated_coverage.csv) enumerates exact complete prefixes, turns, models, workloads and sessions for each phase and observed board. Each claim below further restricts that coverage. File-counter counts separately include calibration and partial records.

1. **The pilot found reload faster at every sampled prefix, without locating a crossover length.** Strength: **supported**.

   Supporting evidence: 18/18 reload-path median comparisons favor reload; prefixes 512, 2048, 8192; turns 32 and 256; 12 repeats per cell.

   Source: [summary / measurement_kind=ttft](../outputs/claims_evidence.json), [docs/PILOT_REPORT.md](../docs/PILOT_REPORT.md).

   Scope: Kaggle T4; Qwen2.5-1.5B; repeated text; pinned, pageable and file paths.

   Limit: Median ordering is descriptive; the pilot does not establish a universal crossover length.

2. **The pilot prefix-only bandwidth threshold is measured, not assumed.** Strength: **supported**.

   Supporting evidence: L=512: 178.611 MB/s; L=2048: 172.441 MB/s; L=8192: 124.937 MB/s

   Source: [pilot_bstar](../outputs/claims_evidence.json), [docs/NOTES.md](../docs/NOTES.md).

   Scope: Pilot T4, Qwen2.5-1.5B; prefix-only threshold, independent of later TTFT adjustment.

   Limit: These values do not include returning-turn or fixed costs.

3. **The redesigned T4 data cover seven fp16 models with no invalid accepted sweep timings.** Strength: **strong**.

   Supporting evidence: 26040 accepted timings; 0 invalid; 7 measured model configurations; 10 full sweep sessions.

   Source: [phase2_report_totals](../outputs/claims_evidence.json), [docs/PHASE2_REPORT.md#model-coverage-and-kv-size](../docs/PHASE2_REPORT.md#model-coverage-and-kv-size).

   Scope: T4; prefixes and new-turn coverage are enumerated per run in the phase-two report.

   Limit: Native context and budget exclusions prevent a balanced full grid.

4. **Verified KV size differs substantially across the measured attention layouts.** Strength: **strong**.

   Supporting evidence: pythia-1.4b = 196608 bytes/token; Qwen2.5-0.5B = 12288 bytes/token; Qwen2.5-1.5B = 28672 bytes/token; Qwen2.5-3B = 36864 bytes/token; opt-1.3b = 196608 bytes/token; phi-2 = 327680 bytes/token; Llama-3.2-3B-Instruct = 114688 bytes/token

   Source: [model_config + cache_layout](../outputs/claims_evidence.json), [docs/PHASE2_REPORT.md#model-coverage-and-kv-size](../docs/PHASE2_REPORT.md#model-coverage-and-kv-size).

   Scope: Seven fp16 model configurations on T4; the five transfer models match their cache tensors on Modal.

   Limit: Models also differ in size and kernels; this is not an isolated GQA/MHA architecture intervention.

5. **Adding the resident-turn baseline improves descriptive T4 rule agreement.** Strength: **supported**.

   Supporting evidence: TTFT-adjusted 1237/1258; prefix-only 1017/1258 resolved simulated-rate decisions.

   Source: [phase2_report_totals.rule_counts](../outputs/claims_evidence.json), [docs/PHASE2_REPORT.md#findings](../docs/PHASE2_REPORT.md#findings).

   Scope: T4, seven models and observed lengths; all simulated rates; same-session measured baselines.

   Limit: This is descriptive agreement, not preregistered hardware transfer or independent Bernoulli trials.

6. **Returning-turn and fixed costs can dominate a small KV footprint.** Strength: **supported**.

   Supporting evidence: Qwen2.5-0.5B at L=512, N=32: prefix-only B* 226.626 MB/s; adjusted B* 2442.265 MB/s; observed [1600.0, unthrottled] target / [1558.1, 9531.0] achieved MB/s.

   Source: [bandwidth_crossover](../outputs/claims_evidence.json), [docs/PHASE2_REPORT.md#findings](../docs/PHASE2_REPORT.md#findings).

   Scope: T4, Qwen2.5-0.5B repeated-text control.

   Limit: Use B* = KV_bytes / (T_recompute - T_GPU_hit - fixed_overhead - other_CPU_and_transfer_legs), only for a positive denominator. Count read, deserialization and H2D costs once; the prefix-only formula is insufficient here.

7. **The selected MHA controls require higher simulated bandwidth than the selected GQA controls.** Strength: **supported**.

   Supporting evidence: Qwen2.5-1.5B: [200.0, 400.0] target / [199.5, 398.4] achieved MB/s; Qwen2.5-3B: [100.0, 200.0] target / [99.9, 199.7] achieved MB/s; pythia-1.4b: [800.0, 1600.0] target / [798.9, 1597.2] achieved (median only) MB/s; phi-2: [800.0, 1600.0] target / [799.2, 1598.4] achieved MB/s

   Source: [bandwidth_crossover](../outputs/claims_evidence.json), [docs/PHASE2_REPORT.md#findings](../docs/PHASE2_REPORT.md#findings).

   Scope: T4 repeated text, prefix 512 and new turn 32; Qwen2.5-1.5B/3B versus Pythia-1.4B and Phi-2.

   Limit: Descriptive model comparison. Model size, prefill kernels and cache layout all differ; this does not isolate the causal effect of GQA.

8. **A fixed first-session T4 calibration predicts later main-model sessions reasonably well.** Strength: **supported**.

   Supporting evidence: phase2-main-session-2: 148/149 correct, median relative TTFT error 2.954%; phase2-main-session-3: 146/150 correct, median relative TTFT error 1.714%

   Source: [heldout_session_score](../outputs/claims_evidence.json), [docs/PHASE2_REPORT.md](../docs/PHASE2_REPORT.md).

   Scope: T4; Qwen2.5-1.5B UltraChat; common grid; calibration stays fixed.

   Limit: Same hardware type and input; no claim about unseen GPU types.

9. **Frozen calibration transfers to most resolved cells on each observed board.** Strength: **supported**.

   Supporting evidence: L4 (PCIe 3 x16): 574/636 correct, 13 unresolved, median absolute TTFT error 3.203 ms; A10 (PCIe 4 x16): 192/206 correct, 14 unresolved, median absolute TTFT error 2.040 ms; A10G (PCIe 4 x8): 398/426 correct, 3 unresolved, median absolute TTFT error 5.758 ms; H100 (PCIe 5 x16): 20/21 correct, 1 unresolved, median absolute TTFT error 6.579 ms

   Source: [consolidated_scorecard in outputs/consolidated_results.jsonl](../outputs/claims_evidence.json), [figures/paper/frozen-scorecard.pdf](../figures/paper/frozen-scorecard.pdf), [docs/PHASE3_REPORT.md#frozen-prediction-scorecard](../docs/PHASE3_REPORT.md#frozen-prediction-scorecard).

   Scope: L4: main and four control models; A10: main only; A10G: main and four controls; H100: complete main-model cells only.

   Limit: Coverage differs across boards. H100 is partial. Unresolved paired intervals are excluded from decision accuracy.

10. **Short calibration does not reliably extrapolate TTFT to the largest native contexts.** Strength: **strong**.

   Supporting evidence: A10G (PCIe 4 x8), Qwen2.5-3B, L=32736, N=32, recompute: predicted 8041.096 vs observed 13914.555 ms, absolute error 5873.459 ms; L4 (PCIe 3 x16), Qwen2.5-3B, L=32736, N=32, recompute: predicted 13088.360 vs observed 18022.902 ms, absolute error 4934.542 ms; L4 (PCIe 3 x16), Qwen2.5-3B, L=32736, N=32, prefix_only: predicted 13980.511 vs observed 9148.164 ms, absolute error 4832.347 ms

   Source: [phase3_prediction_score sorted by absolute_error_ms](../outputs/claims_evidence.json), [docs/PHASE3_REPORT.md#frozen-prediction-scorecard](../docs/PHASE3_REPORT.md#frozen-prediction-scorecard).

   Scope: Observed Qwen2.5-3B native-limit extrapolation on L4 and A10G.

   Limit: Median errors conceal these tails; a low median cannot justify universal long-context prediction.

11. **Exact proportional scaling of crossover bandwidth with prefill throughput is not established.** Strength: **not supported**.

   Supporting evidence: L4 (PCIe 3 x16): 25/27 ratio-resolved shapes compatible with at least one matched T4 bracket; 32 not ratio-resolved; A10 (PCIe 4 x16): 11/12 ratio-resolved shapes compatible with at least one matched T4 bracket; 8 not ratio-resolved; A10G (PCIe 4 x8): 20/24 ratio-resolved shapes compatible with at least one matched T4 bracket; 15 not ratio-resolved; H100 (PCIe 5 x16): 0/1 ratio-resolved shapes compatible with at least one matched T4 bracket; 1 not ratio-resolved

   Source: [consolidated_hypothesis_score](../outputs/claims_evidence.json), [figures/paper/bstar-vs-prefill.pdf](../figures/paper/bstar-vs-prefill.pdf), [docs/PHASE3_REPORT.md#crossover-bandwidth-and-the-throughput-hypothesis](../docs/PHASE3_REPORT.md#crossover-bandwidth-and-the-throughput-hypothesis).

   Scope: Five transfer models where complete simulated-rate shapes and matched T4 observations exist.

   Limit: Compatibility is a broad-bracket test using frozen calibration throughput, not an equality test. Fixed overhead, new-turn cost and extrapolation error matter.

12. **At a matched main-model context, the faster GPU allocations shift crossover bandwidth upward.** Strength: **supported**.

   Supporting evidence: T4 / phase2-main-session-1: [100.0, 200.0] target / [100.0, 199.8] achieved MB/s; prefill 5581.6 tokens/s; T4 / phase2-main-session-2: [200.0, 400.0] target / [199.8, 399.0] achieved (median only) MB/s; prefill 6285.1 tokens/s; T4 / phase2-main-session-3: [200.0, 400.0] target / [199.7, 399.0] achieved MB/s; prefill 6469.7 tokens/s; A10 (PCIe 4 x16) / phase3-a10-main-1: [800.0, 1600.0] target / [795.2, 1544.2] achieved MB/s; prefill 18391.1 tokens/s; A10G (PCIe 4 x8) / phase3-a10-main-2: [400.0, 800.0] target / [396.2, 791.0] achieved MB/s; prefill 14178.2 tokens/s; H100 (PCIe 5 x16) / phase3-h100-main: above tested achieved rates (bound only) MB/s; prefill 73677.8 tokens/s; L4 (PCIe 3 x16) / phase3-l4-main-1: [800.0, 1600.0] target / [787.2, 1539.1] achieved MB/s; prefill 15213.0 tokens/s; L4 (PCIe 3 x16) / phase3-l4-main-2: [800.0, 1600.0] target / [788.6, 1552.0] achieved (median only) MB/s; prefill 14438.4 tokens/s

   Source: [consolidated_crossovers.csv](../outputs/claims_evidence.json), [figures/paper/bstar-vs-gpu.pdf](../figures/paper/bstar-vs-gpu.pdf).

   Scope: Qwen2.5-1.5B, UltraChat, L=1024, N=32; T4, L4, A10, A10G, H100.

   Limit: Only adjacent simulated-rate brackets or censored bounds are observed; host and driver also change. This is an allocation comparison, not isolated GPU causality.

13. **L4 extends the sampled short-context recompute-favored regime relative to T4.** Strength: **supported**.

   Supporting evidence: L4 (PCIe 3 x16) / phase3-l4-main-1: recompute [16, 64, 128, 256], reload [], unresolved []; L4 (PCIe 3 x16) / phase3-l4-main-2: recompute [16, 64, 128, 256], reload [], unresolved []; A10 (PCIe 4 x16) / phase3-a10-main-1: recompute [16, 64, 128], reload [], unresolved [256]; A10G (PCIe 4 x8) / phase3-a10-main-2: recompute [16, 64, 128], reload [256], unresolved []; T4 / phase2-main-session-1: recompute [16, 64, 128], reload [256], unresolved []; T4 / phase2-main-session-2: recompute [16, 64, 128], reload [256], unresolved []; T4 / phase2-main-session-3: recompute [16], reload [256], unresolved [64, 128]

   Source: [phase3_short_regime](../outputs/claims_evidence.json), [figures/paper/short-context-regime.pdf](../figures/paper/short-context-regime.pdf).

   Scope: Qwen2.5-1.5B UltraChat, prefixes 16, 64, 128, 256, new turn 32; real unthrottled pinned path.

   Limit: No continuous crossover length is identified. A10 and A10G have separate allocations and boundaries.

14. **Session variability remains larger than some within-session intervals.** Strength: **supported**.

   Supporting evidence: T4, N=32: median 12.341%, maximum 17.332%; T4, N=256: median 14.847%, maximum 20.958%; L4, N=32: median 4.956%, maximum 8.755%; L4, N=256: median 4.417%, maximum 7.338%; L4 example L=8192, N=32: phase3-l4-main-1: 760.407 ms, within-session 95% CI [759.673, 766.897]; phase3-l4-main-2: 814.803 ms, within-session 95% CI [811.700, 820.760]

   Source: [session_spread + phase3_session_spread](../outputs/claims_evidence.json), [docs/PHASE3_REPORT.md#session-spread-and-clock-drift](../docs/PHASE3_REPORT.md#session-spread-and-clock-drift).

   Scope: Main UltraChat model; three T4 sessions and two L4 sessions, all measured lengths, recompute.

   Limit: Range over median is descriptive; small session counts do not estimate a population confidence interval.

15. **The earlier A10 service-tier spread compares different boards and PCIe widths.** Strength: **limited**.

   Supporting evidence: A10: PCIe 4 x16, one main session; A10G: PCIe 4 x8, one main session; N=32: median matched-cell relative range 23.611%; N=256: median matched-cell relative range 22.664%

   Source: [consolidated_allocation_spread](../outputs/claims_evidence.json), [outputs/phase3_ledger.json](../outputs/phase3_ledger.json), [docs/PHASE3_REPORT.md#session-spread-and-clock-drift](../docs/PHASE3_REPORT.md#session-spread-and-clock-drift).

   Scope: Matched Qwen2.5-1.5B UltraChat cells on A10 and A10G.

   Limit: Different board/PCIe allocations are the likely source of this service-tier difference. Causal attribution is unproved; host changes are confounded, and each board has only one main session.

16. **Kaggle file counters report physical reads.** Strength: **strong**.

   Supporting evidence: 7762/7762 recorded file observations have positive physical_read_bytes; byte-counter range 196608 to 1879052288.

   Source: [consolidated_file_observability](../outputs/claims_evidence.json), [docs/FILE_API_AUDIT.md](../docs/FILE_API_AUDIT.md).

   Scope: Kaggle T4, all recorded phase-two file measurements and microbenchmarks, including calibration.

   Limit: These are process I/O counters, not physical-device traces. Page-cache-only interpretation is contradicted; underlying device and host cache remain unidentified.

17. **Modal file counters do not report physical reads.** Strength: **limited**.

   Supporting evidence: 0/4575 recorded file observations have positive physical_read_bytes; byte-counter range 0 to 0.

   Source: [consolidated_file_observability](../outputs/claims_evidence.json), [docs/FILE_API_AUDIT.md](../docs/FILE_API_AUDIT.md).

   Scope: L4, A10, A10G, and the recovered H100 observations; file measurements and microbenchmarks.

   Limit: Use local file API path (page-cache resident; physical reads not observed). Page-cache residency is the operational interpretation of zero counters, not proof of the underlying host storage state.

18. **MHA file-path outcomes do not transfer uniformly from T4 to A10G.** Strength: **supported**.

   Supporting evidence: T4, pythia-1.4b, file_raw_staged: 0/4 reload wins, 0 unresolved; T4, pythia-1.4b, file_torch_direct: 0/4 reload wins, 0 unresolved; T4, phi-2, file_raw_staged: 0/1 reload wins, 3 unresolved; T4, phi-2, file_torch_direct: 2/3 reload wins, 1 unresolved; L4 (PCIe 3 x16), pythia-1.4b, file_raw_staged: 0/4 reload wins, 0 unresolved; L4 (PCIe 3 x16), pythia-1.4b, file_torch_direct: 0/4 reload wins, 0 unresolved; L4 (PCIe 3 x16), phi-2, file_raw_staged: 0/4 reload wins, 0 unresolved; L4 (PCIe 3 x16), phi-2, file_torch_direct: 0/4 reload wins, 0 unresolved; A10G (PCIe 4 x8), pythia-1.4b, file_raw_staged: 0/4 reload wins, 0 unresolved; A10G (PCIe 4 x8), pythia-1.4b, file_torch_direct: 1/4 reload wins, 0 unresolved; A10G (PCIe 4 x8), phi-2, file_raw_staged: 3/4 reload wins, 0 unresolved; A10G (PCIe 4 x8), phi-2, file_torch_direct: 3/4 reload wins, 0 unresolved

   Source: [outputs/consolidated_file_wins.csv](../outputs/consolidated_file_wins.csv), [docs/FILE_API_AUDIT.md](../docs/FILE_API_AUDIT.md), [docs/PHASE3_REPORT.md#real-file-paths-and-short-contexts](../docs/PHASE3_REPORT.md#real-file-paths-and-short-contexts).

   Scope: Pythia-1.4B and Phi-2 repeated text; matched prefixes 64, 256, 512, 1024, new turn 32; T4, L4 and A10G. A10 x16 has no MHA sweep.

   Limit: Phi-2 already has direct-file wins on T4, so a blanket claim that all MHA file paths lose there is false. Host file paths and read-counter behavior differ, so changes cannot be attributed to GPU speed alone. No MHA performance claim is available for A10 x16 or H100.

19. **Including deserialization improves the descriptive torch-file rule residual on T4.** Strength: **supported**.

   Supporting evidence: Torch median absolute relative error 11.780% to 3.097%; raw-format error 3.107% to 3.086%.

   Source: [phase2_report_totals.file_errors](../outputs/claims_evidence.json), [docs/PHASE2_REPORT.md](../docs/PHASE2_REPORT.md).

   Scope: T4, seven models, full observed file cells; independently measured CPU legs and same-session baselines.

   Limit: The raw path barely changes. This is descriptive residual analysis, not frozen cross-GPU validation.

20. **The H100 point is incomplete and cannot validate the full fast-GPU or MHA hypothesis.** Strength: **limited**.

   Supporting evidence: 26 complete timing cells; 52 unfinished registered cells; complete main-model prefixes [1024, 16384]; Pythia sweep timings 0.

   Source: [phase3_audit + phase3_missing_prediction_cell](../outputs/claims_evidence.json), [outputs/phase3_dropped_cells.json](../outputs/phase3_dropped_cells.json), [docs/PHASE3_REPORT.md](../docs/PHASE3_REPORT.md).

   Scope: One H100 allocation; Qwen2.5-1.5B UltraChat complete cells only.

   Limit: Provider cancellation signal; initiating actor unknown; no second allocation. Partial cells are retained but excluded from scoring.

21. **The pilot prefill reversal has no established cause and did not repeat as a resolved reversal.** Strength: **limited**.

   Supporting evidence: 0/4 phase-two anomaly comparisons have a positive prefix-only-minus-prefix-plus-turn interval lower endpoint.

   Source: [prefill_anomaly_pair](../outputs/claims_evidence.json), [docs/PHASE2_REPORT.md](../docs/PHASE2_REPORT.md).

   Scope: Qwen2.5-1.5B at prefix 8192 on repeated text and UltraChat; observed turn sizes.

   Limit: Non-reproduction does not identify the historical cause.

22. **Production-serving, concurrency, quantization and P100 conclusions are not supported.** Strength: **not supported**.

   Supporting evidence: Successful recorded production-status observations: 0; accepted full sweep timings use concurrency [1]; dtypes ['float16'].

   Source: [production_status + measurement.environment](../outputs/claims_evidence.json), [docs/NOTES.md](../docs/NOTES.md).

   Scope: Reference Hugging Face path only; allocated T4, L4, A10, A10G and partial H100.

   Limit: No measured vLLM/LMCache speedup, P100 transfer, multi-request scaling, 4-bit model comparison or bf16 claim.

23. **A novelty claim for the basic reload-versus-recompute idea is not supported.** Strength: **not supported**.

   Supporting evidence: No novelty claim is made for KV reuse, cache offload or choosing compute versus load.

   Source: [docs/RELATED_WORK.md](../docs/RELATED_WORK.md).

   Scope: Novelty boundary, not a measured performance effect.

   Limit: The permissible angle is this bounded older/commodity-GPU experiment, the calibrated rule and its measured transfer limits.
