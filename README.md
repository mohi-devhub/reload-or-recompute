# Reload or Recompute

A small systems study of when a returning conversation's KV cache is faster to reload than to recompute on older GPUs. The pilot uses Qwen2.5-1.5B on a Kaggle T4 allocation. The full grid requires the user's approval after the pilot.

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
python3 -m unittest discover -s tests -v
python3 scripts/analyze_pilot.py outputs/raw/pilot-v1/pilot-output/results.jsonl
```

`outputs/results.jsonl` retains source observations and adds derived medians, percentile bootstrap intervals, independent microbenchmark fits, and prediction errors. Analysis refuses duplicate sample keys, malformed records, invalid timings, or pooled experimental run IDs. An incomplete grid is reported explicitly and receives no crossover analysis.

Raw downloads are ignored by Git. Retain them locally for audit, including the kernel log and profiler trace. No public GitHub repository is created until the pilot passes.
