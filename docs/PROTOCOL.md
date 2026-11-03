# Pilot measurement protocol

The measured file tier is a local file API path. Kaggle records positive process physical-read counters; underlying storage and host cache are unidentified. See [the counter audit](FILE_API_AUDIT.md).

The pilot requests Qwen2.5-1.5B on T4 in fp16. Prefix lengths are 512, 2048, and 8192 tokens. New turns contain 32 or 256 tokens. These values, the repeat counts, and timeout values are prescribed settings, not measured results.

## Measurement boundary

Input token IDs are already on the GPU. TTFT begins before prefix recomputation or cache acquisition and ends after the new-turn final logits select a token on the CPU. CPU and file conditions include GPU allocation, copies, and cache-container construction. The file condition includes `torch.load`. Model loading, tokenization, initial KV creation, cache writes, and network or queue delays are excluded. Prefix-only prefill and tensor-layout-matched transfers are measured independently.

`model.model` computes the full transformer with its cache. The language-model head operates on the final hidden state only. This avoids materializing unused full-prefix vocabulary logits. Every condition uses that same implementation. Torch SDPA enables its efficient and math backends and explicitly excludes the flash backend. No FlashAttention-2 package is installed for the reference path.

Each shape has two warmups and twelve measured rounds. The condition order is shuffled within each round using a fixed seed. CUDA synchronization encloses each operation. Wall time is the main metric; CUDA-event elapsed time is supplemental and can include GPU idle time during host or file work. Errors are recorded and stop reference measurements. A separate profile is excluded from timing summaries.

## Correctness

The prefix and turn are slices of fixed tokenized text representing alternating user and assistant messages. This is a controlled synthetic conversation, not a natural conversation corpus or a quality benchmark. Fresh recomputation provides reference logits and a greedy first token. Every timed result checks finite logits, a fixed fp16 allclose tolerance, first-token agreement, and the resulting cache length. Reused prefix tensor lengths must remain unchanged. Cache bytes from configuration must equal the sum of tensor bytes. H2D microbenchmarks verify exact tensor equality outside the timed region.

A GPU prefix remains allocated to supply the GPU-hit control and tensor verification. Recompute still executes the entire input. This reduces available VRAM uniformly and must be accounted for before interpreting memory-limit failures.

## File semantics

The file backend uses uncompressed `torch.save` and `torch.load`. File writeback is synchronized before reads. The script attempts global page-cache eviction and logs any permission error. Before each measured read it requests per-file eviction with `POSIX_FADV_DONTNEED`. This is advisory. Per-process `read_bytes` and serialized file sizes accompany observations. File results are not called cold physical-storage unless physical read evidence supports that description. The storage device behind Kaggle's filesystem is not assumed to be a local NVMe SSD.

## Inference and prediction

Report the sample median and a percentile bootstrap confidence interval for the median. Retain every individual timing. Infer a crossing interval only when the ordering changes between sampled lengths. Distinguish absent crossings, inconclusive intervals, and bounds outside the measured range.

Use microbenchmark copy time versus cache bytes to estimate effective bandwidth and fixed overhead independently of the TTFT outcomes. Compare prefix prefill against predicted reload cost. For resumed TTFT, add the measured GPU-hit new-turn time. The initial file estimate is the serial sum of measured file-read cost and pageable H2D cost; its residual also contains deserialization and allocation differences. This omission is a deliberate test of the simple rule, not an adjusted fit to force agreement. A sparse pilot cannot establish out-of-sample model or hardware transfer.

## Budget and stopping

The kernel timeout is 4800 seconds. At most two allocated devices are accepted, giving a conservative timeout ceiling below the user's pilot allowance. Reference installation and reference execution have separate limits. The production attempt uses a separate virtual environment, one pinned historical stack, and a wall-time bound that also caps allocated-device GPU time below the troubleshooting allowance. Installation and idle allocation count toward the ledger.

JSONL samples are flushed and fsynced after each observation. Restarting the reference process in the same working directory skips valid sample keys and rebuilds caches. Cross-session resume requires restoring the previous results file; different environments must remain separate experimental runs. A successful pilot requires the complete reference grid, correct outputs, interpretable timing and storage evidence, and a bounded production-path attempt. Production compatibility failure alone does not fail the pilot.
