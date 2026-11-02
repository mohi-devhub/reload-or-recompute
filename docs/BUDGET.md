# GPU budget

The user authorizes a weekly ceiling of 30 GPU-hours, a pilot ceiling of 3 GPU-hours, and at most 45 GPU-minutes for production troubleshooting. These are limits, not measurements.

| Kernel and version | Outcome | Requested and observed hardware | Process seconds | Conservative device-hours |
| --- | --- | --- | --- | --- |
| mohiachu/reload-or-recompute-pilot, v1 | Reference complete; production venv bootstrap failed | NvidiaTeslaT4; 2 Tesla T4 devices | 234.523513 | 0.130291 |
| mohiachu/reload-or-recompute-production-pilot, v1 | Production package install rejected Python version | NvidiaTeslaT4; 2 Tesla T4 devices | 11.446949 | 0.006359 |

Conservative pilot total: **0.136650 GPU-hours**. Every visible GPU is charged, including the idle second device. Installation, downloads, and idle time within the process lifetime are included.

Production troubleshooting, including the first bootstrap failure: **0.000919 GPU-hours**. No additional production attempts are planned.

Kaggle's final rounded quota snapshot reports 0.07h used and 29.93h remaining. It appears to count session hours, unlike our two-device charge. Provisioning and finalization are outside the process timestamps. Both sources are retained in the canonical budget_ledger record.

Remaining pilot allowance under the conservative process accounting: 2.863350 GPU-hours. Remaining weekly allowance on that basis: 29.863350 GPU-hours.

Source: allocation_end, subprocess, production_status, and budget_ledger records in `outputs/results.jsonl`. Quota snapshots and run logs are retained in `outputs/raw`.

The full grid has not started and requires explicit user approval.

## Phase two

The redesigned phase is authorized with a separate cap of 10 GPU-hours. The old grid is not authorized. Pending reservations charge every possible allocated GPU for the entire session timeout. Completed rows charge process device-hours; quota snapshots retain the separate provisioning and billing evidence.

| Run | Purpose | GPU | Status | Session timeout, s | Reserved or observed device-hours |
| --- | --- | --- | --- | --- | --- |
| calibration-t4 | calibration | NvidiaTeslaT4 | submitted | 1500 | 0.833333 |

Observed usage plus active reservations: 0.833333 GPU-hours. Unreserved phase-two allowance: 9.166667 GPU-hours.

All values and submission settings are recorded in `outputs/phase2_ledger.json`. A model must complete a short calibration before its full sweep is submitted. Across-session main-model runs remain separate statistical groups.
