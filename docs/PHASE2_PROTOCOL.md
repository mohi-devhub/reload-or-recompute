# Redesigned bandwidth study

The user authorizes this phase with a cap of 10 GPU-hours. This protocol replaces the original full-grid plan. Settings below are requested configurations, not observations.

## Scientific target

The principal comparison is measured resumed-turn TTFT against simulated transport bandwidth. For each model and prefix length, calculate `B*_prefix = KV bytes / measured prefix-prefill seconds`. Include fixed overhead and the GPU-hit new-turn baseline for an end-to-end threshold. The study asks whether these predictors bracket the observed bandwidth crossover. A GQA-versus-MHA association across different models does not isolate attention architecture from model width, parameter count, or implementation.

The prefix lengths are 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, and 16384 tokens. New turns contain 32 or 256 tokens. Exclude prefix-plus-turn lengths beyond the model's native context. Add the model's maximum-context-minus-longest-turn boundary to retain a useful near-limit measurement. Do not silently extrapolate position embeddings.

## Rate-limited copies are simulated bandwidth

Test decimal rates of 50, 100, 200, 400, 800, and 1600 MB/s, plus an unthrottled transport control. Pack the cache into a contiguous fp16 buffer and copy it in chunks. Synchronize each throttled chunk and sleep until the cumulative byte deadline. This emulates a serialized, blocking transport path; it does not emulate physical disk, packetization, queueing, or asynchronous storage overlap.

Record target rate, achieved transport rate, transfer duration, cumulative sleep time, payload bytes, and chunk size. Include GPU allocation in the measured transport cost. The resumed transformer must consume the copied tensors, with output logits and first token checked against full recomputation. Keep all simulated conditions explicitly labelled in data, figures, and reports.

## File-leg decomposition

Keep direct `torch.load` as a baseline. Add a staged torch-serialization path and a packed raw fp16 byte path. The staged paths read a file into a byte buffer, deserialize or construct a tensor view, and transfer to GPU, recording each leg. Raw-byte metadata and tensor shapes are held with the cache-layout record. The raw format uses a zero-copy CPU tensor view, then an actual H2D copy.

Independent microbenchmarks calibrate raw reads, deserialization, and H2D without a new turn. Compare old predictions omitting deserialization against predictions including it on the separate TTFT samples. Never fit file residuals back into the TTFT outcomes. Buffer allocation and the BytesIO copy belong to their measured legs. Advisory per-file eviction and physical-read accounting retain the pilot's storage caveats.

## Drift and uncertainty

Warm each model with sustained forward passes. Shuffle prefix lengths and new-turn lengths. Shuffle all conditions inside every measured round, including prefix-only prefill. Keep ten repeats for full sweeps and at least one warmup per condition. Short calibration runs have fewer repeats and are labelled calibration; they cannot supply publication confidence intervals.

Log GPU SM and memory clocks, temperature, power, utilization, and clock-throttling or clock-event reasons at approximately one-second intervals. The long-running nvidia-smi sampler runs beside the benchmark. Match samples to measurement start and end timestamps. A separate, excluded profile compares the pilot-anomaly matrix shapes after warming them.

Run the main model in three distinct Kaggle sessions. Preserve each session's median and bootstrap interval and report the spread between session medians. Do not pool repeated measurements across sessions and describe the resulting CI as across-session uncertainty. Three sessions provide limited evidence, not a precise population interval.

## Conversation source

Freeze a deterministic selection of complete multi-turn rows from [UltraChat 200k](https://huggingface.co/datasets/HuggingFaceH4/ultrachat_200k). It is public synthetic dialogue, rather than observed human chat. Preserve the dataset identifier, split, row IDs, source URL, selection rule, and fixture hash. Use plain role-labelled text and clip to the exact token count. Long contexts may concatenate distinct conversations with explicit role boundaries; record this as stitched conversation text. Keep the repeated-text pilot workload as a named control. No application-quality conclusion follows from these timing workloads.

## Budget gate

Calibrate every new model before its full sweep. Update BUDGET.md before every submission. The controller refuses an uncalibrated full sweep and reservations beyond the phase cap. Pending reservations use the session timeout multiplied by all possible allocated GPUs. Completed reservations are replaced with logged process device-hours and retained quota snapshots. Guard workers with a shorter timeout so the parent can finalize artifacts.

Try a reference-only P100 subset after checking its allocation and runtime. Production work is optional and may be omitted to protect reference coverage. Any attempted production work requires a Python environment compatible with its pinned packages and its own troubleshooting limit.

## Stop

After the redesigned grid, write PHASE2_REPORT.md with measured crossover brackets, predictions, GQA/MHA comparisons, short-length behavior, file residuals, clock findings, session spread, and a revised rule. Record unavailable models, unsupported GPUs, context limits, memory failures, and budget truncation as explicit deviations in NOTES.md. Do not turn these into fabricated measurements.
