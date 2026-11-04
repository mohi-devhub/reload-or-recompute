# Pre-arXiv audit

Audited on 2026-11-03. Manuscript commit: `a7e4e2a7e4d765887f8048dd2d5a4e1d48c447cc`. Data: annotated tag `v0.1.0-data`, peeled commit `691cfe1006482468891a23114e4b93bcb3eb9dd0`. Reviewed PDF SHA-256: `bc47dcd3c135ab1ab1b4e78fcb3a17c3588d2cbbb7fdcf16fc57809e99cf4ed4`.

**Recommendation: revise before submission.** No numerical mismatch was found in the 291 used entries in `paper/NUMBERS.md`. The principal issues concern interpretation, figure captions, and positioning. The PDF still contains an author placeholder. Compilation succeeds, but is not warning-free. No paper file was changed, no experiment was run, and no GPU service was invoked.

## Findings, ranked by severity

### 1. High: zero physical-read counters do not establish page-cache residency

**Location:** PDF p. 4, Section 3.5; `paper/main.tex:119`.

The sentence "Modal's were page-cache resident" is stronger than the observation. The released evidence establishes **0/4,575 positive process physical-read counters**, alongside an unverified virtualized file path. It does not locate the cache satisfying those reads. The following qualification helps, but does not undo the opening assertion or the residency assertion embedded in the chosen tier name.

The [Linux kernel's description of `read_bytes`](https://docs.kernel.org/filesystems/proc.html#proc-pid-io-display-the-io-accounting-fields) ties its accounting to the block-I/O submission layer and specifically qualifies its filesystem coverage. This study has neither a validated counter interpretation for the Modal file path nor a successful warm-versus-evicted comparison.

**Recommended correction:** lead with "physical reads were not observed" and describe page-cache residency as an interpretation, with the actual cache layer unverified. If the established tier name must remain, explicitly distinguish that label from a demonstrated cache state. Retain the Kaggle finding: **7,762/7,762** positive counters support accounted reads beyond page-cache-only hits, with the existing qualification that these are not device traces. The platform comparison cannot isolate a physical-storage effect.

### 2. High, editorial: the submission PDF contains an unfinished author paragraph

**Location:** PDF p. 1, Introduction; `paper/main.tex:34` and `paper/main.tex:35`; reiterated in Appendix C.

The bracketed instruction beginning "Author placeholder" is visible in the PDF. This was deliberately reserved for the author, but remains submission-blocking unfinished text.

**Recommended correction:** supply the author's paragraph or remove the placeholder and the appendix's note about it. This requires no new measurements.

### 3. Moderate: the closest prior work already includes offline calibration and bandwidth frontiers

**Location:** PDF pp. 1 and 8, contributions and Related work; `paper/main.tex:40`, `paper/main.tex:192`, and `paper/main.tex:194`.

The explicit disclaimer of novelty for reuse, offload, thresholds, and compute-versus-load choices is appropriate. However, the description of py-kvcache omits its **Section 6.6 offline per-node/model calibration**, with no fitting during serving. Its Section 5.2 also presents break-even bandwidth frontiers. Thus, calibration followed by later decisions is already prior work. The defensible distinction is the timestamped, frozen **per-cell prediction evaluation on separate sweeps**, its short calibration and measured scope, rather than calibration or a hardware-dependent rule itself. [py-kvcache, Sections 5.2 and 6.6](https://arxiv.org/html/2609.11744v1).

Cake is also broader than the current overlap-only summary: it compares equivalent compute bandwidth across GPUs, uses simulated I/O bandwidth, and evaluates MHA and GQA models. Those methods and qualitative relationships should not be presented as new here. The narrow commodity/older-GPU measurements and prospective prediction assessment remain useful extensions. [Cake, Sections 4 and 5](https://arxiv.org/html/2410.03065v2).

**Recommended correction:** state those overlaps explicitly. Also replace "the whole-prefix boundary such methods split around" with a precise endpoint comparison: this rule compares load-only and recompute-only paths; it does not determine Cake's optimal partial-compute/load split. I found no explicit claim that this study invented either system's mechanism, and no claim to have tested overlap.

### 4. Moderate: Figure 4's caption does not describe the prediction curve's x-coordinate

**Location:** PDF p. 7, Figure 4; `paper/main.tex:168`; released renderer `scripts/report_phase3.py:273` and `scripts/report_phase3.py:296`.

The caption says "versus measured prefill throughput." Observation markers do use measured throughput. Dashed prediction curves instead use **`predicted_prefill_tokens_s`** on the x-axis and predicted break-even bandwidth on the y-axis. For example, the A10G Qwen2.5-3B longest-context point uses different measured and calibration-predicted prefill throughputs. Horizontal and vertical differences therefore mix two prediction errors; the vertical separation is not a bandwidth prediction error at a common measured x-coordinate.

**Recommended correction:** explain both x-coordinate definitions in the caption. Alternatively, plot each frozen bandwidth prediction at its matched observed throughput and explain that presentation choice. Do not refit predictions. The plotted values match the released renderer; this is a caption/interpretation mismatch, not altered data.

### 5. Moderate: Figure 2 implies that an unobserved finite crossover exists

**Location:** PDF p. 5, Figure 2 caption; `paper/main.tex:136`. Related wording appears in Figure 4.

"Upward triangles mark a crossover above the highest tested rate" implies eventual crossing. The observations only establish that recomputation remained faster through the tested rates. Section 2 correctly allows a nonpositive denominator and **no finite predicted crossover**. The released H100 main-model result at prefix **1,024**, turn **32**, is a concrete example: its predicted `B*` is null and its largest tested achieved rate is **49,319.886 MB/s**. That observation cannot distinguish a later crossover from no finite crossover.

**Recommended correction:** describe triangles as "recompute faster through the highest tested rate; crossover not located." Likewise qualify below-grid markers as observations over the tested rates. These are sampled, median-based limits, not confidence bounds or proof of an eventual crossing.

### 6. Moderate: A10/A10G separation is correct, but calibration provenance and causal wording need tightening

**Location:** PDF p. 2, Section 3.1; p. 6, session variability; pp. 10–11, Appendix B.

The tables and figures correctly separate **A10, PCIe generation 4 x16**, from **A10G, generation 4 x8**. The numerical scores are not pooled. However:

- The Ampere calibration GPUs were **A10**. Their frozen predictions were subsequently tested on both A10 and A10G. "Calibration on each new GPU" can suggest an A10G-specific calibration that did not occur. Appendix B explains the API-tier registration but does not state this board provenance plainly.
- "These allocation differences are the likely source" of the spread gives a causal ranking unsupported by the design. The **23.611% / 22.664%** recompute ranges compare different boards and hosts. In particular, link width alone does not explain a fresh-prefill slowdown. The paper correctly acknowledges that sampled SM clocks did not explain it either.
- T4's recompute range uses **three sessions**, L4's **two**. These descriptive ranges are not a controlled estimate of relative platform stability.

**Recommended correction:** say "A10 calibration, transferred unchanged to A10 and A10G" and describe the spread as confounded by board/host/link differences, without identifying a likely cause. Keep the observed ranges and separate board rows.

### 7. Moderate: several "exact selectors" are descriptive or nonexistent fields

**Location:** `paper/NUMBERS.md`; `paper/scripts/generate_evidence.py`; `paper/scripts/audit_numbers.py`.

All used values check out, but the map is not uniformly executable as advertised. **16 used keys** have generic selectors such as "released measurement protocol / referenced canonical analysis metadata" or "prefix or new-turn length present in coverage." `ModelCount` points to `phase2_report_totals.model configurations`, which is not a field. Hypothesis selectors such as `.RatioYes` are registry aliases rather than fields in the cited records. Coverage session values require counting a list, which the selector does not say.

The existing audit checks macro uses, source hashes, figure hashes, and literal classification. It does **not** recompute most statistics or execute these selectors. Some claim-derived numbers are hard-coded in the generator and checked only for textual membership in the released document.

**Recommended correction:** provide actual row predicates, field names, and aggregation/rounding operations. Describe the current script as a provenance/coverage check unless it is extended to recompute values. This is a reproducibility weakness, not a numerical discrepancy; the independent checks below found none.

### 8. Moderate: the paper leaves important calibration choices in the artifact

**Location:** PDF p. 3, Section 3.4; pp. 7–8, practical guidance and limitations.

"A few lengths" does not tell the reader which observations support interpolation and which predictions extrapolate. The main-model calibration anchors are **64, 1,024, and 8,192 tokens**. The three-parameter quadratic fit and these anchors matter directly to the long-context failure. The paper also leaves the exact fixed-overhead identification and path-specific sums implicit in the generic equation.

**Recommended correction:** add a compact appendix description or explicit artifact pointers for calibration anchors by model, the pinned-transfer intercept used for fixed overhead, and the cost legs used by each file path. Clarify that "new turn" is a fixed-length token continuation of clipped, role-labelled text, not necessarily a complete user message at a dialogue boundary. The synthetic/stitched-workload caveat is already present and should remain.

### 9. Low: Figure 1 needs a self-contained coverage warning

**Location:** PDF p. 4, Figure 1.

The bars and annotations match the release. However, the H100 bar is labelled simply "H100," and the caption does not say the run is partial. Its **26 complete cells**, versus **767 L4**, **260 A10**, and **507 A10G** cells, represent unequal coverage. A10 has only the main model, while L4 and A10G include controls. This is explained in surrounding prose and the appendix, but a detached figure can suggest a comparable hardware ranking. Decision counts also include GPU-resident hits, while error includes baseline conditions.

**Recommended correction:** put "partial" and the unequal-coverage qualification in the caption, and make the scored decision types explicit. Do not interpret the bars as a ranking of GPUs or model-family transfer accuracy.

### 10. Low: successful compilation is not a warning-free build

**Location:** `paper/references.bib`; `paper/scripts/build.py`; `paper/BUILD.json`.

The isolated build produces three BibTeX warnings: missing author or sorting key for `vllmprefix`, `vllmoffload`, and `hicache`. A neutral `key` field can fix sorting without inventing an individual author. There is also the expected `epstopdf` warning with shell escape disabled.

`BUILD.json` records only the latter because the build script collects warnings from `main.log`, not the BibTeX output. Its warning inventory is incomplete, although the PDF builds successfully and all citations resolve.

### 11. Low: one primary source has inconsistent titles

**Location:** bibliography entry `fileobservability`, PDF reference [4]; `paper/CITATIONS.md` already notes this.

The bibliography exactly matches the [arXiv landing-page title](https://arxiv.org/abs/2610.21249v1), which says **Predictability-Latency**. The same version's [experimental HTML title](https://arxiv.org/html/2610.21249v1) says **Predictability–Throughput**. Authors, identifier, and year agree. This is a source inconsistency, not an invented reference; a single unambiguous title across those representations cannot be verified. Retain the recorded discrepancy and use the landing-page metadata consistently unless the source is corrected.

### 12. Low: appendix reproduction wording omits a figure change and a manuscript version

**Location:** PDF p. 11, Appendix C; `paper/main.tex:227`.

The appendix says only the throughput figure was reflowed. The GPU-bandwidth figure also has a changed legend. Both changes are documented in `NUMBERS.md` and preserve released data, but the appendix's preservation statement should mention both.

The commands correctly target the data tag. That tag contains no `paper/` directory. The later explanation acknowledges a local manuscript draft, but provides no manuscript commit to check out before the subsequent paper compilation commands. Separate data reproduction from manuscript reproduction and identify the latter version when the submission sources are made available.

## Numerical recomputation

### Method and coverage

I read the release through `git show v0.1.0-data:<path>`, rather than trusting working-tree copies of results. The compressed archive expands to **127,231,839 bytes**, with SHA-256 `4c764d39510a88c5b7b9814be41ab614390d7fd0797e88b0000eb448d67fab75`, matching its release manifest.

Independent CPU-only audit scripts were written under ignored `outputs/raw/paper-audit/`. They do not import the paper's number generator or overwrite manuscript artifacts. The listed source predicates were followed; where selectors were descriptive, the actual predicate and calculation are recorded in `numbers_result.json`.

| Entries in NUMBERS.md | Count | Independent check | Mismatches |
| --- | ---: | --- | ---: |
| Coverage cells | 96 | Completed raw recompute trials, prefix sets, turn lengths, distinct session IDs; compare all released coverage rows | 0 |
| Per-board scorecard table cells | 88 | Reaggregate canonical per-cell scores by observed board, region, and session; compare listed report line/column | 0 |
| Model KV sizes | 7 | Recalculate `2 × layers × KV heads × head dimension × 2 bytes`; check recorded tensor sizes | 0 |
| Remaining values | 100 | Raw timing medians, counts, file counters, thresholds, residuals, spreads, frozen errors, protocols, and stated release selectors | 0 |
| **Total used entries** | **291** | **All checked at printed precision** | **0** |

There are **325 empirical macro occurrences**, and all **308 defined macros** match their registry rendering. The **17 unused registry entries** are not paper claims. Compound table cells count as entries, not as single scalar measurements.

Additional checks went beyond reading the released aggregates:

- Recomputed the raw medians and paired bootstrap decisions/intervals for all **1,560 complete Phase 3 prediction cells**, using the recorded seed and resampling procedure. Compared their predictions with the frozen JSON manifests. No disagreement.
- Recomputed all **1,302 individual Phase 2 simulated-rate classifications** and the independent pinned-transfer overhead fits. The raw-derived totals are **1,237/1,258** adjusted-rule agreements and **1,017/1,258** prefix-only agreements. No disagreement.
- Recomputed all **372 file-rule residual cells** from raw resident-hit timings and independent read, deserialization, and transfer microbenchmarks. No disagreement.
- Checked first-session-held-fixed T4 score aggregates against their individual prediction records, and recomputed session-spread statistics from raw recompute medians. No disagreement.
- Checked the required L4/A10 prediction commit times against sweep submission times and checked scored prediction values against the frozen registrations. They precede the sweeps and remain unchanged. A10G board separation does not change those predictions.

Selected cross-checks, at manuscript precision:

| Quantity | Recomputed value | Source calculation |
| --- | --- | --- |
| Pilot pinned / recompute TTFT, prefix 8,192, turn 32 | 73.724 / 1,737.026 ms | Median of valid raw `ttft` trials for each condition |
| L4 correct/resolved; median absolute TTFT error | 574/636; 3.203 ms | Observed-board score aggregation |
| A10 x16 | 192/206; 2.040 ms | Same aggregation, A10 only |
| A10G x8 | 398/426; 5.758 ms | Same aggregation, A10G only |
| Partial H100 | 20/21; 6.579 ms | Complete recovered cells only |
| Qwen2.5-0.5B example, prefix-only / adjusted threshold | 226.626 / 2,442.265 MB/s | Payload divided by corresponding measured time denominator |
| Torch-file residual, before / after deserialization correction | 11.78% / 3.097% | Median absolute relative residual across released cells |
| Raw-file residual, before / after correction | 3.107% / 3.086% | Same calculation for raw format |
| Kaggle / Modal positive physical-read counters | 7,762/7,762; 0/4,575 | Raw file measurement and microbenchmark observations |

The numerical match does not upgrade claim strength. In particular, broad rate brackets, same-session descriptive baselines, unresolved comparisons, and an unverified cache state retain their limitations.

Local audit records and rerun commands:

```sh
python3 outputs/raw/paper-audit/check_numbers.py
python3 outputs/raw/paper-audit/check_raw_phase2.py
```

Detailed outputs: `outputs/raw/paper-audit/numbers_result.json` and `outputs/raw/paper-audit/raw_phase2_result.json`. These are local audit artifacts, not additions to the frozen data release.

## Citation verification

Every research reference's full author list and order, exact landing-page title, identifier/version, and cited-version year were compared with the primary source. All match, subject to the title ambiguity in finding 11. The year policy is the year of the explicitly cited revision: CacheGen, CacheBlend, and Cake have earlier initial submissions, which does not invalidate their stated revision years. No unverified conference venue is asserted.

| Reference | Verified title | Identifier and cited year | Full author-list check |
| --- | --- | --- | --- |
| LMCache | LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference | [2510.09665v2](https://arxiv.org/abs/2510.09665v2), 2025 | 11/11 match |
| CacheGen | CacheGen: KV Cache Compression and Streaming for Fast Large Language Model Serving | [2310.07240v6](https://arxiv.org/abs/2310.07240v6), 2024 | 14/14 match |
| CacheBlend | CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion | [2405.16444v3](https://arxiv.org/abs/2405.16444v3), 2025 | 9/9 match |
| Cake | Compute Or Load KV Cache? Why Not Both? | [2410.03065v2](https://arxiv.org/abs/2410.03065v2), 2025 | 4/4 match |
| py-kvcache | Building py-kvcache: A Performance Characterization of External KV Caching for vLLM with NVMe SSDs | [2609.11744v1](https://arxiv.org/abs/2609.11744v1), 2026 | 3/3 match |
| File observability | Characterizing Predictability-Latency Trade-offs of KV-Cache SSD Offloading in LMCache for LLM Serving Systems | [2610.21249v1](https://arxiv.org/abs/2610.21249v1), 2026 | 8/8 match; HTML title differs |
| KVServe | KVServe: Service-Aware KV Cache Compression for Communication-Efficient Disaggregated LLM Serving | [2605.13734v1](https://arxiv.org/abs/2605.13734v1), 2026 | 12/12 match |
| ShadowServe | ShadowServe: Interference-Free KV Cache Fetching for Distributed Prefix Caching | [2509.16857v1](https://arxiv.org/abs/2509.16857v1), 2025 | 9/9 match |

The three official documentation references were also fetched and checked:

- [vLLM Automatic Prefix Caching](https://raw.githubusercontent.com/vllm-project/vllm/main/docs/features/automatic_prefix_caching.md): title and reuse description verified.
- [vLLM KV Offloading Usage Guide](https://raw.githubusercontent.com/vllm-project/vllm/main/docs/features/kv_offloading_usage.md): title, CPU tier, and offload/reload description verified.
- [SGLang HiCache System Design and Optimization](https://docs.sglang.io/docs/advanced_features/hicache_design): title and hierarchy description verified.

Individual authors, publication years, and arXiv identifiers are not supplied for those documentation pages and are appropriately not invented. Their URLs are moving documentation targets; the access date is recorded. Primary metadata comparisons are retained locally in `outputs/raw/paper-audit/citations/verification.json`.

## PDF, terminology, and artifact checks

I read all **11 rendered PDF pages**, including the references and appendix, and inspected all four figures in their page layouts. The isolated `pdflatex → bibtex → pdflatex → pdflatex` build succeeds and produces **8 main pages, 1 reference page, and 2 appendix pages**. Extracted text from the rebuilt PDF exactly matches the reviewed PDF. There are no undefined references/citations, overfull boxes, or observed clipped figures/tables. Finding 10 lists the actual warnings.

Figures 1 and 3 are byte-identical to the released PDFs. Figures 2 and 4 have the declared legend/layout changes, with recorded hashes and released renderer provenance. Their displayed scores, regimes, and rate brackets agree with the released evidence; findings 4, 5, and 9 concern how those plots are described.

The manuscript uses **simulated bandwidth** for paced-copy results and distinguishes target from achieved rates. No use of "disk" was found in the main PDF text. A10 and A10G remain separate in numeric tables and plotted series. The main terminology problem is the stronger-than-observed cache-residency assertion in finding 1.

Important caveats already present and supported include long-context extrapolation failure, lack of exact throughput-ratio scaling, confounded MHA/GQA comparisons, non-uniform MHA file outcomes, incomplete H100 coverage, no successful production-path result, fixed single-request fp16 scope, and the unexplained pilot anomaly. None should be removed to make room for the recommended clarifications.

## Secrets and private paths

Scanned **161 current tracked files**, **382 reachable historical blobs**, decompressed released result archives, PDF text, and PDF metadata. Checks covered common credential formats, credential-like literal assignments, private-key markers, credential filenames, and private home-directory paths. **No matching credentials or private home paths were found.** Public author email/ORCID and public model revisions are intentional identifiers, not secrets.

No tracked `.env`, `kaggle.json`, or private-key file was found. Ignore checks confirm `.env`, `kaggle.json`, and `outputs/raw/` are excluded. The scan never opened configured credentials outside the repository and never emitted candidate secret values. This is a scoped static scan, not a guarantee against every possible secret encoding.

Logs: `outputs/raw/paper-audit/security_scan.json` and `outputs/raw/paper-audit/credential_literals.json`. A before/after SHA-256 check confirms every tracked file under `paper/` is unchanged.
