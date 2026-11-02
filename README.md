# Reload or Recompute

A small systems study of when a returning conversation's KV cache is faster to reload than to recompute on older GPUs. The pilot uses Qwen2.5-1.5B on a Kaggle T4 allocation. The full grid requires the user's approval after the pilot.

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
