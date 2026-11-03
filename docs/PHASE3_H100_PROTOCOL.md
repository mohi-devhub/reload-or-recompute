# Optional H100 protocol

The optional run starts only after all six L4/A10 full sweeps have been collected and completed under the main cap. The controller enforces one H100 allocation, a separate $4 ceiling, and a thirty-minute bound including initialization and the registration wait. `H100!` requests a strict H100 allocation, preventing automatic H200 substitution.

One container runs calibration, waits for the host to commit predictions, and then runs the registered sweeps. Child processes are logical stages within that allocation, not separate GPU sessions. GPU UUIDs and the shared container identifier verify this distinction. The parent deadline covers every stage and the waiting period; individual stage deadlines retain finalization margins.

Qwen2.5-1.5B uses the same frozen UltraChat fixture, prefixes 256, 1024, 4096 and 16384, and a 32-token new turn. Pythia-1.4B uses the repeated-text control at prefixes 256 and 1024. Its requested longer prefixes exceed its native context and are listed individually by condition in `configs/phase3_h100_plan.json`. All simulated rates, real paths and baselines match the other phase-three sweeps. Full cells retain ten randomized measured rounds after warmup.

Calibration uses the same predeclared model classes and independent microbenchmarks. Qwen anchors are 64, 1024 and 8192; Pythia anchors are 64, 512 and 2016. Both use the 32-token turn only. Calibration has three measured baseline rounds and five repeats for each transfer/file microbenchmark. No reload TTFT outcomes enter calibration fits.

After calibration, the host writes `configs/predictions_H100.json` and `docs/PREDICTIONS_H100.md`, projects both sweeps, and commits the files before uploading a release marker. Submission-time or calibration-time data cannot contain any tested reload TTFT. The release checks committed JSON/document bytes, manifest hash, GPU, planned models, workloads, lengths and turns. The parent refuses a release whose projected stages exceed its remaining time. No coefficients are changed after release.

The same protected reference functions, fp16 dtype, efficient/math SDPA backend selection, checkpoints, Torch and Transformers versions are retained. The additional code changes orchestration and provenance outside measured functions. File results retain the virtualized-filesystem limitation documented in NOTES.md.

Only the parent is charged in the budget ledger. Its nested logical stages retain individual specifications, durations, environment records and source hashes, without counting them as extra allocations. Reproduce the optional workflow after the main-grid prerequisites have passed:

```sh
python3 scripts/phase3_h100.py plan
python3 scripts/phase3_h100.py start
python3 scripts/phase3_h100.py follow
```

The follower collects calibration, freezes and commits predictions, releases the sweeps, and collects all stages. A failed calibration or missed release deadline ends the same bounded allocation. No second H100 allocation is authorized by this controller.
