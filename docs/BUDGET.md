# GPU budget

The user authorizes a weekly ceiling of 30 GPU-hours, a pilot ceiling of 3 GPU-hours, and at most 45 GPU-minutes for production troubleshooting. These are limits, not measurements.

| Kernel and version | Outcome | Requested and observed hardware | Process seconds | Conservative device-hours |
| --- | --- | --- | --- | --- |
| mohiachu/reload-or-recompute-pilot, v1 | Reference complete; production venv bootstrap failed | NvidiaTeslaT4; 2 Tesla T4 devices | 234.523513 | 0.130291 |
| mohiachu/reload-or-recompute-production-pilot, v1 | Production package install rejected Python version | NvidiaTeslaT4; 2 Tesla T4 devices | 11.446949 | 0.006359 |

Conservative pilot total: **0.136650 GPU-hours**. Every visible GPU is charged, including the idle second device. Installation, downloads, and idle time within the process lifetime are included.

Production troubleshooting, including the first bootstrap failure: **0.000919 GPU-hours**. No additional production attempts are planned.

Kaggle's final rounded quota snapshot reports 0.07h used and 29.93h remaining. It appears to count session hours, unlike our two-device charge. Provisioning and finalization are outside the process timestamps. Both sources are retained in the canonical budget_ledger record.

At the pilot stop, remaining pilot allowance under conservative process accounting: 2.863350 GPU-hours. At the pilot stop, remaining weekly allowance on that basis: 29.863350 GPU-hours.

Source: allocation_end, subprocess, production_status, and budget_ledger records in `outputs/results.jsonl`. Quota snapshots and run logs are retained in `outputs/raw`.

The pilot is complete. The user subsequently approved only the redesigned phase-two study below.

## Phase two

The redesigned phase is authorized with a separate cap of 10 GPU-hours. The old grid is not authorized. Pending reservations charge every possible allocated GPU for the entire session timeout. Completed rows charge the larger of process lifetime and the final execution-log timestamp, multiplied by observed GPU count; quota snapshots retain the separate provisioning and billing evidence.

| Run | Purpose | Requested GPU | Observed devices | Status | Session timeout, s | Reserved or observed device-hours |
| --- | --- | --- | --- | --- | --- | --- |
| calibration-t4 | calibration | NvidiaTeslaT4 | Tesla T4, Tesla T4 | fetched | 1500 | 0.151705 |
| calibration-p100 | calibration | NvidiaTeslaP100 | Tesla T4, Tesla T4 | fetched | 900 | 0.010439 |
| main-session-1 | sweep | NvidiaTeslaT4 | Tesla T4, Tesla T4 | fetched | 2200 | 0.959992 |
| calibration-mha-fixed | calibration | NvidiaTeslaT4 | Tesla T4, Tesla T4 | fetched | 900 | 0.101959 |
| main-session-2 | sweep | NvidiaTeslaT4 | Tesla T4, Tesla T4 | fetched | 2200 | 0.918704 |
| calibration-llama-mirror | calibration | NvidiaTeslaT4 | Tesla T4, Tesla T4 | fetched | 900 | 0.073515 |
| llama-mirror-control | sweep | NvidiaTeslaT4 | Tesla T4, Tesla T4 | fetched | 6000 | 2.929955 |
| qwen-3b-control | sweep | NvidiaTeslaT4 | Tesla T4, Tesla T4 | fetched | 3000 | 1.465243 |
| main-session-3 | sweep | NvidiaTeslaT4 | Tesla T4, Tesla T4 | fetched | 2200 | 0.963603 |
| main-repeated-control | sweep | NvidiaTeslaT4 | Tesla T4, Tesla T4 | fetched | 730 | 0.255995 |
| phi2-control | sweep | NvidiaTeslaT4 | Tesla T4, Tesla T4 | fetched | 2130 | 0.929553 |
| pythia-control | sweep | NvidiaTeslaT4 | Tesla T4, Tesla T4 | fetched | 1430 | 0.555226 |
| opt-control | sweep | NvidiaTeslaT4 | Tesla T4, Tesla T4 | fetched | 900 | 0.330194 |
| qwen-half-control | sweep | NvidiaTeslaT4 | Tesla T4, Tesla T4 | fetched | 620 | 0.254834 |

Observed usage plus active reservations: 9.900916 GPU-hours. Unreserved phase-two allowance: 0.099084 GPU-hours.

All values and submission settings are recorded in `outputs/phase2_ledger.json`. A model must complete a short calibration before its full sweep is submitted. Across-session main-model runs remain separate statistical groups.

## Combined study total

Pilot plus redesigned phase: **10.037566 conservative GPU-hours**. Remaining weekly allowance on this accounting basis: **19.962434 GPU-hours**. Source: `study_budget_summary` in `outputs/results.jsonl`; the completed phase is stopped.

## Phase three: Modal

Main targets share a hard cap of $6. Optional H100 has a separate $4 cap and at most thirty minutes total. List-price estimates count CPU, capped RAM, GPU, initialization and teardown; credits are not deducted. A separate infrastructure reservation covers image building, temporary storage and result transfer. Tariffs are captured from [Modal pricing](https://modal.com/pricing) at submission.

| Run | GPU | Purpose | Status | Observed function wall seconds | Reserved or estimated USD |
| --- | --- | --- | --- | --- | --- |
| preload | CPU | prepare | failed_reservation_retained | Pending | 0.046420 |
| preload-retry | CPU | prepare | failed_reservation_retained | Pending | 0.046420 |
| preload-fixed | CPU | prepare | collected | 175.49629664421082 | 0.010392 |
| calibration-l4-main | L4 | calibration | submitted | Pending | 0.186780 |
| calibration-a10-main | A10 | calibration | submitted | Pending | 0.232020 |

Main usage plus reservations: $0.722032 / $6. H100: $0.000000 / $4. Infrastructure reservation: $0.200000.

Measured wall time excludes provider initialization; the estimate adds a conservative initialization/teardown allowance. Provider billing snapshots are retained separately. No unmeasured invoice amount is claimed.
