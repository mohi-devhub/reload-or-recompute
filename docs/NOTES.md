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
