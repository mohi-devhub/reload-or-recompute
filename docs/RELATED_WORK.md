# Related work: Reload or Recompute

Reviewed before benchmark implementation. Sources were checked on November 2, 2026. This is a bounded literature search, not proof that no other matching experiment exists. Paper identifiers, dates, and hardware names below are source metadata; they are not measurements from this project. No published performance numbers are adopted as our results.

## Scope and decision

Loading cached KV instead of computing a prefix is established practice. Neither that idea, hardware-dependent break-even lengths, nor the expectation that slower prefill can favour loading is a novelty claim here. The proposed contribution is an independently reproducible characterization on older commodity GPUs, with pinned/pageable/file controls and an independently calibrated bandwidth rule. A T4 pilot can check feasibility; it cannot establish transfer across GPU types or a causal GQA advantage.

No exact match to that experiment was found in the sources below. Proceed with the pilot. The closest work, py-kvcache, substantially narrows the contribution. If this becomes a paper, present it as replication and extension and compare its prediction method explicitly.

## Required systems and papers

### LMCache

[LMCache paper](https://arxiv.org/abs/2510.09665) and [official documentation](https://docs.lmcache.ai/) describe an external KV layer for inference engines, including CPU memory, files, and remote storage. Connectors, transfer batching, and overlap make its cost different from a Python tensor-copy loop. The production path therefore tests a separate implementation; its failure would limit generalization from the reference path. [Current installation prerequisites](https://docs.lmcache.ai/getting_started/installation.html) are not evidence that every wheel or kernel supports T4. Record the actual stack and error.

### CacheGen

[CacheGen: KV Cache Compression and Streaming for Fast Large Language Model Serving](https://arxiv.org/abs/2310.07240) compresses and streams saved KV states, adapting compression to bandwidth. It establishes the computation-versus-transfer tradeoff and shows why bytes per token matter. Our initial reference experiment uses uncompressed KV, so compression results are a different comparison with additional encoding and quality considerations.

### CacheBlend

[CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion](https://arxiv.org/abs/2405.16444) reuses cached text chunks and selectively recomputes states to recover cross-chunk attention. A returning conversation with an identical prefix is simpler: exact prefix KV reuse needs no approximate chunk fusion. [LMCache's CacheBlend documentation](https://docs.lmcache.ai/kv_cache_optimizations/cacheblend.html) describes the implemented integration.

### Cake

[Compute Or Load KV Cache? Why Not Both?](https://arxiv.org/abs/2410.03065), by Jin, Liu, Zhang, and Mao, overlaps computation from the start of a prefix with loading from its end. The [initial full text, experimental setup](https://arxiv.org/html/2410.03065v1#S5.SS1) uses A100 and H100 systems and controlled I/O bandwidth. It directly precedes the research question, including the influence of available compute and context length. This project tests a simpler whole-prefix choice on T4 and potentially P100, rather than proposing a replacement for Cake's hybrid scheduler. The hardware statement here is tied to the inspected initial version.

### vLLM prefix caching and offload

[Automatic prefix caching](https://github.com/vllm-project/vllm/blob/main/docs/features/automatic_prefix_caching.md) skips prefill for matching cached prefixes. A GPU hit is a useful lower latency bound. [Native KV offloading](https://github.com/vllm-project/vllm/blob/main/docs/features/kv_offloading_usage.md) extends reuse to pinned CPU memory and secondary tiers using asynchronous DMA. Weight offload settings must not be mistaken for reusable-prefix KV offload. Current upstream documentation does not describe every historical package version; record the pilot's versions separately.

### SGLang HiCache

[HiCache system design](https://docs.sglang.io/docs/advanced_features/hicache_design) extends RadixAttention through GPU memory, host memory, and external storage. Prefetch, storage policies, and layer-wise transfer alter the latency on the request path. HiCache already serves repeated-prefix and multi-turn use cases, so hierarchical conversation caching is not a new application claim.

## Newer and especially close work

### py-kvcache: closest overlap

[Building py-kvcache: A Performance Characterization of External KV Caching for vLLM with NVMe SSDs](https://arxiv.org/html/2609.11744v1), by Kanichai, De Matteis, and Trivedi, measures CPU and NVMe reuse against recompute. Its setup uses RTX 4000 Ada and H100 systems and includes Llama and Qwen models. It already studies hardware-dependent break-even frontiers, weaker-versus-faster GPUs, and an offline threshold per model and tier. Its criterion combines cached-prefix cost with uncached-tail prefill. This overlaps the central question and slower-GPU hypothesis, but does not provide the proposed T4/P100 reference-path study. A defensible extension needs measured older-hardware behavior and out-of-sample prediction checks; a fitted crossover alone is insufficient.

### Storage semantics and hidden cache hits

[Characterizing Predictability–Throughput Trade-offs of KV-Cache SSD Offloading in LMCache for LLM Serving Systems](https://arxiv.org/html/2610.21249v1) traces buffered versus direct storage paths. It warns that apparent file reads can be page-cache hits and that partial chunks amplify I/O. Consequently, report cache-eviction permissions and per-process physical read counters. An eviction hint without evidence cannot establish a cold-disk result. The work compares deployment snapshots, which should not be treated as a controlled version ablation.

### Other adjacent work

[KVServe](https://arxiv.org/abs/2605.13734) selects KV compression profiles using a latency model and online adaptation for disaggregated serving. [ShadowServe](https://arxiv.org/abs/2509.16857) addresses interference during distributed prefix fetching. These reinforce that bulk bandwidth alone may miss coordination and contention. Neither abstract reports the requested older-GPU reference experiment.

## Implications for measurement

Measure end-to-end resumed-turn latency through first-token selection, including file loading, host staging, synchronization, and the new turn. Also measure prefix prefill and isolated transfer separately. A reload estimate must add the resumed-turn cost when compared with end-to-end recompute. Disk-to-GPU has a disk-read leg and a host-to-device leg unless the implementation demonstrably overlaps them.

Calibrate bandwidth and fixed overhead from microbenchmarks, not the TTFT outcomes being predicted. Report prediction error and observed sign of the advantage. With only a sparse pilot grid, a crossing is an interval; all observed points favouring one side gives a bound, not an invented crossover. A one-GPU pilot cannot validate the cross-hardware hypothesis.
