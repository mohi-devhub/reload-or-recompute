# Phase two: simulated bandwidth crossovers

Redesigned run queue finished.
All bandwidth-sweep rates and crossover intervals below are **simulated transport bandwidth**. They do not measure a physical storage device at those rates.

Accepted full-sweep timing samples: 26040. Invalid full-sweep samples: 0. Conservative phase usage: 9.900916 GPU-hours against the authorized cap of 10. Incomplete sweep sessions: 0. Unsubmitted queued runs: 0.

## Findings

The TTFT-adjusted rule agrees with 1237 of 1258 resolved simulated-rate cells; the prefix-only rule agrees with 1017. These use measured same-session recompute and GPU-hit baselines; the fixed-calibration later-session test below is the separate check of prediction across sessions.

At prefixes 16, 32 with a 32-token new turn, recompute beats the unthrottled chunked-copy control in each varied-dialogue main-model session with resolved paired intervals. The prefix-only bandwidth threshold is insufficient in this regime.

For a 32-token new turn, the median across lengths of the recompute session-range/median ratio is 12.3%, reaching 17.3%. This is observed session spread, not a population confidence interval.

For a 256-token new turn, the median across lengths of the recompute session-range/median ratio is 14.8%, reaching 21.0%. This is observed session spread, not a population confidence interval.

At prefix 512 and new turn 32 on matched repeated text, EleutherAI/pythia-1.4b has simulated crossover [800.0, 1600.0] target / [798.9, 1597.2] achieved (median only) MB/s, versus [200.0, 400.0] target / [199.5, 398.4] achieved MB/s for Qwen/Qwen2.5-1.5B. This model comparison includes prefill-kernel and model-size differences as well as KV layout.

At prefix 512 and new turn 32 on matched repeated text, microsoft/phi-2 has simulated crossover [800.0, 1600.0] target / [799.2, 1598.4] achieved MB/s, versus [100.0, 200.0] target / [99.9, 199.7] achieved MB/s for Qwen/Qwen2.5-3B. This model comparison includes prefill-kernel and model-size differences as well as KV layout.

Small KV footprint alone does not determine the returning-turn decision: Qwen0.5B at prefix 512 and new turn 32 has prefix-only B* 226.6 MB/s, but TTFT-adjusted B* 2442.3 MB/s and observed simulated crossover [1600.0, unthrottled] target / [1558.1, 9531.0] achieved MB/s. Cache continuation and fixed costs matter in this short-context regime.

The pilot's median timing reversal did not reproduce on either text source. Paired intervals distinguish resolved ordering from uncertainty; the historical cause remains unproved. P100 transfer remains untested because the requested allocation returned T4 hardware.

Figures: [main-model TTFT](../figures/phase2-ttft-qwen2.5-1.5b.png), [crossover bandwidth versus length](../figures/phase2-crossover-bandwidth-by-length.png), [predicted versus interpolated crossover](../figures/phase2-predicted-simulated-crossover.png), and [file-rule residuals](../figures/phase2-file-residuals.png).

## What was measured

The reference path uses fp16, one inference request, synchronized wall-clock TTFT through first-token selection, and ten interleaved measured rounds after warmup. Prefix-only prefill is randomized in those rounds. Reload transfers a packed cache in chunks with cumulative rate deadlines. Target and achieved transport bandwidth, sleep time, and bytes are stored separately. All full measurements are retained in the JSONL. Calibration timings have fewer repeats and are excluded from publication summaries. The cache already exists at return time: its initial CPU offload, packing, pinning, and file creation are outside returning-turn TTFT. Tokenization and GPU input-ID placement are also outside timing; this is not serving-API latency. File-read buffer allocation remains inside the staged read leg. CUDA-event intervals include device idle time during host pacing; they are not isolated GPU kernel time.

The primary main-model workload is frozen public UltraChat generated dialogue. Long contexts stitch distinct conversations and are marked accordingly. Three distinct Kaggle kernel sessions use that same frozen input. A separate repeated-text main-model run with a 32-token new turn at the common short lengths and the anomaly length supplies the matched control used for the model-family comparison. The remaining models use that repeated-text control. This is not a human-conversation trace or a quality evaluation.

## Model coverage and KV size

| Model | Family | Verified KV bytes/token | Native total context | Completed sweep sessions |
| --- | --- | --- | --- | --- |
| Qwen/Qwen2.5-0.5B | GQA | 12288 | 32768 | 1 |
| Qwen/Qwen2.5-1.5B | GQA | 28672 | 131072 | 4 |
| Qwen/Qwen2.5-3B | GQA | 36864 | 32768 | 1 |
| EleutherAI/pythia-1.4b | MHA | 196608 | 2048 | 1 |
| facebook/opt-1.3b | MHA | 196608 | 2048 | 1 |
| microsoft/phi-2 | MHA | 327680 | 2048 | 1 |
| unsloth/Llama-3.2-3B-Instruct | GQA | 114688 | 131072 | 1 |
| meta-llama/Llama-3.2-3B | GQA, requested | Unverified: gated access failed | Unmeasured | Unmeasured |

For fp16, `KV bytes/token = 2 × layers × KV heads × head dimension × 2 bytes`; the first factor counts keys and values. This configuration arithmetic must equal the sum of observed tensor bytes. Native context includes the new turn, so the short-context MHA models do not silently run the long-context grid. The extra near-limit prefix leaves room for the longest requested new turn. Environment, revision, shapes, and actual source hashes accompany observations.

| Sweep session | Workload | Prefixes with complete measured cells | New-turn sizes in complete cells |
| --- | --- | --- | --- |
| phase2-main-session-1 | ultrachat | 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384 | 32, 256 |
| phase2-main-session-2 | ultrachat | 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384 | 32, 256 |
| phase2-llama-mirror-control | repeated_control | 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384 | 32, 256 |
| phase2-qwen-3b-control | repeated_control | 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384 | 32, 256 |
| phase2-main-session-3 | ultrachat | 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384 | 32, 256 |
| phase2-main-repeated-control | repeated_control | 16, 32, 64, 128, 256, 512, 1024, 1792, 2048, 8192 | 32 |
| phase2-phi2-control | repeated_control | 16, 32, 64, 128, 256, 512, 1024, 1792 | 32, 256 |
| phase2-pythia-control | repeated_control | 16, 32, 64, 128, 256, 512, 1024, 1792 | 32, 256 |
| phase2-opt-control | repeated_control | 16, 32, 64, 128, 256, 512, 1024 | 32, 256 |
| phase2-qwen-half-control | repeated_control | 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192 | 32, 256 |

Budget coverage reduction in phase2-main-repeated-control: supported requested prefixes omitted [4096, 16384]; requested new-turn sizes omitted [256]. This is separate from native-context exclusions.

Budget coverage reduction in phase2-qwen-half-control: supported requested prefixes omitted [16384]; requested new-turn sizes omitted []. This is separate from native-context exclusions.

OPT also omits the extra near-limit boundary point to prioritize requested grid cells under the phase cap; its completed prefixes are listed above.

## Measured runtime and provenance

| Runtime field | Observed values in accepted measurements |
| --- | --- |
| gpu_names | ["Tesla T4", "Tesla T4"] |
| gpu_count | 2 |
| gpu_query | "Tesla T4, 580.178.04, 15360 MiB\nTesla T4, 580.178.04, 15360 MiB" |
| python | "3.13.16" |
| torch | "2.11.0+cu130" |
| cuda_runtime | "13.0" |
| transformers | "4.51.3" |
| vllm | "not installed" |
| cpu_count | 4 |
| cpu_ram_kb | 32869292; 32869296 |
| free_working_bytes | 20940050432; 20940054528 |
| free_tmp_bytes | 1038081527808; 1038081531904; 1038081536000 |

The runtime table uses the environment inside the timed worker after dependency installation. The startup log also records the pre-install environment. Kaggle allocates two T4 devices per session here; inference uses one, while the conservative ledger charges both.

The [physical-work audit](../outputs/phase2_audit.json) checks byte arithmetic, rate limits, sample uniqueness, actual randomized rounds, fixed model revisions, and matching reference-function source across sweeps; the parent process-budget entry point is excluded from that function hash.

| Fetched run | Saved source matches executed source | Private kernel verified | Saved container image |
| --- | --- | --- | --- |
| calibration-t4 | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |
| calibration-p100 | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |
| main-session-1 | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |
| calibration-mha-fixed | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |
| main-session-2 | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |
| calibration-llama-mirror | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |
| llama-mirror-control | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |
| qwen-3b-control | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |
| main-session-3 | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |
| main-repeated-control | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |
| phi2-control | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |
| pythia-control | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |
| opt-control | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |
| qwen-half-control | True | True | gcr.io/kaggle-private-byod/python@sha256:de153e6d303881930c51286216393d56f56b26458d0661350305a1e8144eea01 |

## Independent bandwidth microbenchmarks

These are measured unthrottled bandwidths, rather than simulated-rate results. File bandwidth includes buffer allocation in the read API leg. The table selects prefix 512; the JSONL contains every measured length and separate read, deserialization, and H2D intervals.

| Model/session | Workload | Path | Median MB/s | Bootstrap 95% CI, MB/s |
| --- | --- | --- | --- | --- |
| Qwen/Qwen2.5-1.5B/phase2-main-session-1 | ultrachat | file_legs_torch | 1996.9 | [1939.1, 2133.9] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-1 | ultrachat | file_legs_raw | 2580.4 | [2481.2, 2653.5] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-1 | ultrachat | h2d_pinned | 9880.5 | [9837.1, 9948.3] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-1 | ultrachat | h2d_pageable | 4597.7 | [4441.8, 4678.1] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-2 | ultrachat | file_legs_torch | 2513.0 | [2416.8, 2554.9] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-2 | ultrachat | file_legs_raw | 2808.3 | [2683.1, 2869.7] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-2 | ultrachat | h2d_pinned | 9991.8 | [9726.5, 10051.1] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-2 | ultrachat | h2d_pageable | 4707.4 | [4546.6, 4772.2] |
| unsloth/Llama-3.2-3B-Instruct/phase2-llama-mirror-control | repeated_control | file_legs_torch | 2603.5 | [2069.7, 2633.4] |
| unsloth/Llama-3.2-3B-Instruct/phase2-llama-mirror-control | repeated_control | file_legs_raw | 2493.6 | [2096.8, 2741.9] |
| unsloth/Llama-3.2-3B-Instruct/phase2-llama-mirror-control | repeated_control | h2d_pinned | 11641.3 | [11597.2, 11673.1] |
| unsloth/Llama-3.2-3B-Instruct/phase2-llama-mirror-control | repeated_control | h2d_pageable | 4399.3 | [4321.8, 4443.6] |
| Qwen/Qwen2.5-3B/phase2-qwen-3b-control | repeated_control | file_legs_torch | 2065.8 | [1950.2, 2256.9] |
| Qwen/Qwen2.5-3B/phase2-qwen-3b-control | repeated_control | file_legs_raw | 2656.9 | [2597.5, 2802.0] |
| Qwen/Qwen2.5-3B/phase2-qwen-3b-control | repeated_control | h2d_pinned | 10078.1 | [10023.5, 10107.2] |
| Qwen/Qwen2.5-3B/phase2-qwen-3b-control | repeated_control | h2d_pageable | 4662.6 | [4487.1, 4715.4] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-3 | ultrachat | file_legs_torch | 1893.8 | [1847.5, 2141.3] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-3 | ultrachat | file_legs_raw | 2337.2 | [2039.9, 2553.0] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-3 | ultrachat | h2d_pinned | 11075.9 | [11057.0, 11112.9] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-3 | ultrachat | h2d_pageable | 4550.8 | [4423.2, 4603.6] |
| Qwen/Qwen2.5-1.5B/phase2-main-repeated-control | repeated_control | file_legs_torch | 1917.4 | [1818.9, 1979.0] |
| Qwen/Qwen2.5-1.5B/phase2-main-repeated-control | repeated_control | file_legs_raw | 2297.8 | [2154.1, 2497.9] |
| Qwen/Qwen2.5-1.5B/phase2-main-repeated-control | repeated_control | h2d_pinned | 10683.0 | [10599.1, 10734.9] |
| Qwen/Qwen2.5-1.5B/phase2-main-repeated-control | repeated_control | h2d_pageable | 4447.3 | [4268.7, 4514.9] |
| microsoft/phi-2/phase2-phi2-control | repeated_control | file_legs_torch | 1121.9 | [1094.4, 1138.6] |
| microsoft/phi-2/phase2-phi2-control | repeated_control | file_legs_raw | 1143.9 | [1081.7, 1161.5] |
| microsoft/phi-2/phase2-phi2-control | repeated_control | h2d_pinned | 11960.1 | [11932.5, 11969.2] |
| microsoft/phi-2/phase2-phi2-control | repeated_control | h2d_pageable | 4558.4 | [4530.5, 4586.3] |
| EleutherAI/pythia-1.4b/phase2-pythia-control | repeated_control | file_legs_torch | 1080.4 | [1042.8, 1118.4] |
| EleutherAI/pythia-1.4b/phase2-pythia-control | repeated_control | file_legs_raw | 1159.3 | [1129.5, 1166.6] |
| EleutherAI/pythia-1.4b/phase2-pythia-control | repeated_control | h2d_pinned | 12123.4 | [12113.4, 12132.8] |
| EleutherAI/pythia-1.4b/phase2-pythia-control | repeated_control | h2d_pageable | 4516.9 | [4468.2, 4567.1] |
| facebook/opt-1.3b/phase2-opt-control | repeated_control | file_legs_torch | 1125.5 | [1093.0, 1146.6] |
| facebook/opt-1.3b/phase2-opt-control | repeated_control | file_legs_raw | 1143.2 | [1089.4, 1165.0] |
| facebook/opt-1.3b/phase2-opt-control | repeated_control | h2d_pinned | 11537.8 | [11517.5, 11548.1] |
| facebook/opt-1.3b/phase2-opt-control | repeated_control | h2d_pageable | 4601.4 | [4551.2, 4635.5] |
| Qwen/Qwen2.5-0.5B/phase2-qwen-half-control | repeated_control | file_legs_torch | 2675.4 | [2362.9, 2795.7] |
| Qwen/Qwen2.5-0.5B/phase2-qwen-half-control | repeated_control | file_legs_raw | 3179.9 | [2800.2, 3253.8] |
| Qwen/Qwen2.5-0.5B/phase2-qwen-half-control | repeated_control | h2d_pinned | 9490.8 | [9283.7, 9571.8] |
| Qwen/Qwen2.5-0.5B/phase2-qwen-half-control | repeated_control | h2d_pageable | 4319.2 | [4280.3, 4377.9] |

## Crossover bandwidths by model and length

`B*_prefix = KV bytes / prefix-prefill seconds`. The overhead-adjusted TTFT prediction is `B*_TTFT = KV bytes / (full-recompute TTFT - GPU-hit new-turn TTFT - fixed overhead)`. The fixed overhead is calibrated from independent unthrottled H2D microbenchmarks. A nonpositive denominator predicts no beneficial finite reload bandwidth under this additive model. Unthrottled point predictions use the independently measured complete H2D leg, avoiding double-counting its allocation overhead. Prefix-only values in the repeated-text table come from the short-turn rounds; separately timed long-turn-round estimates remain in the JSONL.

A paired-round bootstrap evaluates the recompute-minus-hit denominator with the calibrated transfer overhead held fixed. A positive point threshold is flagged when that interval includes zero. Its full point value remains in the table and JSONL; unstable predictions are omitted from dashed curves and the prediction scatter, while all observed brackets and bounds remain visible. This interval excludes uncertainty in the overhead fit and variation across sessions.

Intervals use adjacent tested nominal simulated rates whose median TTFT ordering changes. The label "median only" means endpoint paired confidence intervals do not both resolve the sign. Achieved-rate endpoints and harmonic interpolation estimates are retained separately in JSONL. Interpolation is not an additional measured bandwidth point and assumes local linearity in inverse bandwidth. Its agreement with a bandwidth model is not independent validation of that assumption; the sampled-rate decisions and held-out session checks provide the direct tests.

### EleutherAI/pythia-1.4b

| Prefix | Predicted prefix B*, MB/s | Predicted TTFT B*, turn 32 | Observed simulated bracket, turn 32 | Predicted TTFT B*, turn 256 | Observed simulated bracket, turn 256 |
| --- | --- | --- | --- | --- | --- |
| 16 | 178.4 | No positive denominator | above tested achieved rates (bound only) | 513.5 (denominator uncertain) | [200.0, 400.0] target / [197.6, 394.3] achieved (median only) |
| 32 | 358.7 | No positive denominator | above tested achieved rates (bound only) | 862.1 | [400.0, 800.0] target / [396.3, 789.1] achieved (median only) |
| 64 | 701.2 | No positive denominator | above tested achieved rates (bound only) | 1427.3 | [400.0, 800.0] target / [397.3, 793.3] achieved (median only) |
| 128 | 1226.6 | 5313.3 | [1600.0, unthrottled] target / [1588.5, 11596.9] achieved | 1667.9 | [800.0, 1600.0] target / [795.5, 1588.8] achieved |
| 256 | 1210.6 | 1969.1 | [1600.0, unthrottled] target / [1594.4, 12080.5] achieved (median only) | 1481.4 | [800.0, 1600.0] target / [797.7, 1594.4] achieved (median only) |
| 512 | 1175.3 | 1543.7 | [800.0, 1600.0] target / [798.9, 1597.2] achieved (median only) | 1410.2 | [800.0, 1600.0] target / [799.2, 1597.2] achieved (median only) |
| 1024 | 1207.2 | 1369.7 | [800.0, 1600.0] target / [799.4, 1598.7] achieved | 1613.7 | [800.0, 1600.0] target / [799.5, 1598.6] achieved |
| 1792 | 1403.6 | 1591.6 | [1600.0, unthrottled] target / [1599.2, 12107.8] achieved (median only) | 1590.4 | [1600.0, unthrottled] target / [1599.2, 12107.2] achieved (median only) |

### Qwen/Qwen2.5-0.5B

| Prefix | Predicted prefix B*, MB/s | Predicted TTFT B*, turn 32 | Observed simulated bracket, turn 32 | Predicted TTFT B*, turn 256 | Observed simulated bracket, turn 256 |
| --- | --- | --- | --- | --- | --- |
| 16 | 7.9 | No positive denominator | above tested achieved rates (bound only) | No positive denominator | above tested achieved rates (bound only) |
| 32 | 15.4 | No positive denominator | above tested achieved rates (bound only) | No positive denominator | above tested achieved rates (bound only) |
| 64 | 30.6 | No positive denominator | above tested achieved rates (bound only) | No positive denominator | above tested achieved rates (bound only) |
| 128 | 61.7 | No positive denominator | above tested achieved rates (bound only) | No positive denominator | above tested achieved rates (bound only) |
| 256 | 122.7 | No positive denominator | above tested achieved rates (bound only) | No positive denominator | above tested achieved rates (bound only) |
| 512 | 226.6 | 2442.3 | [1600.0, unthrottled] target / [1558.1, 9531.0] achieved | 694.7 | [400.0, 800.0] target / [396.9, 789.0] achieved |
| 1024 | 257.4 | 473.2 | [400.0, 800.0] target / [397.4, 792.0] achieved | 310.6 | [200.0, 400.0] target / [199.4, 397.3] achieved |
| 2048 | 206.4 | 259.0 | [200.0, 400.0] target / [199.8, 398.7] achieved | 242.2 | [200.0, 400.0] target / [199.7, 399.1] achieved |
| 4096 | 173.6 | 188.5 | [100.0, 200.0] target / [100.0, 199.9] achieved | 181.2 | [100.0, 200.0] target / [100.0, 199.9] achieved |
| 8192 | 139.1 | 147.3 | [100.0, 200.0] target / [100.0, 199.9] achieved | 143.5 | [100.0, 200.0] target / [100.0, 199.9] achieved |

### Qwen/Qwen2.5-1.5B

| Prefix | Predicted prefix B*, MB/s | Predicted TTFT B*, turn 32 | Observed simulated bracket, turn 32 | Predicted TTFT B*, turn 256 | Observed simulated bracket, turn 256 |
| --- | --- | --- | --- | --- | --- |
| 16 | 14.2 | No positive denominator | above tested achieved rates (bound only) | Not scheduled / unavailable | Not scheduled / unavailable |
| 32 | 26.8 | No positive denominator | above tested achieved rates (bound only) | Not scheduled / unavailable | Not scheduled / unavailable |
| 64 | 53.3 | No positive denominator | above tested achieved rates (bound only) | Not scheduled / unavailable | Not scheduled / unavailable |
| 128 | 110.3 | No positive denominator | above tested achieved rates (bound only) | Not scheduled / unavailable | Not scheduled / unavailable |
| 256 | 204.4 | 564.4 | [400.0, 800.0] target / [395.1, 790.5] achieved (median only) | Not scheduled / unavailable | Not scheduled / unavailable |
| 512 | 189.6 | 223.3 | [200.0, 400.0] target / [199.5, 398.4] achieved | Not scheduled / unavailable | Not scheduled / unavailable |
| 1024 | 193.4 | 222.4 | [200.0, 400.0] target / [199.7, 399.1] achieved | Not scheduled / unavailable | Not scheduled / unavailable |
| 1792 | 150.9 | 162.0 | [100.0, 200.0] target / [100.0, 199.8] achieved | Not scheduled / unavailable | Not scheduled / unavailable |
| 2048 | 163.8 | 172.4 | [100.0, 200.0] target / [100.0, 199.9] achieved | Not scheduled / unavailable | Not scheduled / unavailable |
| 8192 | 126.2 | 129.5 | [100.0, 200.0] target / [100.0, 200.0] achieved | Not scheduled / unavailable | Not scheduled / unavailable |

### Qwen/Qwen2.5-3B

| Prefix | Predicted prefix B*, MB/s | Predicted TTFT B*, turn 32 | Observed simulated bracket, turn 32 | Predicted TTFT B*, turn 256 | Observed simulated bracket, turn 256 |
| --- | --- | --- | --- | --- | --- |
| 16 | 15.5 | 2323.5 (denominator uncertain) | above tested achieved rates (bound only) | 25.3 | <= 50.0 (bound only) |
| 32 | 27.2 | 1072.2 (denominator uncertain) | [800.0, 1600.0] target / [745.0, 1393.9] achieved (median only) | 44.1 | <= 50.0 (bound only) |
| 64 | 51.0 | 413.2 | [200.0, 400.0] target / [198.0, 392.6] achieved (median only) | 86.9 | <= 50.0 (bound only) |
| 128 | 79.4 | 125.1 | [100.0, 200.0] target / [99.7, 199.1] achieved | 101.6 | [50.0, 100.0] target / [49.9, 99.7] achieved |
| 256 | 87.0 | 103.4 | [100.0, 200.0] target / [99.9, 199.4] achieved (median only) | 93.5 | [50.0, 100.0] target / [49.9, 99.8] achieved |
| 512 | 91.6 | 104.9 | [100.0, 200.0] target / [99.9, 199.7] achieved | 96.0 | [50.0, 100.0] target / [50.0, 99.9] achieved |
| 1024 | 94.1 | 106.9 | [100.0, 200.0] target / [99.9, 199.8] achieved | 101.7 | [50.0, 100.0] target / [50.0, 99.9] achieved |
| 2048 | 97.2 | 96.7 | [50.0, 100.0] target / [50.0, 100.0] achieved | 119.4 | [100.0, 200.0] target / [100.0, 199.9] achieved |
| 4096 | 82.1 | 86.9 | [50.0, 100.0] target / [50.0, 100.0] achieved | 87.6 | [50.0, 100.0] target / [50.0, 100.0] achieved |
| 8192 | 74.7 | 75.9 | [50.0, 100.0] target / [50.0, 100.0] achieved | 75.8 | [50.0, 100.0] target / [50.0, 100.0] achieved |
| 16384 | 54.1 | 56.1 | [50.0, 100.0] target / [50.0, 100.0] achieved | 55.9 | [50.0, 100.0] target / [50.0, 100.0] achieved |

### facebook/opt-1.3b

| Prefix | Predicted prefix B*, MB/s | Predicted TTFT B*, turn 32 | Observed simulated bracket, turn 32 | Predicted TTFT B*, turn 256 | Observed simulated bracket, turn 256 |
| --- | --- | --- | --- | --- | --- |
| 16 | 221.6 | No positive denominator | above tested achieved rates (bound only) | 800.2 | [400.0, 800.0] target / [394.3, 777.9] achieved (median only) |
| 32 | 417.9 | 1253217.8 (denominator uncertain) | above tested achieved rates (bound only) | 4200.9 (denominator uncertain) | [1600.0, unthrottled] target / [1559.1, 10838.5] achieved (median only) |
| 64 | 776.3 | 10407.5 | above tested achieved rates (bound only) | 8067.3 (denominator uncertain) | [1600.0, unthrottled] target / [1579.2, 9586.6] achieved (median only) |
| 128 | 1399.4 | 6321.8 | [1600.0, unthrottled] target / [1589.3, 9999.8] achieved | 2738.2 | [1600.0, unthrottled] target / [1588.9, 10037.9] achieved |
| 256 | 1320.0 | 1779.0 | [1600.0, unthrottled] target / [1594.6, 11779.0] achieved | 1796.8 | [800.0, 1600.0] target / [798.1, 1594.4] achieved |
| 512 | 1171.2 | 1840.3 | [1600.0, unthrottled] target / [1597.3, 11541.0] achieved (median only) | 2232.5 | [1600.0, unthrottled] target / [1597.2, 11554.9] achieved (median only) |
| 1024 | 1328.1 | 1602.8 | [800.0, 1600.0] target / [799.6, 1598.6] achieved (median only) | 1657.1 | [800.0, 1600.0] target / [799.5, 1598.6] achieved (median only) |

### microsoft/phi-2

| Prefix | Predicted prefix B*, MB/s | Predicted TTFT B*, turn 32 | Observed simulated bracket, turn 32 | Predicted TTFT B*, turn 256 | Observed simulated bracket, turn 256 |
| --- | --- | --- | --- | --- | --- |
| 16 | 161.2 | 2501.7 | [1600.0, unthrottled] target / [1550.9, 9331.9] achieved (median only) | 198.4 | [100.0, 200.0] target / [99.6, 198.6] achieved (median only) |
| 32 | 320.9 | 3434.2 | [1600.0, unthrottled] target / [1574.9, 10098.2] achieved | 401.1 | [200.0, 400.0] target / [199.2, 397.4] achieved |
| 64 | 551.0 | 3084.9 | [1600.0, unthrottled] target / [1587.3, 10420.6] achieved | 499.8 | [200.0, 400.0] target / [199.7, 398.6] achieved |
| 128 | 916.7 | 1362.9 | [800.0, 1600.0] target / [797.9, 1593.8] achieved | 991.5 | [400.0, 800.0] target / [399.2, 796.9] achieved |
| 256 | 1028.4 | 923.0 | [800.0, 1600.0] target / [799.0, 1596.7] achieved | 1051.1 | [800.0, 1600.0] target / [798.7, 1596.7] achieved |
| 512 | 897.3 | 898.7 | [800.0, 1600.0] target / [799.2, 1598.4] achieved | 873.4 | [800.0, 1600.0] target / [799.3, 1598.3] achieved (median only) |
| 1024 | 863.9 | 825.1 | [800.0, 1600.0] target / [799.8, 1599.2] achieved | 914.4 | [800.0, 1600.0] target / [799.7, 1599.2] achieved |
| 1792 | 813.1 | 836.1 | [800.0, 1600.0] target / [799.8, 1599.5] achieved | 897.0 | [800.0, 1600.0] target / [799.8, 1599.5] achieved |

### unsloth/Llama-3.2-3B-Instruct

| Prefix | Predicted prefix B*, MB/s | Predicted TTFT B*, turn 32 | Observed simulated bracket, turn 32 | Predicted TTFT B*, turn 256 | Observed simulated bracket, turn 256 |
| --- | --- | --- | --- | --- | --- |
| 16 | 51.2 | 1865.3 | [1600.0, unthrottled] target / [1456.8, 6225.2] achieved (median only) | 67.1 | <= 50.0 (bound only) |
| 32 | 91.4 | 1935.6 | [1600.0, unthrottled] target / [1524.2, 7743.0] achieved | 127.7 | [50.0, 100.0] target / [49.8, 99.4] achieved (median only) |
| 64 | 166.0 | 1239.9 | [800.0, 1600.0] target / [790.0, 1562.1] achieved | 252.3 | [100.0, 200.0] target / [99.7, 198.8] achieved |
| 128 | 289.3 | 614.9 | [400.0, 800.0] target / [398.1, 795.3] achieved | 368.4 | [200.0, 400.0] target / [199.4, 398.4] achieved |
| 256 | 313.5 | 363.5 | [200.0, 400.0] target / [199.8, 398.9] achieved | 345.9 | [200.0, 400.0] target / [199.8, 398.8] achieved |
| 512 | 305.5 | 336.4 | [200.0, 400.0] target / [199.9, 399.5] achieved | 328.4 | [200.0, 400.0] target / [199.9, 399.5] achieved |
| 1024 | 296.8 | 337.5 | [200.0, 400.0] target / [199.9, 399.8] achieved | 366.9 | [200.0, 400.0] target / [199.9, 399.7] achieved |
| 2048 | 322.6 | 312.6 | [200.0, 400.0] target / [200.0, 399.9] achieved | 323.8 | [200.0, 400.0] target / [200.0, 399.8] achieved |
| 4096 | 288.7 | 292.0 | [200.0, 400.0] target / [200.0, 399.9] achieved | 304.3 | [200.0, 400.0] target / [200.0, 399.9] achieved |
| 8192 | 244.0 | 249.8 | [200.0, 400.0] target / [200.0, 400.0] achieved | 252.3 | [200.0, 400.0] target / [200.0, 400.0] achieved |
| 16384 | 187.2 | 188.7 | [100.0, 200.0] target / [100.0, 200.0] achieved | 187.5 | [100.0, 200.0] target / [100.0, 200.0] achieved |

## Main model on varied multi-turn text

| Prefix | Session | New-turn tokens | Predicted TTFT B*, MB/s | Observed simulated bandwidth bracket, MB/s |
| --- | --- | --- | --- | --- |
| 16 | phase2-main-session-1 | 32 | No positive denominator | above tested achieved rates (bound only) |
| 16 | phase2-main-session-2 | 32 | No positive denominator | above tested achieved rates (bound only) |
| 16 | phase2-main-session-3 | 32 | No positive denominator | above tested achieved rates (bound only) |
| 16 | phase2-main-session-1 | 256 | 36.9 | <= 50.0 (bound only) |
| 16 | phase2-main-session-2 | 256 | 37.4 | <= 50.0 (bound only) |
| 16 | phase2-main-session-3 | 256 | 28.5 | <= 50.0 (bound only) |
| 32 | phase2-main-session-1 | 32 | No positive denominator | above tested achieved rates (bound only) |
| 32 | phase2-main-session-2 | 32 | No positive denominator | above tested achieved rates (bound only) |
| 32 | phase2-main-session-3 | 32 | No positive denominator | above tested achieved rates (bound only) |
| 32 | phase2-main-session-1 | 256 | 60.6 | <= 50.0 (bound only) |
| 32 | phase2-main-session-2 | 256 | 87.3 | [50.0, 100.0] target / [49.6, 98.7] achieved (median only) |
| 32 | phase2-main-session-3 | 256 | 67.2 | <= 50.0 (bound only) |
| 64 | phase2-main-session-1 | 32 | No positive denominator | above tested achieved rates (bound only) |
| 64 | phase2-main-session-2 | 32 | No positive denominator | above tested achieved rates (bound only) |
| 64 | phase2-main-session-3 | 32 | No positive denominator | above tested achieved rates (bound only) |
| 64 | phase2-main-session-1 | 256 | 114.8 | [50.0, 100.0] target / [49.8, 99.3] achieved |
| 64 | phase2-main-session-2 | 256 | 153.3 | [50.0, 100.0] target / [49.7, 98.9] achieved (median only) |
| 64 | phase2-main-session-3 | 256 | 136.3 | [50.0, 100.0] target / [49.8, 99.3] achieved |
| 128 | phase2-main-session-1 | 32 | No positive denominator | above tested achieved rates (bound only) |
| 128 | phase2-main-session-2 | 32 | No positive denominator | above tested achieved rates (bound only) |
| 128 | phase2-main-session-3 | 32 | No positive denominator | above tested achieved rates (bound only) |
| 128 | phase2-main-session-1 | 256 | 205.8 | [100.0, 200.0] target / [99.4, 198.4] achieved |
| 128 | phase2-main-session-2 | 256 | 261.1 | [100.0, 200.0] target / [99.5, 197.8] achieved |
| 128 | phase2-main-session-3 | 256 | 222.8 | [100.0, 200.0] target / [99.5, 197.7] achieved |
| 256 | phase2-main-session-1 | 32 | 318.8 | [200.0, 400.0] target / [199.2, 395.5] achieved |
| 256 | phase2-main-session-2 | 32 | 382.8 | [200.0, 400.0] target / [199.2, 397.1] achieved (median only) |
| 256 | phase2-main-session-3 | 32 | 323.3 | [200.0, 400.0] target / [198.9, 396.9] achieved |
| 256 | phase2-main-session-1 | 256 | 152.7 | [100.0, 200.0] target / [99.8, 199.2] achieved |
| 256 | phase2-main-session-2 | 256 | 204.1 | [100.0, 200.0] target / [99.7, 198.8] achieved |
| 256 | phase2-main-session-3 | 256 | 165.4 | [100.0, 200.0] target / [99.8, 198.9] achieved |
| 512 | phase2-main-session-1 | 32 | 208.6 | [200.0, 400.0] target / [199.6, 398.8] achieved |
| 512 | phase2-main-session-2 | 32 | 266.2 | [200.0, 400.0] target / [199.4, 397.7] achieved |
| 512 | phase2-main-session-3 | 32 | 202.9 | [200.0, 400.0] target / [199.6, 398.0] achieved (median only) |
| 512 | phase2-main-session-1 | 256 | 167.2 | [100.0, 200.0] target / [99.9, 199.6] achieved |
| 512 | phase2-main-session-2 | 256 | 203.1 | [100.0, 200.0] target / [99.9, 199.5] achieved |
| 512 | phase2-main-session-3 | 256 | 164.0 | [100.0, 200.0] target / [99.9, 199.5] achieved |
| 1024 | phase2-main-session-1 | 32 | 173.6 | [100.0, 200.0] target / [100.0, 199.8] achieved |
| 1024 | phase2-main-session-2 | 32 | 200.6 | [200.0, 400.0] target / [199.8, 399.0] achieved (median only) |
| 1024 | phase2-main-session-3 | 32 | 208.0 | [200.0, 400.0] target / [199.7, 399.0] achieved |
| 1024 | phase2-main-session-1 | 256 | 150.4 | [100.0, 200.0] target / [100.0, 199.8] achieved |
| 1024 | phase2-main-session-2 | 256 | 188.3 | [100.0, 200.0] target / [99.9, 199.7] achieved |
| 1024 | phase2-main-session-3 | 256 | 177.4 | [100.0, 200.0] target / [99.9, 199.8] achieved |
| 2048 | phase2-main-session-1 | 32 | 152.4 | [100.0, 200.0] target / [100.0, 199.9] achieved |
| 2048 | phase2-main-session-2 | 32 | 178.5 | [100.0, 200.0] target / [100.0, 199.9] achieved |
| 2048 | phase2-main-session-3 | 32 | 149.7 | [100.0, 200.0] target / [100.0, 199.9] achieved |
| 2048 | phase2-main-session-1 | 256 | 157.2 | [100.0, 200.0] target / [100.0, 199.9] achieved |
| 2048 | phase2-main-session-2 | 256 | 185.4 | [100.0, 200.0] target / [100.0, 199.9] achieved |
| 2048 | phase2-main-session-3 | 256 | 153.4 | [100.0, 200.0] target / [100.0, 199.9] achieved |
| 4096 | phase2-main-session-1 | 32 | 142.5 | [100.0, 200.0] target / [100.0, 200.0] achieved |
| 4096 | phase2-main-session-2 | 32 | 166.8 | [100.0, 200.0] target / [100.0, 200.0] achieved |
| 4096 | phase2-main-session-3 | 32 | 137.7 | [100.0, 200.0] target / [100.0, 199.9] achieved |
| 4096 | phase2-main-session-1 | 256 | 133.8 | [100.0, 200.0] target / [100.0, 200.0] achieved |
| 4096 | phase2-main-session-2 | 256 | 157.8 | [100.0, 200.0] target / [100.0, 199.9] achieved |
| 4096 | phase2-main-session-3 | 256 | 136.1 | [100.0, 200.0] target / [100.0, 199.9] achieved |
| 8192 | phase2-main-session-1 | 32 | 121.5 | [100.0, 200.0] target / [100.0, 200.0] achieved |
| 8192 | phase2-main-session-2 | 32 | 141.0 | [100.0, 200.0] target / [100.0, 200.0] achieved |
| 8192 | phase2-main-session-3 | 32 | 120.9 | [100.0, 200.0] target / [100.0, 200.0] achieved |
| 8192 | phase2-main-session-1 | 256 | 123.3 | [100.0, 200.0] target / [100.0, 200.0] achieved |
| 8192 | phase2-main-session-2 | 256 | 139.3 | [100.0, 200.0] target / [100.0, 200.0] achieved |
| 8192 | phase2-main-session-3 | 256 | 119.1 | [100.0, 200.0] target / [100.0, 200.0] achieved |
| 16384 | phase2-main-session-1 | 32 | 86.3 | [50.0, 100.0] target / [50.0, 100.0] achieved |
| 16384 | phase2-main-session-2 | 32 | 97.2 | [50.0, 100.0] target / [50.0, 100.0] achieved |
| 16384 | phase2-main-session-3 | 32 | 85.2 | [50.0, 100.0] target / [50.0, 100.0] achieved |
| 16384 | phase2-main-session-1 | 256 | 85.4 | [50.0, 100.0] target / [50.0, 100.0] achieved |
| 16384 | phase2-main-session-2 | 256 | 97.8 | [50.0, 100.0] target / [50.0, 100.0] achieved (median only) |
| 16384 | phase2-main-session-3 | 256 | 83.9 | [50.0, 100.0] target / [50.0, 100.0] achieved |

### Rule decisions at resolved simulated-rate cells

| Model | Workload | Resolved rate cells | Prefix-only rule agrees | TTFT-adjusted rule agrees |
| --- | --- | --- | --- | --- |
| unsloth/Llama-3.2-3B-Instruct | repeated_control | 151 | 139 | 149 |
| Qwen/Qwen2.5-1.5B | repeated_control | 69 | 42 | 69 |
| Qwen/Qwen2.5-1.5B | ultrachat | 453 | 376 | 444 |
| facebook/opt-1.3b | repeated_control | 88 | 70 | 86 |
| microsoft/phi-2 | repeated_control | 109 | 100 | 106 |
| EleutherAI/pythia-1.4b | repeated_control | 99 | 85 | 97 |
| Qwen/Qwen2.5-3B | repeated_control | 149 | 134 | 146 |
| Qwen/Qwen2.5-0.5B | repeated_control | 140 | 71 | 140 |
These are descriptive counts over correlated model/length/session cells with resolved paired confidence intervals, not independent generalization trials.

### Matched-size repeated-text comparison at prefix 512, new turn 32

| MHA model | GQA comparison | KV-byte ratio, MHA/GQA | MHA simulated crossover | GQA simulated crossover |
| --- | --- | --- | --- | --- |
| EleutherAI/pythia-1.4b | Qwen/Qwen2.5-1.5B | 6.857 | [800.0, 1600.0] target / [798.9, 1597.2] achieved (median only) | [200.0, 400.0] target / [199.5, 398.4] achieved |
| facebook/opt-1.3b | Qwen/Qwen2.5-1.5B | 6.857 | [1600.0, unthrottled] target / [1597.3, 11541.0] achieved (median only) | [200.0, 400.0] target / [199.5, 398.4] achieved |
| microsoft/phi-2 | Qwen/Qwen2.5-3B | 8.889 | [800.0, 1600.0] target / [799.2, 1598.4] achieved | [100.0, 200.0] target / [99.9, 199.7] achieved |

## GQA versus MHA and short lengths

Compare the matched repeated-text runs at the common native lengths. The table reports both measured cache size and bandwidth crossovers. Differences across models combine attention architecture, parameter count, prefill throughput, and kernels; this is an association, not an isolated GQA treatment. The short-length rows expose fixed-overhead regimes where prefix-only and resumed-TTFT thresholds can disagree. A censored threshold is not assigned an exact crossover value.

These short-context cutoffs belong to this Transformers reference path, including cache construction and continuation kernels. They are not established cutoffs for an unmeasured serving engine.

The following short-context table gives the paired unthrottled-copy TTFT minus recompute TTFT. A positive interval favors recompute; an interval containing zero is unresolved. It includes tensor-view construction and cache reconstruction inside TTFT. The microbenchmark overhead fit captures the transfer path, so it need not explain every Python or shape-dependent cost at very short lengths.

| Model | Workload/session | Prefix | New turn | Unthrottled copy minus recompute, ms (paired 95% CI) |
| --- | --- | --- | --- | --- |
| EleutherAI/pythia-1.4b | repeated_control/phase2-pythia-control | 16 | 32 | 2.149 [1.827, 2.514] |
| EleutherAI/pythia-1.4b | repeated_control/phase2-pythia-control | 32 | 32 | 1.654 [1.480, 2.031] |
| EleutherAI/pythia-1.4b | repeated_control/phase2-pythia-control | 64 | 32 | 1.427 [0.784, 2.863] |
| EleutherAI/pythia-1.4b | repeated_control/phase2-pythia-control | 128 | 32 | -2.680 [-3.335, -1.303] |
| EleutherAI/pythia-1.4b | repeated_control/phase2-pythia-control | 16 | 256 | -6.630 [-7.497, -0.615] |
| EleutherAI/pythia-1.4b | repeated_control/phase2-pythia-control | 32 | 256 | -5.044 [-6.829, -3.948] |
| EleutherAI/pythia-1.4b | repeated_control/phase2-pythia-control | 64 | 256 | -8.986 [-10.021, -6.232] |
| EleutherAI/pythia-1.4b | repeated_control/phase2-pythia-control | 128 | 256 | -12.567 [-15.908, -10.759] |
| Qwen/Qwen2.5-0.5B | repeated_control/phase2-qwen-half-control | 16 | 32 | 2.239 [1.708, 2.807] |
| Qwen/Qwen2.5-0.5B | repeated_control/phase2-qwen-half-control | 32 | 32 | 2.087 [1.094, 3.376] |
| Qwen/Qwen2.5-0.5B | repeated_control/phase2-qwen-half-control | 64 | 32 | 2.559 [2.263, 4.049] |
| Qwen/Qwen2.5-0.5B | repeated_control/phase2-qwen-half-control | 128 | 32 | 2.526 [1.910, 2.740] |
| Qwen/Qwen2.5-0.5B | repeated_control/phase2-qwen-half-control | 16 | 256 | 1.853 [1.380, 2.341] |
| Qwen/Qwen2.5-0.5B | repeated_control/phase2-qwen-half-control | 32 | 256 | 1.882 [0.972, 2.464] |
| Qwen/Qwen2.5-0.5B | repeated_control/phase2-qwen-half-control | 64 | 256 | 2.145 [1.327, 3.203] |
| Qwen/Qwen2.5-0.5B | repeated_control/phase2-qwen-half-control | 128 | 256 | 1.794 [1.061, 2.708] |
| Qwen/Qwen2.5-1.5B | repeated_control/phase2-main-repeated-control | 16 | 32 | 2.589 [2.177, 3.726] |
| Qwen/Qwen2.5-1.5B | repeated_control/phase2-main-repeated-control | 32 | 32 | 2.394 [1.664, 3.324] |
| Qwen/Qwen2.5-1.5B | repeated_control/phase2-main-repeated-control | 64 | 32 | 2.794 [1.870, 4.141] |
| Qwen/Qwen2.5-1.5B | repeated_control/phase2-main-repeated-control | 128 | 32 | 3.401 [2.995, 3.899] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-1 | 16 | 32 | 2.247 [1.922, 3.106] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-1 | 32 | 32 | 2.010 [1.795, 3.337] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-1 | 64 | 32 | 2.646 [2.335, 3.177] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-1 | 128 | 32 | 1.323 [0.334, 2.168] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-1 | 16 | 256 | -12.636 [-15.218, -10.817] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-1 | 32 | 256 | -14.308 [-15.585, -12.093] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-1 | 64 | 256 | -15.235 [-16.614, -12.779] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-1 | 128 | 256 | -18.387 [-20.537, -15.647] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-2 | 16 | 32 | 2.155 [1.797, 2.568] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-2 | 32 | 32 | 2.574 [1.852, 3.750] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-2 | 64 | 32 | 3.010 [2.393, 4.419] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-2 | 128 | 32 | 2.564 [2.042, 3.265] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-2 | 16 | 256 | -11.845 [-13.180, -9.645] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-2 | 32 | 256 | -11.424 [-15.271, -9.172] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-2 | 64 | 256 | -13.169 [-17.331, -9.910] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-2 | 128 | 256 | -14.213 [-14.703, -13.236] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-3 | 16 | 32 | 2.052 [0.594, 2.292] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-3 | 32 | 32 | 2.418 [1.144, 2.619] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-3 | 64 | 32 | 2.321 [-0.967, 2.568] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-3 | 128 | 32 | 1.074 [-0.626, 2.311] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-3 | 16 | 256 | -14.602 [-20.064, -4.956] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-3 | 32 | 256 | -12.357 [-14.508, -8.280] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-3 | 64 | 256 | -16.874 [-19.150, -12.998] |
| Qwen/Qwen2.5-1.5B | ultrachat/phase2-main-session-3 | 128 | 256 | -16.568 [-18.006, -15.489] |
| Qwen/Qwen2.5-3B | repeated_control/phase2-qwen-3b-control | 16 | 32 | -0.292 [-1.102, 0.848] |
| Qwen/Qwen2.5-3B | repeated_control/phase2-qwen-3b-control | 32 | 32 | -1.638 [-1.990, -0.027] |
| Qwen/Qwen2.5-3B | repeated_control/phase2-qwen-3b-control | 64 | 32 | -6.095 [-6.894, -5.008] |
| Qwen/Qwen2.5-3B | repeated_control/phase2-qwen-3b-control | 128 | 32 | -34.635 [-39.184, -31.774] |
| Qwen/Qwen2.5-3B | repeated_control/phase2-qwen-3b-control | 16 | 256 | -23.712 [-29.252, -20.594] |
| Qwen/Qwen2.5-3B | repeated_control/phase2-qwen-3b-control | 32 | 256 | -23.333 [-28.118, -20.338] |
| Qwen/Qwen2.5-3B | repeated_control/phase2-qwen-3b-control | 64 | 256 | -24.668 [-31.955, -21.570] |
| Qwen/Qwen2.5-3B | repeated_control/phase2-qwen-3b-control | 128 | 256 | -42.735 [-45.117, -41.129] |
| facebook/opt-1.3b | repeated_control/phase2-opt-control | 16 | 32 | 0.703 [0.510, 1.068] |
| facebook/opt-1.3b | repeated_control/phase2-opt-control | 32 | 32 | 0.467 [0.356, 0.548] |
| facebook/opt-1.3b | repeated_control/phase2-opt-control | 64 | 32 | 0.329 [0.164, 0.910] |
| facebook/opt-1.3b | repeated_control/phase2-opt-control | 128 | 32 | -1.519 [-5.935, -0.761] |
| facebook/opt-1.3b | repeated_control/phase2-opt-control | 16 | 256 | -2.940 [-3.793, -1.922] |
| facebook/opt-1.3b | repeated_control/phase2-opt-control | 32 | 256 | -2.117 [-3.425, 0.644] |
| facebook/opt-1.3b | repeated_control/phase2-opt-control | 64 | 256 | -1.243 [-2.712, 0.853] |
| facebook/opt-1.3b | repeated_control/phase2-opt-control | 128 | 256 | -7.392 [-9.886, -4.461] |
| microsoft/phi-2 | repeated_control/phase2-phi2-control | 16 | 32 | -1.402 [-2.850, -0.629] |
| microsoft/phi-2 | repeated_control/phase2-phi2-control | 32 | 32 | -1.593 [-1.898, -1.405] |
| microsoft/phi-2 | repeated_control/phase2-phi2-control | 64 | 32 | -5.301 [-6.125, -4.673] |
| microsoft/phi-2 | repeated_control/phase2-phi2-control | 128 | 32 | -26.738 [-29.301, -22.773] |
| microsoft/phi-2 | repeated_control/phase2-phi2-control | 16 | 256 | -26.222 [-35.284, -23.020] |
| microsoft/phi-2 | repeated_control/phase2-phi2-control | 32 | 256 | -23.230 [-26.289, -21.701] |
| microsoft/phi-2 | repeated_control/phase2-phi2-control | 64 | 256 | -40.352 [-48.095, -38.012] |
| microsoft/phi-2 | repeated_control/phase2-phi2-control | 128 | 256 | -41.075 [-41.835, -36.856] |
| unsloth/Llama-3.2-3B-Instruct | repeated_control/phase2-llama-mirror-control | 16 | 32 | -1.182 [-2.267, -0.270] |
| unsloth/Llama-3.2-3B-Instruct | repeated_control/phase2-llama-mirror-control | 32 | 32 | -1.181 [-1.571, -0.794] |
| unsloth/Llama-3.2-3B-Instruct | repeated_control/phase2-llama-mirror-control | 64 | 32 | -5.582 [-6.482, -3.603] |
| unsloth/Llama-3.2-3B-Instruct | repeated_control/phase2-llama-mirror-control | 128 | 32 | -22.988 [-25.474, -18.744] |
| unsloth/Llama-3.2-3B-Instruct | repeated_control/phase2-llama-mirror-control | 16 | 256 | -28.093 [-36.690, -20.729] |
| unsloth/Llama-3.2-3B-Instruct | repeated_control/phase2-llama-mirror-control | 32 | 256 | -26.840 [-29.054, -23.930] |
| unsloth/Llama-3.2-3B-Instruct | repeated_control/phase2-llama-mirror-control | 64 | 256 | -27.496 [-30.718, -25.080] |
| unsloth/Llama-3.2-3B-Instruct | repeated_control/phase2-llama-mirror-control | 128 | 256 | -40.417 [-46.958, -35.769] |

### Measured returning-turn paths at prefix 512, new turn 32

These matched repeated-text measurements distinguish real unthrottled memory and local-file paths from the simulated bandwidth sweep. The pinned path is the unthrottled chunked-copy control; it imposes no bandwidth limit. Positive paired differences favor recompute.

| Model | Path | Recompute median, ms | Path median and 95% CI, ms | Paired path minus recompute, ms (95% CI) |
| --- | --- | --- | --- | --- |
| unsloth/Llama-3.2-3B-Instruct | cpu_pageable | 220.550 | 57.605 [57.481, 57.741] | -162.908 [-165.194, -160.436] |
| unsloth/Llama-3.2-3B-Instruct | simulated_unthrottled | 220.550 | 51.368 [50.600, 53.750] | -168.954 [-172.551, -165.118] |
| unsloth/Llama-3.2-3B-Instruct | file_torch_direct | 220.550 | 77.988 [75.777, 80.133] | -142.142 [-146.278, -139.509] |
| unsloth/Llama-3.2-3B-Instruct | file_torch_staged | 220.550 | 105.667 [104.789, 107.569] | -114.215 [-117.035, -112.558] |
| unsloth/Llama-3.2-3B-Instruct | file_raw_staged | 220.550 | 81.165 [80.428, 82.596] | -138.949 [-141.535, -137.365] |
| Qwen/Qwen2.5-1.5B | cpu_pageable | 101.633 | 38.997 [38.498, 39.425] | -63.123 [-64.335, -60.332] |
| Qwen/Qwen2.5-1.5B | simulated_unthrottled | 101.633 | 37.007 [36.607, 38.697] | -64.870 [-66.628, -60.791] |
| Qwen/Qwen2.5-1.5B | file_torch_direct | 101.633 | 45.296 [45.022, 46.141] | -55.979 [-57.729, -53.923] |
| Qwen/Qwen2.5-1.5B | file_torch_staged | 101.633 | 53.620 [53.185, 54.249] | -47.559 [-50.742, -45.667] |
| Qwen/Qwen2.5-1.5B | file_raw_staged | 101.633 | 46.777 [46.181, 47.394] | -53.943 [-56.398, -52.988] |
| facebook/opt-1.3b | cpu_pageable | 77.039 | 43.549 [42.565, 45.005] | -29.903 [-46.079, -23.407] |
| facebook/opt-1.3b | simulated_unthrottled | 77.039 | 35.339 [33.783, 35.436] | -43.691 [-54.777, -32.124] |
| facebook/opt-1.3b | file_torch_direct | 77.039 | 109.258 [106.793, 115.617] | 34.570 [25.933, 46.161] |
| facebook/opt-1.3b | file_torch_staged | 77.039 | 307.503 [305.549, 309.952] | 232.023 [217.591, 242.711] |
| facebook/opt-1.3b | file_raw_staged | 77.039 | 142.916 [138.983, 146.730] | 65.877 [57.466, 74.833] |
| microsoft/phi-2 | cpu_pageable | 227.553 | 76.109 [72.935, 83.485] | -149.086 [-154.094, -145.350] |
| microsoft/phi-2 | simulated_unthrottled | 227.553 | 51.953 [50.802, 59.813] | -171.602 [-180.966, -164.317] |
| microsoft/phi-2 | file_torch_direct | 227.553 | 188.988 [184.179, 193.752] | -40.048 [-47.331, -26.776] |
| microsoft/phi-2 | file_torch_staged | 227.553 | 510.323 [506.669, 521.590] | 286.052 [276.431, 295.895] |
| microsoft/phi-2 | file_raw_staged | 227.553 | 233.091 [231.259, 239.251] | 7.854 [-0.645, 12.549] |
| EleutherAI/pythia-1.4b | cpu_pageable | 90.788 | 48.821 [43.334, 49.150] | -42.096 [-47.001, -34.294] |
| EleutherAI/pythia-1.4b | simulated_unthrottled | 90.788 | 31.300 [28.272, 33.641] | -57.765 [-67.501, -46.520] |
| EleutherAI/pythia-1.4b | file_torch_direct | 90.788 | 109.223 [107.460, 116.517] | 20.840 [16.085, 35.761] |
| EleutherAI/pythia-1.4b | file_torch_staged | 90.788 | 308.847 [304.337, 311.812] | 220.223 [208.550, 234.147] |
| EleutherAI/pythia-1.4b | file_raw_staged | 90.788 | 142.297 [138.738, 146.581] | 56.698 [45.383, 64.621] |
| Qwen/Qwen2.5-3B | cpu_pageable | 228.430 | 52.063 [51.145, 54.476] | -176.346 [-181.638, -167.731] |
| Qwen/Qwen2.5-3B | simulated_unthrottled | 228.430 | 49.938 [49.051, 51.899] | -178.227 [-181.696, -173.996] |
| Qwen/Qwen2.5-3B | file_torch_direct | 228.430 | 58.646 [58.470, 58.999] | -169.766 [-174.157, -164.332] |
| Qwen/Qwen2.5-3B | file_torch_staged | 228.430 | 67.596 [66.816, 67.973] | -161.888 [-165.286, -158.435] |
| Qwen/Qwen2.5-3B | file_raw_staged | 228.430 | 59.123 [58.518, 61.271] | -169.950 [-173.341, -164.749] |
| Qwen/Qwen2.5-0.5B | cpu_pageable | 29.923 | 29.169 [29.043, 29.256] | -1.083 [-3.558, 0.143] |
| Qwen/Qwen2.5-0.5B | simulated_unthrottled | 29.923 | 28.544 [28.145, 28.867] | -1.938 [-4.013, -0.290] |
| Qwen/Qwen2.5-0.5B | file_torch_direct | 29.923 | 31.784 [31.400, 32.425] | 1.671 [-0.426, 3.513] |
| Qwen/Qwen2.5-0.5B | file_torch_staged | 29.923 | 34.964 [34.530, 35.478] | 4.971 [2.418, 6.001] |
| Qwen/Qwen2.5-0.5B | file_raw_staged | 29.923 | 32.886 [32.202, 34.013] | 2.931 [0.423, 4.266] |

### Additivity diagnostic

The next table subtracts the measured transfer leg and a same-round resident-hit TTFT from the simulated 50 MB/s reload TTFT at prefix 64 with a 256-token new turn. A negative resolved residual contradicts a constant resident-hit baseline for that condition; it does not mean a negative copy cost. This post-transfer remainder also includes view construction and host dispatch, so it is not isolated GPU kernel time.

| Model/session | Workload | Post-transfer minus resident hit, ms (paired 95% CI) |
| --- | --- | --- |
| unsloth/Llama-3.2-3B-Instruct/phase2-llama-mirror-control | repeated_control | -13.378 [-15.667, -8.235] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-1 | ultrachat | -13.694 [-15.528, -12.117] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-2 | ultrachat | -8.985 [-10.516, -4.343] |
| Qwen/Qwen2.5-1.5B/phase2-main-session-3 | ultrachat | -13.826 [-15.649, -9.800] |
| facebook/opt-1.3b/phase2-opt-control | repeated_control | -8.184 [-9.981, -4.841] |
| microsoft/phi-2/phase2-phi2-control | repeated_control | -22.293 [-26.712, -19.025] |
| EleutherAI/pythia-1.4b/phase2-pythia-control | repeated_control | -14.777 [-17.126, -13.167] |
| Qwen/Qwen2.5-3B/phase2-qwen-3b-control | repeated_control | -22.243 [-27.164, -20.636] |
| Qwen/Qwen2.5-0.5B/phase2-qwen-half-control | repeated_control | -1.199 [-2.363, -0.829] |

A paced copy changes the device activity preceding the new turn. Clock or power-state changes are possible explanations for a changing remainder, but the one-Hz samples cannot resolve the subsecond mechanism. These residuals remain evidence against exact additivity, not a fitted-away correction.

## File-tier decomposition and predictive residuals

Staged torch serialization and raw fp16 bytes use separate raw-read and CPU-deserialization timers, followed by actual H2D copies. Direct torch.load remains an additional baseline. Both file formats store the same packed fp16 buffer with shapes held as metadata; the pilot used nested per-layer tensors, so this is not an isolated cross-phase format experiment. The old estimate omits deserialization; the new estimate adds it. Each prediction uses independent microbenchmark medians plus the GPU-hit new-turn baseline. The raw-read API leg includes buffer allocation, and the BytesIO materialization belongs to the torch deserialization leg; neither is advertised as pure physical-media bandwidth.

The staged torch path materializes the full byte buffer before deserializing it, and BytesIO adds another host copy. It can be slower than direct torch.load. The raw format is likewise not assumed to be the fastest file path; the measured direct baseline remains visible.

| Format | Median absolute relative TTFT error, old rule | Median absolute relative TTFT error, with deserialization |
| --- | --- | --- |
| torch | 11.8% | 3.1% |
| raw | 3.1% | 3.1% |

The overall median weights each completed model/length/turn/session cell equally. The replicated main model therefore contributes more cells; per-model residuals follow.

| Model | Format | Cells | Old median absolute relative error | With deserialization |
| --- | --- | --- | --- | --- |
| EleutherAI/pythia-1.4b | torch | 16 | 39.9% | 4.3% |
| EleutherAI/pythia-1.4b | raw | 16 | 3.7% | 3.7% |
| Qwen/Qwen2.5-0.5B | torch | 20 | 8.9% | 2.9% |
| Qwen/Qwen2.5-0.5B | raw | 20 | 2.4% | 2.4% |
| Qwen/Qwen2.5-1.5B | torch | 76 | 8.5% | 2.6% |
| Qwen/Qwen2.5-1.5B | raw | 76 | 2.4% | 2.4% |
| Qwen/Qwen2.5-3B | torch | 22 | 8.5% | 3.3% |
| Qwen/Qwen2.5-3B | raw | 22 | 3.5% | 3.5% |
| facebook/opt-1.3b | torch | 14 | 26.1% | 3.5% |
| facebook/opt-1.3b | raw | 14 | 4.5% | 4.4% |
| microsoft/phi-2 | torch | 16 | 43.5% | 3.9% |
| microsoft/phi-2 | raw | 16 | 4.7% | 4.7% |
| unsloth/Llama-3.2-3B-Instruct | torch | 22 | 18.2% | 3.1% |
| unsloth/Llama-3.2-3B-Instruct | raw | 22 | 3.6% | 3.6% |

Adding a measured leg does not guarantee lower residuals: host dispatch, overlapping copies, allocation, cold-read patterns, and GPU clock state can make independently measured costs nonadditive. The raw-byte view avoids tensor deserialization but still performs the file read and GPU transfer. Physical-read accounting and advisory eviction status remain in the records. Phase two uses per-file DONTNEED advice, without a privileged global page-cache flush; advice alone does not guarantee a cold physical device.

## Clocks, drift, and the pilot anomaly

Telemetry samples SM and memory clocks, temperature, power, utilization, and active throttle reasons at approximately one Hz. Subsecond timing joins use nearby samples where needed; they cannot identify exact clocks for each individual GPU kernel. Timing-specific joined summaries are retained.

| Session | GPU-0 telemetry samples | Effective Hz | SM clock range, MHz | Temperature range, C | Power range, W | Throttle masks observed |
| --- | --- | --- | --- | --- | --- | --- |
| phase2-calibration-t4 | 241 | 0.938 | 585.0–1590.0 | 36.0–54.0 | 26.53–102.12 | 0x0000000000000000, 0x0000000000000004 |
| phase2-main-session-1 | 1625 | 0.947 | 405.0–1590.0 | 57.0–83.0 | 30.07–123.52 | 0x0000000000000000, 0x0000000000000004 |
| phase2-calibration-mha-fixed | 158 | 0.941 | 585.0–1590.0 | 40.0–57.0 | 26.48–104.0 | 0x0000000000000000, 0x0000000000000004 |
| phase2-main-session-2 | 1550 | 0.946 | 495.0–1590.0 | 52.0–83.0 | 28.72–108.62 | 0x0000000000000000, 0x0000000000000004 |
| phase2-calibration-llama-mirror | 110 | 0.937 | 585.0–1590.0 | 51.0–65.0 | 26.95–89.59 | 0x0000000000000000, 0x0000000000000004 |
| phase2-llama-mirror-control | 4962 | 0.944 | 465.0–1590.0 | 52.0–82.0 | 27.55–124.08 | 0x0000000000000000, 0x0000000000000004 |
| phase2-qwen-3b-control | 2483 | 0.947 | 360.0–1590.0 | 45.0–81.0 | 28.12–122.66 | 0x0000000000000000, 0x0000000000000004 |
| phase2-main-session-3 | 1626 | 0.946 | 390.0–1590.0 | 47.0–82.0 | 28.15–115.89 | 0x0000000000000000, 0x0000000000000004 |
| phase2-main-repeated-control | 422 | 0.945 | 585.0–1590.0 | 47.0–82.0 | 27.66–102.42 | 0x0000000000000000, 0x0000000000000004 |
| phase2-phi2-control | 1569 | 0.944 | 465.0–1590.0 | 51.0–82.0 | 28.03–115.97 | 0x0000000000000000, 0x0000000000000004 |
| phase2-pythia-control | 931 | 0.943 | 585.0–1590.0 | 42.0–82.0 | 26.84–105.03 | 0x0000000000000000, 0x0000000000000004 |
| phase2-opt-control | 550 | 0.944 | 585.0–1590.0 | 40.0–72.0 | 26.71–100.47 | 0x0000000000000000, 0x0000000000000004 |
| phase2-qwen-half-control | 423 | 0.947 | 585.0–1590.0 | 53.0–81.0 | 28.71–126.24 | 0x0000000000000000, 0x0000000000000004 |

These whole-session ranges include loading and idle intervals. They are not proof of thermal throttling during a particular measurement. The phase-two Torch CUDA build differs from the pilot; cross-phase timing changes are not attributed solely to drift. The observed 0x4 event bit denotes software power capping in [NVIDIA's NVML definitions](https://nvidia.github.io/cuda-python/cuda-bindings/13.4.4/module/generated/cuda.bindings.nvml.ClocksEventReasons.html). Joined long-prefill clock samples accompany the timings; these associations are not a controlled causal clock experiment.

| Session | Startup-reported power cap, W | Samples above that cap | Maximum raw reported draw, W |
| --- | --- | --- | --- |
| phase2-calibration-t4 | 70.0 | 8 | 102.12 |
| phase2-main-session-1 | 70.0 | 165 | 123.52 |
| phase2-calibration-mha-fixed | 70.0 | 4 | 104.00 |
| phase2-main-session-2 | 70.0 | 181 | 108.62 |
| phase2-calibration-llama-mirror | 70.0 | 3 | 89.59 |
| phase2-llama-mirror-control | 70.0 | 235 | 124.08 |
| phase2-qwen-3b-control | 70.0 | 210 | 122.66 |
| phase2-main-session-3 | 70.0 | 160 | 115.89 |
| phase2-main-repeated-control | 70.0 | 25 | 102.42 |
| phase2-phi2-control | 70.0 | 73 | 115.97 |
| phase2-pythia-control | 70.0 | 20 | 105.03 |
| phase2-opt-control | 70.0 | 21 | 100.47 |
| phase2-qwen-half-control | 70.0 | 26 | 126.24 |

Some power-draw samples exceed the cap shown by the startup display. These readings are retained without correction and are not used to calculate energy or establish instantaneous physical power. No independent power instrument was available.

| Main-model session and workload | Prefix-only median at 8192, ms | Prefix + 32 recompute median, ms | Prefix-only matched SM MHz | Prefix + 32 matched SM MHz |
| --- | --- | --- | --- | --- |
| phase2-main-repeated-control, repeated_control | 1861.5 | 1882.7 | 697.5 | 750.0 |
| phase2-main-session-1, ultrachat | 1980.1 | 2001.3 | 667.5 | 720.0 |
| phase2-main-session-2, ultrachat | 1701.0 | 1729.5 | 810.0 | 847.5 |
| phase2-main-session-3, ultrachat | 2005.8 | 2013.8 | 652.5 | 615.0 |

| Session/workload | Paired prefix-only minus prefix + 32, ms | Bootstrap 95% CI, ms |
| --- | --- | --- |
| phase2-main-repeated-control/repeated_control | -14.341 | [-39.033, 7.292] |
| phase2-main-session-1/ultrachat | -35.365 | [-53.096, -10.318] |
| phase2-main-session-2/ultrachat | -20.844 | [-58.561, -10.691] |
| phase2-main-session-3/ultrachat | -20.442 | [-45.456, 2.539] |

A positive difference would reproduce the pilot ordering. An interval spanning zero does not resolve the ordering. The original pilot has no matching clock trace, so these new observations cannot identify its historical cause.

| Excluded profile input tokens | Wall, ms | GPU kernels, ms | GEMM kernels, ms |
| --- | --- | --- | --- |
| 8192 | 1943.247 | 1933.654 | 853.429 |
| 8224 | 1975.334 | 1971.741 | 873.850 |
| 8448 | 2002.670 | 1999.697 | 868.232 |

Input-shape-specific GEMM kernel names and durations are preserved in the profile summaries. The profile is a separate instrumented pass, so its timings do not enter benchmark confidence intervals. A matrix-shape or clock explanation for the original pilot must be distinguished from a proved historical cause.

## Across-session uncertainty

Session-to-session spread is the range of separate session medians. Each accompanying CI is a within-session percentile bootstrap interval. The session medians are not pooled into one artificially narrow interval. The following table selects a short turn and representative conditions; all conditions and both new-turn lengths are in the results.

| Prefix | Condition | Sessions | Separate session medians, ms | Range / median | Within-session 95% CIs, ms |
| --- | --- | --- | --- | --- | --- |
| 16 | file_raw_staged | 3 | 33.279, 34.364, 34.210 | 3.2% | [32.948, 33.925]; [34.047, 34.794]; [33.755, 35.510] |
| 16 | recompute | 3 | 30.685, 31.530, 30.970 | 2.7% | [30.305, 31.250]; [31.159, 31.934]; [30.839, 32.792] |
| 16 | simulated_200_MBps | 3 | 34.799, 35.907, 35.740 | 3.1% | [34.602, 35.244]; [35.449, 36.350]; [35.248, 36.093] |
| 32 | file_raw_staged | 3 | 33.741, 35.040, 34.537 | 3.8% | [33.349, 34.099]; [34.252, 35.486]; [34.332, 35.769] |
| 32 | recompute | 3 | 30.718, 32.025, 31.471 | 4.2% | [30.435, 30.934]; [31.381, 32.230]; [31.111, 32.325] |
| 32 | simulated_200_MBps | 3 | 37.219, 38.406, 37.704 | 3.2% | [36.832, 39.739]; [37.812, 39.341]; [37.314, 38.047] |
| 64 | file_raw_staged | 3 | 34.771, 34.835, 35.505 | 2.1% | [34.198, 36.671]; [34.216, 35.747]; [35.050, 36.036] |
| 64 | recompute | 3 | 30.618, 30.935, 31.336 | 2.3% | [30.507, 31.049]; [30.728, 31.308]; [31.107, 34.964] |
| 64 | simulated_200_MBps | 3 | 41.163, 41.867, 41.968 | 1.9% | [40.765, 41.467]; [41.468, 42.193]; [41.593, 42.525] |
| 128 | file_raw_staged | 3 | 36.444, 36.270, 36.251 | 0.5% | [35.890, 37.023]; [35.965, 37.076]; [35.836, 36.745] |
| 128 | recompute | 3 | 32.373, 31.915, 32.603 | 2.1% | [31.509, 33.235]; [31.431, 32.064]; [31.831, 34.245] |
| 128 | simulated_200_MBps | 3 | 50.444, 50.863, 50.991 | 1.1% | [50.099, 51.299]; [50.555, 51.091]; [50.767, 51.923] |
| 256 | file_raw_staged | 3 | 38.442, 39.431, 38.866 | 2.5% | [37.171, 38.898]; [39.067, 40.072]; [38.456, 39.229] |
| 256 | recompute | 3 | 56.317, 52.661, 56.573 | 6.9% | [55.712, 58.015]; [49.859, 59.230]; [53.224, 58.111] |
| 256 | simulated_200_MBps | 3 | 68.917, 69.935, 69.386 | 1.5% | [68.601, 69.634]; [69.398, 70.340]; [68.903, 70.178] |
| 512 | file_raw_staged | 3 | 43.419, 43.962, 44.330 | 2.1% | [42.124, 45.390]; [43.179, 45.115]; [43.818, 45.373] |
| 512 | recompute | 3 | 103.337, 88.500, 106.410 | 17.3% | [101.898, 104.495]; [87.544, 95.003]; [104.818, 107.535] |
| 512 | simulated_200_MBps | 3 | 105.833, 106.277, 106.574 | 0.7% | [105.285, 106.469]; [106.035, 106.704]; [106.350, 106.753] |
| 1024 | file_raw_staged | 3 | 54.737, 54.701, 54.175 | 1.0% | [53.049, 57.327]; [53.825, 56.332]; [52.324, 56.126] |
| 1024 | recompute | 3 | 202.617, 180.537, 174.965 | 15.3% | [200.778, 211.521]; [177.917, 181.313]; [172.847, 176.084] |
| 1024 | simulated_200_MBps | 3 | 179.816, 180.548, 180.037 | 0.4% | [179.365, 182.476]; [179.949, 181.438]; [179.643, 180.635] |
| 2048 | file_raw_staged | 3 | 70.467, 70.287, 69.749 | 1.0% | [69.512, 75.207]; [68.910, 71.965]; [68.977, 71.752] |
| 2048 | recompute | 3 | 418.876, 364.902, 426.685 | 14.7% | [407.400, 429.721]; [356.461, 369.837]; [424.929, 435.728] |
| 2048 | simulated_200_MBps | 3 | 326.629, 326.298, 326.894 | 0.2% | [326.222, 327.437]; [326.130, 328.139]; [326.382, 327.329] |
| 4096 | file_raw_staged | 3 | 116.739, 112.465, 114.209 | 3.7% | [110.076, 133.259]; [108.174, 123.049]; [110.676, 130.879] |
| 4096 | recompute | 3 | 876.080, 746.869, 897.641 | 17.2% | [868.191, 883.856]; [735.384, 767.856]; [878.373, 907.995] |
| 4096 | simulated_200_MBps | 3 | 631.016, 624.543, 624.840 | 1.0% | [624.696, 648.202]; [623.493, 638.580]; [624.080, 629.636] |
| 8192 | file_raw_staged | 3 | 215.976, 205.157, 348.632 | 66.4% | [197.458, 222.889]; [199.197, 217.663]; [336.772, 358.157] |
| 8192 | recompute | 3 | 2001.330, 1729.460, 2013.808 | 14.2% | [1978.278, 2051.099]; [1710.696, 1765.723]; [1992.586, 2055.021] |
| 8192 | simulated_200_MBps | 3 | 1246.687, 1258.674, 1242.068 | 1.3% | [1233.467, 1256.965]; [1252.069, 1263.205]; [1230.048, 1255.640] |
| 16384 | file_raw_staged | 3 | 652.560, 643.717, 664.968 | 3.3% | [647.693, 658.627]; [640.946, 651.108]; [655.602, 692.019] |
| 16384 | recompute | 3 | 5539.798, 4932.296, 5615.971 | 12.3% | [5332.370, 5787.885]; [4869.739, 4980.156]; [5574.491, 5721.256] |
| 16384 | simulated_200_MBps | 3 | 2504.880, 2506.099, 2506.018 | 0.0% | [2500.592, 2506.609]; [2505.928, 2506.759]; [2503.895, 2506.168] |

### Fixed-calibration check in later sessions

This check fixes the first main session's recompute, GPU-hit, and transfer calibration. It predicts later-session decisions without refitting their TTFT baselines. It tests session transfer on the same GPU type and input, not transfer to another GPU type.

| Later session | Resolved simulated-rate cells | Correct decisions using first-session calibration | Median absolute TTFT prediction error |
| --- | --- | --- | --- |
| phase2-main-session-2 | 149 | 148 | 3.0% |
| phase2-main-session-3 | 150 | 146 | 1.7% |

## Correctness, unavailable coverage, and budget

Every accepted restore must preserve the resident-cache continuation under a stricter same-shape comparison, agree on the full-recompute first token, and produce the expected cache length. Full-versus-cached fp16 logit differences are reported separately. The first MHA calibration failed the pilot elementwise check; recalibration tests restoration against an independently computed resident continuation and retains layerwise KV and logit differences.

The original Meta Llama base-model access was gated. The user-authorized ungated Llama-Instruct mirror is a distinct weight checkpoint; its observed config and KV layout are verified above. The P100 request returned T4s and aborted at the allocation check. That attempt provides no P100 measurements. Consequently, transfer of the rule across GPU types and the slower-versus-faster GPU hypothesis remain untested. Production work was optional and was omitted to prioritize this reference study. NOTES.md records the exact deviations, and BUDGET.md records every submitted kernel.

## Updated rule of thumb

For a calibrated additive estimate, reload when effective bandwidth exceeds `B* = transfer_bytes / (recompute_TTFT - GPU_hit_new_turn_TTFT - overhead - deserialization - other_transfer_legs)` with a positive denominator, and recompute otherwise.

This report ends the redesigned phase. Further experiments require a new user instruction.
