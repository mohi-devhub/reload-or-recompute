# Pilot report: Reload or Recompute

The measured file tier is a local file API path. Kaggle records positive process physical-read counters; underlying storage and host cache are unidentified. See [the counter audit](FILE_API_AUDIT.md).

Reference pilot passes with limitations. Reload wins throughout the sampled grid; the crossover is not identified. The production installation failed on the Python version. The full grid awaits approval.

This report is generated from `outputs/results.jsonl`. Configuration values describe the requested experiment; all observed values below come from its records. The full grid has not been started.

## Environment

- Requested GPU: `NvidiaTeslaT4`. Observed: `Tesla T4`, `Tesla T4`.
- Allocated devices: 2. Reference inference uses one device.
- Torch: `2.11.0+cu128`. CUDA runtime: `12.8`. Transformers: `4.51.3`. vLLM in the reference environment: `not installed`.
- GPU and driver query: Tesla T4, 580.178.04, 15360 MiB, GPU-2430a3c1-4db4-3a00-f33a-8e1a5df7fead; Tesla T4, 580.178.04, 15360 MiB, GPU-856fd157-d44b-a076-f238-7bf880cc0086.
- CPU cores: 4. Load average at process startup: `[0.43408203125, 0.27099609375, 0.126953125]`.
- CPU memory and initial free filesystem bytes are preserved verbatim in each source environment record.

## Raw timing summaries

Wall-clock TTFT ends when a greedy first token is available on the CPU. Tokenization, cache creation, offload writes, queueing, and transport are excluded. Cache acquisition and the new turn are included. CUDA events and synchronization accompany wall timing. See PROTOCOL.md.

### New turn: 32 tokens

| Prefix tokens | Condition | Median TTFT, ms | Bootstrap 95% CI, ms | Range, ms | Repeats |
| --- | --- | --- | --- | --- | --- |
| 512 | recompute | 90.258 | [89.874, 91.240] | 87.916–94.802 | 12 |
| 512 | cpu_pinned | 36.531 | [35.977, 37.001] | 35.606–37.637 | 12 |
| 512 | cpu_pageable | 39.724 | [39.210, 40.156] | 38.914–43.076 | 12 |
| 512 | file | 55.416 | [54.752, 57.360] | 52.281–58.862 | 12 |
| 512 | gpu_hit | 36.236 | [35.563, 37.093] | 35.326–37.454 | 12 |
| 2048 | recompute | 355.298 | [354.468, 357.838] | 351.584–359.313 | 12 |
| 2048 | cpu_pinned | 35.628 | [35.285, 36.479] | 34.403–39.472 | 12 |
| 2048 | cpu_pageable | 48.924 | [48.162, 49.287] | 47.402–50.374 | 12 |
| 2048 | file | 78.846 | [76.446, 79.377] | 75.297–84.562 | 12 |
| 2048 | gpu_hit | 36.042 | [35.134, 37.250] | 32.928–39.105 | 12 |
| 8192 | recompute | 1737.026 | [1728.186, 1745.245] | 1712.068–1757.012 | 12 |
| 8192 | cpu_pinned | 73.724 | [73.442, 76.383] | 73.347–78.199 | 12 |
| 8192 | cpu_pageable | 108.685 | [108.214, 109.463] | 107.358–111.460 | 12 |
| 8192 | file | 182.906 | [180.111, 189.695] | 175.920–199.289 | 12 |
| 8192 | gpu_hit | 58.907 | [58.293, 60.022] | 57.343–69.820 | 12 |

### New turn: 256 tokens

| Prefix tokens | Condition | Median TTFT, ms | Bootstrap 95% CI, ms | Range, ms | Repeats |
| --- | --- | --- | --- | --- | --- |
| 512 | recompute | 122.992 | [121.989, 124.087] | 117.922–124.687 | 12 |
| 512 | cpu_pinned | 50.599 | [49.940, 54.415] | 47.913–56.878 | 12 |
| 512 | cpu_pageable | 53.328 | [52.240, 54.313] | 51.063–56.752 | 12 |
| 512 | file | 65.027 | [63.364, 65.510] | 60.992–67.644 | 12 |
| 512 | gpu_hit | 48.657 | [47.627, 50.912] | 46.232–52.085 | 12 |
| 2048 | recompute | 392.750 | [390.207, 397.925] | 383.163–403.977 | 12 |
| 2048 | cpu_pinned | 68.801 | [66.607, 69.493] | 65.825–71.466 | 12 |
| 2048 | cpu_pageable | 74.340 | [72.494, 75.727] | 70.685–78.500 | 12 |
| 2048 | file | 97.511 | [96.147, 99.407] | 94.740–103.171 | 12 |
| 2048 | gpu_hit | 64.077 | [62.998, 66.873] | 56.856–67.807 | 12 |
| 8192 | recompute | 1869.626 | [1852.305, 1875.976] | 1840.335–1878.958 | 12 |
| 8192 | cpu_pinned | 131.684 | [130.068, 134.578] | 129.238–136.272 | 12 |
| 8192 | cpu_pageable | 163.955 | [163.661, 164.707] | 162.918–166.489 | 12 |
| 8192 | file | 240.179 | [236.803, 243.301] | 229.874–251.167 | 12 |
| 8192 | gpu_hit | 116.901 | [115.710, 117.902] | 115.270–126.812 | 12 |

The interval is a percentile bootstrap of the median over measured rounds. It measures within-session repeat variability, not across-session uncertainty.

## Prefix prefill and bandwidth

| Prefix tokens | Prefix-only median, ms | Prefill tokens/s from median latency |
| --- | --- | --- |
| 512 | 82.190 | 6229.4 |
| 2048 | 340.523 | 6014.3 |
| 8192 | 1879.994 | 4357.5 |

| Prefix tokens | Transfer | Median effective GB/s | Bootstrap 95% CI, GB/s |
| --- | --- | --- | --- |
| 512 | h2d_pinned | 10.543 | [10.485, 10.568] |
| 512 | h2d_pageable | 3.638 | [3.571, 3.713] |
| 512 | file_read | 3.813 | [3.647, 3.999] |
| 2048 | h2d_pinned | 11.455 | [11.446, 11.473] |
| 2048 | h2d_pageable | 4.159 | [4.076, 4.203] |
| 2048 | file_read | 1.581 | [1.416, 1.708] |
| 8192 | h2d_pinned | 12.022 | [12.018, 12.024] |
| 8192 | h2d_pageable | 4.379 | [4.355, 4.411] |
| 8192 | file_read | 1.709 | [1.663, 1.749] |

KV bytes per token from configuration: 28672. The script requires exact agreement with the observed tensor byte count.
Model revision: `8faed761d45a263340a0528343f099c05c9a4323`.

CPU RAM: 31.347 GiB. Initial free filesystem, bytes: `/kaggle/working` = 20940488704, `/tmp` = 1126014296064.

Page-cache control: `OSError: [Errno 30] Read-only file system: '/proc/sys/vm/drop_caches'`. Per-file DONTNEED is advisory. File timings include deserialization and pageable H2D.

Raw file microbenchmark physical-read/file-byte ratio: median 1.000, range [1.000, 1.000]. These counters are process I/O accounting, not a trace of the underlying storage device.

## Crossovers and predictive rule

`T_reload(L) = overhead + L × kv_bytes_per_token / effective_bandwidth`. The bandwidth and overhead fit uses microbenchmark medians independently of TTFT. The file prediction adds file-read and pageable-copy legs. The resumed-TTFT prediction adds the GPU-hit new-turn baseline. File deserialization remains an omitted cost and is part of the residual.

- h2d_pinned: overhead 0.235 ms; bandwidth 12.160 GB/s; nonnegative constraint active: False.
- h2d_pageable: overhead 0.809 ms; bandwidth 4.444 GB/s; nonnegative constraint active: False.
- file_read: overhead 0.000 ms; bandwidth 1.704 GB/s; nonnegative constraint active: True.

| New-turn tokens | Tier | Observed ordering or crossing | Predicted ordering or crossing |
| --- | --- | --- | --- |
| 32 | cpu_pinned | reload faster at all sampled lengths | reload faster at all sampled lengths |
| 32 | cpu_pageable | reload faster at all sampled lengths | reload faster at all sampled lengths |
| 32 | file | reload faster at all sampled lengths | reload faster at all sampled lengths |
| 256 | cpu_pinned | reload faster at all sampled lengths | reload faster at all sampled lengths |
| 256 | cpu_pageable | reload faster at all sampled lengths | reload faster at all sampled lengths |
| 256 | file | reload faster at all sampled lengths | reload faster at all sampled lengths |

| Prefix | Turn | Tier | Predicted TTFT, ms | Measured TTFT, ms | Signed error | Correct median ordering |
| --- | --- | --- | --- | --- | --- | --- |
| 512 | 32 | cpu_pinned | 37.678 | 36.531 | 3.1% | True |
| 2048 | 32 | cpu_pinned | 41.106 | 35.628 | 15.4% | True |
| 8192 | 32 | cpu_pinned | 78.458 | 73.724 | 6.4% | True |
| 512 | 32 | cpu_pageable | 40.348 | 39.724 | 1.6% | True |
| 2048 | 32 | cpu_pageable | 50.063 | 48.924 | 2.3% | True |
| 8192 | 32 | cpu_pageable | 112.567 | 108.685 | 3.6% | True |
| 512 | 32 | file | 48.969 | 55.416 | -11.6% | True |
| 2048 | 32 | file | 84.527 | 78.846 | 7.2% | True |
| 8192 | 32 | file | 250.395 | 182.906 | 36.9% | True |
| 512 | 256 | cpu_pinned | 50.099 | 50.599 | -1.0% | True |
| 2048 | 256 | cpu_pinned | 69.141 | 68.801 | 0.5% | True |
| 8192 | 256 | cpu_pinned | 136.451 | 131.684 | 3.6% | True |
| 512 | 256 | cpu_pageable | 52.769 | 53.328 | -1.0% | True |
| 2048 | 256 | cpu_pageable | 78.099 | 74.340 | 5.1% | True |
| 8192 | 256 | cpu_pageable | 170.560 | 163.955 | 4.0% | True |
| 512 | 256 | file | 61.390 | 65.027 | -5.6% | True |
| 2048 | 256 | file | 112.563 | 97.511 | 15.4% | True |
| 8192 | 256 | file | 308.389 | 240.179 | 28.4% | True |

A crossing is reported only between sampled lengths with opposite median ordering. Reload winning at every sampled length gives no exact crossover. Inspect the paired-difference intervals in the JSONL before treating a close median ordering as decisive. The GPU-hit baseline is measured at each shape, so this is a transfer-cost test, not a fully independent predictor of an unseen hardware configuration.

## Production path

Status: `failed`. Exit code: `1`.

Allocated-device time for this attempt: 0.000827 GPU-hours.

Exact install and runtime logs are retained under `outputs/raw`. The reviewed error and implications belong in NOTES.md. The first setup failed in ensurepip. The supplemental install reached pip and rejected `vllm==0.9.0`: `Requires-Python >=3.9,<3.13`; Kaggle provided Python 3.13. LMCache native kernels, CPU reuse, and file reuse were not reached. No sm_75 compatibility claim or production performance result is made. Both setup failures and the package choice are recorded in NOTES.md.

## GPU budget and full-grid projection

Kernel process lifetime: 234.524 seconds. Conservative allocated-device charge: 0.130291 GPU-hours. Kaggle provisioning and finalization may add time; reconcile against the quota ledger.
Kernel process lifetime: 11.447 seconds. Conservative allocated-device charge: 0.006359 GPU-hours. Kaggle provisioning and finalization may add time; reconcile against the quota ledger.

Total conservative process device-hours: 0.136650. Production troubleshooting: 0.000919 GPU-hours. See BUDGET.md for both kernel rows and the rounded Kaggle quota snapshot.
Timing-only proxy for one pilot-model sweep over the full requested length grid: 0.150996 allocated GPU-hours. Repeating that cost for every requested model gives 0.754979 allocated GPU-hours.

This is a conditional service-time proxy, not a credible total cost forecast. It uses linear interpolation and proportional extrapolation outside the pilot lengths, assumes every model costs the same as the pilot model, and includes warmups. It excludes setup, model downloads, profiling, cache preparation, bandwidth runs, memory failures, and differences in model architecture and quantization. P100 runtime and additional hardware cannot be forecast from this pilot. Use the observed kernel allocation as the setup baseline and calibrate each new model before authorizing a large sweep. The present data do not certify that the entire grid fits the remaining quota.

## Findings and surprises

All 18 reload-versus-recompute median orderings agree with the simple rule. This is an easy classification regime: every tested prefix favours reload. A numerical crossover prediction error cannot be computed without a measured crossing.

| Tier | Median absolute TTFT prediction error | Maximum absolute TTFT prediction error |
| --- | --- | --- |
| cpu_pinned | 3.4% | 15.4% |
| cpu_pageable | 2.9% | 5.1% |
| file | 13.5% | 36.9% |

Every generated first token matches recomputation. Maximum relative logit L2 error is 0.003841. Peak allocated VRAM is 4137518592 bytes. The closest reload-minus-recompute paired confidence-interval upper endpoint is -33.538 ms, so the reload advantage is resolved within this session.

Pinned reload and a GPU-resident hit overlap in latency at the shorter contexts. Do not interpret the occasional lower pinned median as faster than the resident-cache bound. Host dispatch, asynchronous copies, and within-session variation make independently measured copy cost imperfectly additive with the GPU-hit baseline.

Prefix-only prefill at the longest length is slower than recomputing the prefix plus the short turn. These are different matrix shapes and were measured at different times. Kernel selection and session drift are possible explanations; this pilot does not isolate the cause. The rule therefore uses actual measured prefill and reports its residuals without forcing monotonicity.

The file-read fit needs a nonnegative constraint on its overhead, and the longest file-TTFT prediction overestimates observed latency. The raw read microbenchmark, torch.load read pattern, CPU allocation, and host dispatch differ. A single effective-bandwidth term does not explain all file latency in this pilot.

The separate profile shows recompute dominated by GPU kernel execution, chiefly GEMMs. Reload profiles show substantial host dispatch and execution gaps beyond the copy itself. This establishes which operations dominate the instrumented path; it does not prove hardware FLOP or PCIe saturation. The profile file read was not evicted and is excluded from storage timing claims.

## Provisional rule of thumb

Reload when measured prefix prefill exceeds `fixed_overhead + L × kv_bytes_per_token / effective_bandwidth`, adding the file-read leg for files. Recompute when that cost is larger; include the new-turn baseline for TTFT and recalibrate for each model, GPU, and storage path.

This pilot favours reload at every sampled length, so it cannot locate the threshold or validate the rule on a different model or GPU.

## Limitations and review

- The pilot measures within-session latency for a controlled repeated-text conversation.
- It cannot test cross-GPU transfer or a GQA-versus-MHA causal hypothesis.
- File-cache hints and process read counters do not identify the physical storage medium.
- The profile is collected separately from reported timings. Inspect it before assigning a limiter.
- The production smoke is not a production throughput benchmark or a verified external-hit comparison.
- No full-grid work is authorized by this report.
