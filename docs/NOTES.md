# Study notes and deviations

## Before implementation

- Related work is reviewed in RELATED_WORK.md. py-kvcache substantially overlaps the central question. Proceed only as replication and older-hardware extension; no novelty claim for the underlying choice or slower-GPU hypothesis.
- The workspace initially contained no project or Git repository.
- The Kaggle CLI needed to refresh its existing credentials outside the filesystem sandbox. No credential file was read, copied, or added to this project.
- Pilot design: measure both requested new-turn lengths. Use one GPU for computation, but charge the budget for every allocated GPU if Kaggle allocates multiple devices.
- All timing estimates in planning are limits or projections, not measured results. Published source identifiers and configuration values are not project measurements.

## Reference pilot and production bootstrap

- The reference kernel completed its requested measurements and cache correctness checks. Its production setup failed before package installation. The exact error in `outputs/raw/pilot-v1/pilot-output/production-venv.log` is: `Error: Command '['/kaggle/working/production-venv/bin/python3', '-m', 'ensurepip', '--upgrade', '--default-pip']' returned non-zero exit status 1.` This is an environment bootstrap error, not an LMCache kernel compatibility result.
- A production-only supplemental kernel uses `venv --without-pip` and the existing pip's `--python` option, documented in [pip's interpreter-management guide](https://pip.pypa.io/en/stable/topics/python-option/). Its environment lives in `/tmp` to keep dependencies out of saved output artifacts. The original measurements and source hash remain unchanged.
- The supplemental kernel is part of the pilot, not the full grid. It preserves the production troubleshooting time limit. It does not repeat the reference measurements.
- The production attempt pins an available historical vLLM and LMCache pair to give Turing a compatible runtime opportunity. The latest documentation is background, not a guarantee for that pair. No unavailable version was submitted to a GPU.

## Production outcome

The supplemental kernel passed environment creation and attempted package installation. The exact relevant lines in `outputs/raw/production-v1/pilot-output/production-install.log` are:

```text
Error in sitecustomize; set PYTHONVERBOSE for traceback:
ModuleNotFoundError: No module named 'wrapt'
ERROR: Ignored the following versions that require a different python version: ... 0.9.0 Requires-Python >=3.9,<3.13; ...
ERROR: Could not find a version that satisfies the requirement vllm==0.9.0
ERROR: No matching distribution found for vllm==0.9.0
```

The ellipses shorten pip's list of other releases; the version-specific requirement and terminal error are copied exactly. Kaggle supplied Python 3.13, so the selected historical release cannot install there. Its Python requirement was not checked against the observed interpreter before the supplemental submission. No native build or LMCache CPU/disk runtime was reached. This is a failed production-path attempt, not evidence of an sm_75 failure. Stop production work at this point and retain the valid reference path.

## Measurement limitations

- Global page-cache eviction failed because `/proc/sys/vm/drop_caches` is read-only. Per-file eviction hints succeeded, and physical-read accounting supports reads beyond the process's page cache. The physical disk type and any host or storage cache remain unknown.
- Every observed length favours reload. The pilot therefore establishes no exact crossing and cannot score a predicted crossover length. The report gives pointwise latency and decision errors instead.
- The simple file model overestimates the longest-context TTFT and its overhead fit reaches a nonnegative constraint. These residuals are retained, not tuned away.
- Synthetic text controls token count but does not establish application quality or trace-level cache hit rates. Offload writes and cache creation are outside returning-turn TTFT.
- The full-grid projection is a pilot-model service-time proxy with explicit assumptions. It does not measure larger-model, quantized-model, or P100 cost.

## Phase two: pilot break-even bandwidth

Phase two replaces the original full grid. The user authorizes a separate ceiling of 10 GPU-hours. Every throttled path is simulated bandwidth; it is not a measurement of a physical storage device.

`B*_prefix(L) = L × kv_bytes_per_token / T_prefill(L) = kv_bytes_per_token × prefill_tokens_per_second(L)`. With reload fixed overhead `h`, use `B* = bytes / (T_prefill - h)` when the denominator is positive. For resumed-turn TTFT, the appropriate threshold is `bytes / (T_recompute(prefix + turn) - T_gpu_hit(turn | prefix) - h)`. The pilot anomaly and shape-dependent new-turn cost make these two thresholds differ.

| Prefix tokens | Prefix-only B*, MB/s | Bootstrap 95% CI, MB/s | With H2D overhead, MB/s | TTFT B*, turn 32, MB/s | TTFT B*, turn 256, MB/s |
| --- | --- | --- | --- | --- | --- |
| 512 | 178.611 | [174.935, 181.927] | 179.123 | 272.930 | 198.112 |
| 2048 | 172.441 | [171.369, 173.040] | 172.561 | 184.064 | 178.787 |
| 8192 | 124.937 | [124.034, 127.024] | 124.953 | 139.987 | 134.027 |

MB and GB are decimal throughout the bandwidth sweep. The user's approximate 125–180 MB/s range is supported by the prefix-only pilot medians after rounding. It is not the same as an end-to-end TTFT threshold. Source: `pilot_bstar` records in `outputs/results.jsonl`, regenerated with `python3 scripts/pilot_bstar.py`. Small KV size is a plausible contributor, not an isolated causal conclusion from one model.

## Phase-two calibration findings and deviations

- The initial T4 calibration completed the Qwen variants and OPT. Llama access failed with a gated-repository HTTP error. The runner checked for the existing `HF_TOKEN` Kaggle secret without logging its value; no usable access was available. Llama is blocked unless the user supplies an existing authorized secret label.
- The P100 request was accepted by the API, but Kaggle actually allocated two Tesla T4 devices. The GPU check aborted before reference measurements. This supplies no P100 data. The failed allocation is charged using the last Kaggle execution-log timestamp and observed device count, including the conversion stage, because the normal allocation finalizer was not reached.
- The initial MHA calibration stopped on the pilot's elementwise full-versus-cached logit tolerance. Both failed cases had the same greedy token and correct cache length. The revised check compares restored-cache logits with an independently computed resident-cache continuation at the same shape, while retaining full-versus-cached logit differences and requiring first-token agreement. A new calibration is required before those models' full sweeps. This checks restoration fidelity without disguising fp16 differences between different prefill matrix shapes.
- The first calibration's unthrottled file/H2D microbenchmark records inherit a `simulated_bandwidth` flag from the shared copy helper. Their condition names identify their actual purpose. That metadata bug is corrected for all full sweeps; calibration data remain unchanged and are not used as publication TTFT confidence intervals.
- Kaggle's phase-two image supplies a different CUDA build of Torch from the pilot. Every measurement retains its actual environment; cross-phase changes are not attributed solely to drift or the cache format.
- The public conversation source is generated UltraChat dialogue. At long token counts, multiple distinct conversations are concatenated and explicitly marked as stitched. These are realistic varied text inputs, not claims about natural long single-conversation traffic.
- The optional production path is omitted in this phase to prioritize the redesigned reference grid and session replication. No claim is made about a Python-3.12 LMCache runtime.
