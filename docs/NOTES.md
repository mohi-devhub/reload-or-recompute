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

- The initial T4 calibration completed the Qwen variants and OPT. Llama access failed with a gated-repository HTTP error. The runner checked for the existing `HF_TOKEN` Kaggle secret without logging its value; no usable access was available. The user subsequently authorized the ungated mirror described below.
- The P100 request was accepted by the API, but Kaggle actually allocated two Tesla T4 devices. The GPU check aborted before reference measurements. This supplies no P100 data. The failed allocation is charged using the last Kaggle execution-log timestamp and observed device count, including the conversion stage, because the normal allocation finalizer was not reached.
- The initial MHA calibration stopped on the pilot's elementwise full-versus-cached logit tolerance. Both failed cases had the same greedy token and correct cache length. The revised check compares restored-cache logits with an independently computed resident-cache continuation at the same shape, while retaining full-versus-cached logit differences and requiring first-token agreement. A new calibration is required before those models' full sweeps. This checks restoration fidelity without disguising fp16 differences between different prefill matrix shapes.
- The first calibration's unthrottled file/H2D microbenchmark records inherit a `simulated_bandwidth` flag from the shared copy helper. Their condition names identify their actual purpose. That metadata bug is corrected for all full sweeps; calibration data remain unchanged and are not used as publication TTFT confidence intervals.
- Kaggle's phase-two image supplies a different CUDA build of Torch from the pilot. Every measurement retains its actual environment; cross-phase changes are not attributed solely to drift or the cache format.
- The public conversation source is generated UltraChat dialogue. At long token counts, multiple distinct conversations are concatenated and explicitly marked as stitched. These are realistic varied text inputs, not claims about natural long single-conversation traffic.
- The optional production path is omitted in this phase to prioritize the redesigned reference grid and session replication. No claim is made about a Python-3.12 LMCache runtime.

- The corrected MHA calibration passed. Layerwise diagnostics show full-versus-standalone prefix KV differences already exist before any reload; resident-cache continuations likewise differ from full prefill. Exact H2D tensor comparisons and the same-shape continuation check test transfer correctness separately. Full-versus-cached logit differences and first-token agreement remain recorded rather than being discarded by a widened elementwise tolerance.
- All three primary main-model replications use the varied-dialogue fixture. A separate repeated-text main-model session supplies the control, with coverage reduced as documented below. Other full model sweeps use that same repeated-text control for the GQA/MHA comparison. This is an allocation of corpus coverage, not a claim that every model received a natural dialogue sweep.

## Authorized Llama substitution

The user subsequently directed use of `unsloth/Llama-3.2-3B-Instruct`, an ungated mirror, without waiting on a Hugging Face secret. It is an instruction-tuned substitution for the originally requested base model. The public config lookup shows the Llama architecture and no weight-quantization configuration. The benchmark must independently verify its tensor layout before accepting a full sweep. If the mirror fails, the user authorizes SmolLM3-3B as the fallback GQA comparison. No secret is requested or supplied for this substitution.

## Budget refinement after the first main session

The first full session completed. Runtime projections are updated from its length-dependent timings rather than relying only on the pilot curve. The pending main-model repeated-text control covers the common short/native MHA lengths, including a near-limit boundary, plus the original anomaly length. It omits the intermediate long control and the longest repeated-text point to preserve the phase cap after adding the authorized Llama mirror. All three primary varied-dialogue main-model sessions retain the full requested length grid and both new-turn lengths. Other model sweeps retain their configured native-context grid. Exact control lengths and the smaller timeout are in `configs/phase2_queue.json` and the eventual run specification; this is an explicit control-workload coverage reduction, not a missing primary main-model replication.

The auxiliary main-model repeated-text control uses the short new turn only. The primary dialogue sessions and other model sweeps retain both new-turn lengths. This retains the matched-size MHA comparison and anomaly control while reserving budget for the large Llama KV payload. The scheduler waits for active reservations to be reconciled rather than bypassing the cap when another pending timeout temporarily does not fit.

### Quota-snapshot refresh correction

Repeated output fetches for main-session-1, main-session-2, calibration-t4, and calibration-mha-fixed refreshed their `quota-after.json` during later source-provenance checks. Those files therefore describe the refresh time rather than the nearest post-run quota state; they cannot support per-run billing deltas. The controller now preserves an existing post-run snapshot and writes any later quota observation to a timestamped refresh file. Conservative device-hour accounting is unaffected: it uses executed process and kernel-log durations, rather than quota differences. The original phase-start quota snapshot and each submission's pre-run snapshot remain available.

### Parent deadline guard for later submissions

Later submissions add a parent session deadline, subtract actual elapsed setup time before starting the worker, and retain a finalization margin. The controller keeps its original setup allowance by default and permits a smaller explicit allowance after observing setup durations; the timeout-based GPU reservation is unchanged. Startup-duration records are derived from the parent and worker environment timestamps. This changes process budgeting only: timed forwards, copy pacing, file legs, randomized order, and correctness checks are unchanged. The three primary main-model sessions were already submitted with the same original runner; each later run retains its actual source hash and specification.

The remaining queued control sweeps use the smaller setup allowance with correspondingly shorter session timeouts, preserving their original worker budgets. Their exact authorized specifications are in `configs/phase2_queue.json`; the primary replications and already-running Llama/Qwen-3B kernels are unchanged. The host queue watcher was restarted to load these settings, without restarting either remote kernel.

Phase two retains per-file DONTNEED advice and physical-read counters for file conditions. It does not retry a privileged global cache flush, which was unavailable in the pilot. Advisory eviction is not proof of a cold physical device; the report names this limitation and labels the read leg as an API measurement including allocation.

### File representation and residual comparisons

Phase two packs KV tensors into one contiguous fp16 buffer, with tensor shapes retained as metadata. Both the torch-serialized and raw-byte formats use this packed representation; the pilot serialized its nested per-layer cache tensors. Phase-two old-versus-new file-rule residuals compare predictions against the same phase-two staged measurements, differing only in whether the independently measured deserialization leg is included. They are not a controlled attribution of pilot-to-phase-two changes to a single format or software change.

### Unthrottled prediction accounting

Unthrottled achieved bandwidth already includes allocation time in its transfer interval. The pointwise unthrottled prediction now uses the independent pinned-H2D microbenchmark duration directly, instead of adding a fitted overhead to an observed TTFT-transfer duration that already contains it. This also avoids using the tested TTFT transfer as its own calibration. Measured samples, crossover brackets, and the existing held-out-session method are unchanged. Paced predictions retain their declared additive approximation, including the known allocation/deadline overlap described in the protocol.

The final Qwen0.5B control waits until OPT has ended. This keeps the remaining MHA comparison ahead of an additional long-context GQA sweep when reservations are tight. It changes host scheduling only; active kernels and measurement functions are unchanged. Any eventual length reduction will be recorded separately with its actual budget evidence.

### Final budget allocation

After Phi-2 and Pythia completed, the original pending reservations no longer fit the remaining phase allowance. OPT therefore omits the protocol's extra near-limit boundary point and runs the requested native-supported prefixes through 1024 with both new turns. Its requested longer prefixes exceed its native total context once the new turn is included. This removes an added boundary measurement before reducing any requested Qwen0.5B length; the exact remaining coverage is chosen only after OPT's actual runtime is known. The final ledger supplies the measured budget evidence.

OPT completed its configured native-supported grid. The final Qwen0.5B sweep omits only prefix 16384 and retains every requested prefix through 8192, both new-turn sizes, all simulated rates, and the reference paths. The reconciled allowance permits less session time than the full Qwen0.5B worker projection alone, before setup and finalization. The shorter grid fits its per-length calibration projection with margin and a bounded final reservation. Exact observed usage, timeout, and projections are retained in the final budget records. This is a budget exclusion, not a measured memory limit or a fabricated long-context result.

### Reproduction pins after the final upload

After every experimental kernel had been uploaded, the local reproduction runner gained explicit model-revision arguments, and the controller gained public checkpoint/image manifests and an optional Kaggle owner setting. The observed manifests are generated from measurement and saved-source metadata, then refreshed after final collection. Uploaded scripts and all measured operations remain unchanged; their saved source hashes are authoritative. A fresh replication defaults to the authorized Llama mirror rather than the historical gated checkpoint. These preparation changes were not used to revise any observations.

### Near-zero baseline differences

Final plot review exposed a very large point threshold when recompute-minus-resident-hit time is nearly zero. The analysis now bootstraps the paired-round difference of medians with the independently calibrated transfer overhead held fixed. Finite point thresholds whose denominator interval includes zero are flagged; those predictions are omitted from dashed curves and the prediction scatter, while full point estimates and every measured bracket/bound are retained. This adds uncertainty diagnostics without changing measured timings or rule-decision counts. The interval does not include overhead-fit uncertainty or between-session variation.

## Phase three: platform preparation

The first Modal CPU-only preparation app built the pinned image layers, then the client failed with `RetryTimeoutError` after `StreamTerminatedError: Connection lost`. The app was confirmed stopped with zero running tasks and no saved result. Its full reservation remains charged conservatively because no measured function duration was recovered. A cached-image retry is separate in the ledger. No GPU calibration or sweep preceded this failure.

Displayed per-second Modal tariffs and billing-API hourly tariffs have rounding differences. Cost reservations use the larger of the displayed per-second rate and the current hourly rate divided by 3600, including CPU and capped memory. No credits or free-tier storage are used to reduce the estimate.

The cached-image preparation retry exposed `IndexError: 2` in the wrapper's repository-relative root calculation after Modal relocated the module to `/root`. The wrapper now resolves local upload paths only in `modal.is_local()` and uses fixed container paths remotely. A local test of the remote-import branch passes. This is outside the protected measurement functions; the failed CPU reservation remains in the budget.

Modal CLI 1.6.2 treats a nonexistent local download destination as a file even when the remote path is a directory; an existing directory receives an additional remote-directory component. Collection now creates the destination and normalizes that component after download. The remote records were preserved, and no GPU measurement was repeated for this collection-only correction.

Modal's allocated Ampere device reports `NVIDIA A10`, rather than A10G. The report and records retain that actual name and its observed compute capability. It is the requested Modal A10 service tier; no claim is made that its board branding is A10G.

### L4 allocation diagnosis

Both original L4 calibration apps stayed at zero running tasks while A10 calibration and three A10 sweep containers started. Before any L4 sweep or prediction fit, a separate main-model calibration requested a smaller host allocation (two physical CPU cores and 16 GiB capped RAM rather than four and 32 GiB). This tests host-resource availability without changing the timing functions. It is not evidence of a GPU performance difference. The ledger retains every request; the final allocation outcome and any adopted host difference must be reported. Source hashes for the platform adapter change when requested-resource metadata is added; all protected function hashes remain identical.

The smaller-host L4 diagnostic also remained queued with zero running containers and was cancelled. It supplies no timings or evidence that host size caused the wait. Its reservation remains charged conservatively; it is explicitly excluded from prediction fitting. Original L4 host requests remain unchanged. Modal function statistics confirmed one queued input and no running worker for each original L4 calibration app.

A separate, bounded minimal-image L4 Sandbox probe tests allocation through Modal's second interface. It is excluded from benchmark prediction fits. Sandboxes use standard GPU pricing but non-preemptible CPU/RAM tariffs; the probe's reservation was corrected to those higher CPU/RAM rates while remaining within the main cap. This diagnostic has no model timing function and is not a hardware-transfer data point.

### Ampere service-tier variation

The two A10-tier main sweeps report different actual names (`NVIDIA A10` and `NVIDIA A10G`) and distinct GPU UUIDs. Their initial PCIe link snapshots also differ. Calibration predictions remain frozen from the original calibration allocation. Each session retains its actual board name and PCIe telemetry; session spread therefore includes service-tier allocation variation, not just repeated measurements on a homogeneous physical board. The final report must not silently label every A10-tier allocation A10G or attribute the spread solely to clock drift.

The original L4 calibration subsequently allocated and completed on `NVIDIA L4` (compute capability 8.9), with the original four-core / 32 GiB host request and the exact pinned Torch/Transformers versions. The smaller-host change was not adopted. The minimal Sandbox diagnostic was cancelled once the original allocation succeeded; SDK cancellation terminates its unscheduled Sandbox, and its placeholder app was stopped. Both diagnostic reservations remain conservatively counted. No timed-function change or CUDA/runtime substitution was needed to obtain the L4 result.

After the original L4 main calibration succeeded, its control calibration still had no allocated container in repeated provider snapshots. One fresh control-calibration request uses identical resources, anchors, runtime and timing functions. Selection is defined before reading any timing outcomes: keep the first allocated container by provider start timestamp and cancel the duplicate. A bounded watcher cancels the fresh retry if neither allocates within its observation window. All requests remain in the ledger, and only the selected calibration may enter the frozen fit.

### Phase-three coverage and reproduction details

The native-limit Llama prefix is excluded on both nominal 24 GB targets because its projected simultaneous reference caches plus weights exceed capacity. Every affected condition is listed in `configs/phase3_plan.json`; this is a feasibility exclusion, not a measured OOM or a substituted shorter native limit. All other planned prefixes, turns and simulated-rate conditions remain scheduled.

Short calibration uses three measured rounds and five independent microbenchmark repeats; full sweeps retain ten measured randomized rounds after warmup. This keeps calibration short and separate from published sweep confidence intervals. The adapter schedules calibration-only baselines and adds a direct torch-load CPU/H2D microbenchmark. Full sweeps omit the phase-two staged-torch TTFT condition because this phase requests raw staged and direct torch paths. Protected timing functions remain identical.

Torch and Transformers match the T4 versions exactly. The logged Python patch differs: T4 used 3.13.16; Modal used 3.13.3. Drivers and PCIe configurations also differ and remain explicit platform differences. After all phase-three sweep scripts had been uploaded, the reproduction image pinned the already observed safetensors, Accelerate, Hugging Face Hub and Tokenizers versions. Their actual installation log, its hash and package versions are recorded in `configs/phase3_packages.json`. This does not change any uploaded measurements or protected timing function.

After uploads, the reproduction startup guard and offline audit were tightened to match complete GPU-name tokens, avoiding an L4/L40S or A10/A100 substring false match. Existing runs retain their originally uploaded adapter hashes; their logged names and compute capabilities are independently checked by the stronger offline audit. This changes future allocation validation only, with no change to measured timing functions or observations.
