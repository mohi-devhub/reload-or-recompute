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
