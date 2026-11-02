# GPU budget

The user authorizes a weekly ceiling of 30 GPU-hours, a pilot ceiling of 3 GPU-hours, and at most 45 GPU-minutes troubleshooting the production path. These are limits, not observations.

The pilot kernel has been submitted. Actual allocation time and GPU count are pending its output. Record allocated-device time, including installation and idle time, rather than only timed CUDA operations. Reconcile local elapsed time with Kaggle's run timestamps and quota where available. Queue time is not GPU allocation time.

| Kernel and version | Status | Requested hardware | Observed hardware | Allocation time | Charged GPU-hours | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| mohiachu/reload-or-recompute-pilot, version 1 | Running | NvidiaTeslaT4 | Pending output | Pending | Pending | Kaggle CLI push and status; `outputs/raw/control/quota-before.json` |

Submission uses `--timeout 4800`. The script accepts at most two allocated GPUs, so the timeout bounds device-hours to less than the pilot allowance. The script uses only one GPU for inference and charges all allocated devices. The production attempt has an additional device-time limit. Do not submit a retry until the first run's consumption is known.

The full grid is not authorized. No full-grid kernels may be submitted before the user approves the pilot.
