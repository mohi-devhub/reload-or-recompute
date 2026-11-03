# Phase three: preregistered hardware transfer

This phase is authorized for L4 and the Modal A10/A10G allocation, with a combined Modal cap of $6. An optional single H100 container session has a separate ceiling of $4 and at most thirty minutes including initialization and waiting for registration. No credits are subtracted from estimated list-price costs. CPU, RAM, initialization, idle time, output transfer, and temporary storage are included in reservations. Prices are captured from [Modal pricing](https://modal.com/pricing) at submission.

## Unchanged measurements

The phase-two `timed`, `flat_reload`, nested `forward`, and nested `request` functions are protected by source-text hashes checked against the executed T4 source. A platform adapter supplies GPU allocation checks, PCIe telemetry, output persistence, and scheduling. It does not change these timed functions. The full source difference and protected hashes are recorded. Every GPU uses fp16 and the same efficient/math SDPA backend selection, without FlashAttention. Checkpoints, Torch 2.11.0+cu130, and Transformers 4.51.3 are pinned.

Cache files live on container-local scratch. Model weights and copied logs use separate persistent volumes. File eviction remains per-file advisory DONTNEED; physical read counters are retained. Separate direct torch-load microbenchmarks calibrate its combined CPU load leg without substituting the slower staged BytesIO deserialization path.

## Calibration and frozen predictions

Calibration measures only prefix prefill, full recompute, resident-hit TTFT, and independent transfer/file microbenchmarks. It does not measure simulated-rate TTFT or real reload TTFT. Baselines have three measured rounds plus one warmup. Microbenchmarks have five repeats. Every model receives the original sustained warmup.

Calibration prefix anchors are 64, 1024, 8192 for Qwen1.5B and Qwen3B; 64, 512, 1024 for the Llama mirror; and 64, 512, 2016 for Pythia and Phi-2. Qwen1.5B uses both requested new-turn sizes; controls use 32. These are configuration choices, not measured observations.

For prefix-only and recompute baselines, fit a nonnegative quadratic time model `a + b L + c L²` independently for each model and new-turn size. GPU-hit baselines use a nonnegative affine model `a + b L`. Fit only the new GPU's three calibration anchors using least squares over all nonnegative active coefficient sets. Scale the length axis by the largest calibration anchor for numerical stability. These fixed model classes include a fixed-cost term and permit attention growth without consulting sweep data or T4 time curves. Report anchor, interpolation, and extrapolation scores separately; a poor shape extrapolation is a limitation of the prefill predictor rather than evidence about bandwidth alone. T4 data are used only for the comparison and hypothesis-level ratios.

Fit nonnegative affine time-versus-bytes functions to independent pinned/pageable H2D, staged raw/torch read and deserialization legs, and direct torch-load CPU/H2D microbenchmarks. The pinned fit intercept supplies the existing overhead term. For a paced condition use `predicted_hit + KV_bytes / target_rate + overhead`; the pacing/allocation overlap remains the approximation declared in phase two. For unthrottled and real paths use the independently calibrated complete transfer/file legs plus predicted hit.

Write every predicted decision and TTFT, and `B* = KV_bytes / (predicted_recompute - predicted_hit - overhead)`, to immutable JSON plus `docs/PREDICTIONS_<GPU>.md`. Commit before starting that GPU's sweep. Submission checks the prediction file hashes against the commit. Sweep microbenchmarks are retained as observations but cannot update predictions. No model or coefficient selection after seeing sweep outcomes.

## Grid and exclusions

The requested grid is retained in a machine-readable plan. "Longest native" means native total context minus the new-turn size. Native-limit prefixes not supported by the frozen text or projected reference-path memory footprint are explicitly listed as dropped, with one row per affected condition. A representative successful tensor footprint and model config from phase two supply the memory arithmetic; it is not an observed OOM. The Llama native limit requires several simultaneous caches beyond a 24 GB allocation, so its native-limit point is excluded rather than silently substituted. Budget reductions start with the largest models' longest prefixes. Prefix-only and recompute are baselines; the unthrottled chunked pinned path is also the real pinned-RAM control and is scored once.

Full sweeps retain ten measured randomized rounds after one warmup. Main-model sessions use separate containers and preserve individual medians/CIs and the range of session medians. GPU UUIDs identify whether physical devices were reused. Actual allocated names and compute capabilities take precedence over requested labels. Modal's API calls its Ampere allocation `A10`; any A10 versus A10G naming difference is reported.

## Scoring and hypothesis

Score reload/recompute decisions against paired-round bootstrap intervals for path-minus-recompute TTFT; unresolved intervals do not enter the correct/total decision score. Report median absolute relative TTFT error over all complete predicted cells, plus per-path scores. Observed crossovers are adjacent measured simulated-rate brackets, with achieved endpoints and endpoint-CI flags; harmonic interpolation is supplementary and assumes local inverse-bandwidth linearity.

Pre-register the hypothesis-level ratio as the calibration-predicted prefill-throughput ratio relative to T4. Afterward compare observed crossover-ratio intervals with that frozen ratio at matched model/workload/length/turn cells. Also show sweep-measured throughput ratios, without using them to revise predictions. Dividing two prefix-only formula estimates is an algebraic identity and is not evidence that the hypothesis holds. Censored or unresolved crossovers cannot establish an exact ratio.

No optional H100 run starts until both main targets finish under their cap. A strict H100 allocation request prevents automatic H200 substitution. If run, one container performs calibration, waits for the committed prediction release, and then performs the sweep within its total session deadline. A free P100 retry may be attempted once; another T4 allocation ends those attempts.

Stop after the final report and artifact checks. No subsequent experiments are authorized by unused allowance.
