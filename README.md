# Reload or Recompute

The redesigned T4 phase is complete: seven fp16 models, three varied-dialogue main-model sessions, 26,040 timing samples, and 9.900916 conservative GPU-hours against the cap of 10. The authorized phase-three study tests frozen predictions on Modal L4 and A10. Read [the phase-two report](docs/PHASE2_REPORT.md), [the hardware-transfer protocol](docs/PHASE3_PROTOCOL.md), [coverage and deviations](docs/NOTES.md), and [the budget](docs/BUDGET.md). The Qwen0.5B 16k point is excluded by the earlier phase's budget; native context limits and a reduced auxiliary control are explicit in its report.

A small systems study of when a returning conversation's KV cache is faster to reload than to recompute on older GPUs. The pilot uses Qwen2.5-1.5B on a Kaggle T4 allocation. The original grid was replaced by the approved simulated-bandwidth study.

The reference pilot passed with limitations. Reload won at every sampled length, so no crossover length was identified. The production install failed on the selected vLLM release's Python requirement. Read [the pilot report](docs/PILOT_REPORT.md), [the GPU ledger](docs/BUDGET.md), and [the timing figure](figures/pilot-ttft.png).

Basic KV reuse and hardware-dependent break-even decisions are established work. Read [the literature review](docs/RELATED_WORK.md), especially py-kvcache and Cake, before interpreting this study's scope.

## Reproduce the pilot

Configure Kaggle CLI credentials outside this repository. Do not copy a credential file into the project. The submitted kernel must remain private. CLI help and metadata were checked against the installed Kaggle CLI before the initial submission.

```sh
kaggle kernels push --help
kaggle kernels status --help
kaggle kernels output --help
kaggle quota --format json
```

Edit `id` in `kernels/pilot/kernel-metadata.json` to use your Kaggle username. Keep the GPU, Internet, and privacy settings. Review [the budget](docs/BUDGET.md) before any submission.

```sh
kaggle kernels push -p kernels/pilot --accelerator NvidiaTeslaT4 --timeout 4800
kaggle kernels status mohiachu/reload-or-recompute-pilot
kaggle kernels output mohiachu/reload-or-recompute-pilot \
  -p outputs/raw/pilot-v1 \
  --file-pattern '(^|/)pilot-output/[^/]+\.(jsonl|log|txt|json)$'
```

For another owner, substitute that owner's kernel reference in the status and output commands. Kaggle exposes completed output artifacts, so an empty download while the kernel is running does not establish a benchmark failure. The file filter deliberately excludes temporary environments and KV payloads.

The kernel checks the actual GPU before timing. It logs the environment, appends JSONL samples incrementally, runs the reference path in a child process, and makes one bounded production compatibility attempt. See [the measurement protocol](docs/PROTOCOL.md) for timing boundaries, correctness checks, file-cache controls, and limitations.

## Analyze completed measurements

The local analysis requires Python and NumPy. Matplotlib is needed only for plots. The GPU kernel installs its reference dependencies itself. Exact runtime versions and model revision are stored with the results.

```sh
python3 -m pip install -r requirements-analysis.txt
python3 -m unittest discover -s tests -v
python3 scripts/analyze_pilot.py outputs/raw/pilot-v1/pilot-output/results.jsonl
```

The submitted reference source is preserved by commit `3e5262f`. Its source hash and exact Kaggle container image are recorded in the canonical `submission_metadata` record. The later source corrects production bootstrapping; reference measurement logic is unchanged. For exact historical source, read that commit rather than assuming the latest script is byte-identical.

The supplemental production-only probe reproduces the package-install compatibility failure without repeating the reference grid:

```sh
python3 scripts/build_production_kernel.py
kaggle kernels push -p kernels/production --accelerator NvidiaTeslaT4 --timeout 1500
kaggle kernels status mohiachu/reload-or-recompute-production-pilot
kaggle kernels output mohiachu/reload-or-recompute-production-pilot \
  -p outputs/raw/production-v1 \
  --file-pattern '(^|/)pilot-output/[^/]+\.(jsonl|log|txt|json)$'
```

This probe was already attempted for the study. Do not submit it again without accounting for the troubleshooting budget. The observed error and its limits are in [NOTES.md](docs/NOTES.md).

Capture the quota before submission and after each completed kernel in `outputs/raw/control/quota-before.json`, `quota-after-v1.json`, and `quota-after-production.json` using `kaggle quota --format json`. Retain source metadata with `kaggle kernels pull mohiachu/reload-or-recompute-pilot -p outputs/raw/pilot-v1/source -m`.

With both output directories, those quota snapshots, and the reference source metadata retained, rebuild the accepted results, profile summary, report, figures, and budget ledger:

```sh
python3 scripts/finalize_pilot.py
```

`outputs/results.jsonl` retains source observations and adds derived medians, percentile bootstrap intervals, independent microbenchmark fits, and prediction errors. Analysis refuses duplicate sample keys, malformed records, invalid timings, or pooled experimental run IDs. An incomplete grid is reported explicitly and receives no crossover analysis.

Raw downloads are ignored by Git. Retain them locally for audit, including the kernel log and profiler trace. The public results include individual timing observations and derived diagnostics; they exclude credentials and raw downloaded artifacts.

## Reproduce the redesigned study

Derive the pilot bandwidth thresholds without using a GPU:

```sh
python3 scripts/pilot_bstar.py
```

The generic runner and controller are in `kernels/phase2/runner.py` and `scripts/phase2_control.py`. Submission builds a private standalone script from the runner, frozen inputs, and the explicit run specification. It writes the GPU reservation to BUDGET.md before calling the Kaggle CLI. It refuses full sweeps for uncalibrated models on the requested GPU.

Checkpoint revisions and the actual Kaggle image are pinned in `configs/model_revisions.json` and `configs/phase2_runtime.json`. These pins come from the observed runtime, rather than a guessed package environment. Set `KAGGLE_KERNEL_OWNER` to your Kaggle username for a separately budgeted replication; the historical owner is the default. Preserve this study's final ledger and obtain a new run budget before starting another study. The commands below document the study configuration, rather than resetting its allowance.

The initial T4 calibration used:

```sh
python3 scripts/phase2_control.py submit --name calibration-t4 --purpose calibration \
  --lengths 32,512 --turns 32 --rates 50,200 --workloads repeated_control \
  --repeats 3 --micro-repeats 3 --stabilize 3 --timeout 1500
python3 scripts/phase2_control.py fetch --name calibration-t4
python3 scripts/phase2_project.py
```

The accepted main-model sessions use different seeds and distinct kernel references. Their full specifications are in `outputs/phase2_ledger.json`. The remaining approved configurations are in `configs/phase2_queue.json`. The dispatcher submits at most two sessions at a time and stops if the controller rejects a submission:

```sh
python3 scripts/phase2_dispatch.py
```

Existing run names cannot be submitted again. Do not erase the ledger to bypass the budget or calibration gate. Consult NOTES.md for the corrected MHA validation, gated Llama access, and mismatched P100 allocation. The dispatcher is resumable from the ledger after an interruption.

Analyze fetched artifacts and generate the report after the queue finishes:

```sh
python3 scripts/analyze_phase2.py
python3 scripts/audit_phase2.py
python3 scripts/report_phase2.py
python3 scripts/consolidate_phase2.py
```

Phase-two records in the canonical JSONL keep sessions separate. It includes individual timings, independently measured file legs, rate-limiter diagnostics, within-session confidence intervals, crossover brackets, session spread, and telemetry summaries. Every rate-limited path is simulated bandwidth. It must not be described as measured physical storage throughput.

After consolidation, a public checkout can rebuild the statistics and figures without the private Kaggle downloads:

```sh
python3 scripts/analyze_phase2.py --from-results outputs/results.jsonl
python3 scripts/report_phase2.py
```

The public archive includes individual GPU telemetry samples used in clock summaries. Instrumented profile summaries are retained; the larger profiler trace remains in ignored raw artifacts. The physical-work audit additionally requires the original fetched artifacts and saved source metadata.

## Rule of thumb

Use `B* = transfer_bytes / (T_recompute - T_GPU_hit - overhead - deserialization - other_transfer_legs)` as a calibrated threshold: reload above it when the denominator is positive, and recompute otherwise.

## Reproduce hardware transfer

Modal credentials stay outside the repository. The image pins Torch 2.11.0+cu130, Transformers 4.51.3, fp16 and the observed checkpoint revisions. Platform scheduling and persistence wrap the unchanged reference functions; hashes and the scheduling diff are in `outputs/phase3_provenance.json`. Modal's Ampere API tier is named `A10`; actual allocated names are recorded.

The commands below document the study. Existing run names and committed prediction registrations are immutable. Preserve the final ledger and create a separately authorized replication rather than resetting either budget.

```sh
python3 scripts/phase3_plan.py
python3 scripts/phase3_control.py submit --name preload --prepare --timeout 1200
python3 scripts/phase3_control.py collect --name preload
python3 scripts/phase3_control.py submit --name calibration-l4-main --gpu L4 --timeout 420 \
  --spec outputs/raw/phase3/control/specs/calibration-l4-main.json
python3 scripts/phase3_control.py collect --name calibration-l4-main
python3 scripts/phase3_control.py submit --name calibration-l4-controls --gpu L4 --timeout 600 \
  --spec outputs/raw/phase3/control/specs/calibration-l4-controls.json
python3 scripts/phase3_control.py collect --name calibration-l4-controls
```

After both calibration groups have completed and passed correctness checks, freeze and commit predictions **before** any sweep. Repeat with `A10` / `a10` for the second GPU. The submitter checks the prediction document and JSON against their Git commit, captures current tariffs, reserves cost before starting Modal, and refuses allocations beyond the cap.

```sh
python3 scripts/predict_phase3.py L4
git add configs/predictions_L4.json docs/PREDICTIONS_L4.md
git commit -m 'Preregister L4 predictions before sweep'
python3 scripts/phase3_sweeps.py --gpu L4 --name l4-main-1 --submit
python3 scripts/phase3_control.py collect --name l4-main-1
python3 scripts/phase3_sweeps.py --gpu L4 --name l4-main-2 --submit
python3 scripts/phase3_control.py collect --name l4-main-2
python3 scripts/phase3_sweeps.py --gpu L4 --name l4-controls --submit
python3 scripts/phase3_control.py collect --name l4-controls
```

Each bounded function appends results, backs up metadata during execution, verifies the GPU and exact runtime, and samples clocks, temperature, power, throttle reasons and PCIe link state. Cache files used for timing remain on local scratch. Named model/log volumes are temporary experiment infrastructure; remove only the study-created volumes after verified collection to stop their storage charges.

Public observations can rebuild phase-three scores, crossover tables and the figure without paid GPU work:

```sh
python3 scripts/analyze_phase3.py --from-results outputs/results.jsonl
python3 scripts/report_phase3.py
```

The analysis preserves each session and scores every complete frozen cell without refitting. Simulated-rate brackets are observations; interpolation between them is explicitly model-assisted. Canonical records include the calibration sources, frozen prediction manifests, timing samples, telemetry and budget ledger.
