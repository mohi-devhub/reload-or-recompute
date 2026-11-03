# Reload or Recompute

Pilot: Qwen2.5-1.5B on T4 favored reload in all 18 sampled reload-path comparisons; it did not identify a crossover length.<br>
Phase 2: seven fp16 models and 26,040 accepted timings established simulated-bandwidth crossovers and short-context overhead effects.<br>
Phase 3: frozen decisions scored 574/636 on L4, 192/206 on A10 at PCIe x16, and 398/426 on A10G at PCIe x8.<br>
The interrupted H100 run scored 20/21 resolved decisions; long-context extrapolation, exact throughput scaling and uniform MHA file-path transfer are not established.<br>
The data release is complete; no more GPU spending is authorized, and no paper has been written.

[Claims and exact evidence](docs/CLAIMS.md) · [Figure captions](docs/FIGURE_CAPTIONS.md) · [File API audit](docs/FILE_API_AUDIT.md) · [Budget](docs/BUDGET.md) · [Deviations](docs/NOTES.md)

Reload when `T_GPU_hit + fixed_overhead + transfer_bytes / effective_bandwidth + other_CPU_and_transfer_legs < T_recompute`; equivalently, use `B* = transfer_bytes / (T_recompute - T_GPU_hit - fixed_overhead - other_legs)` only for a positive denominator, counting read, deserialization and H2D costs once and treating near-zero savings as unresolved.

The Modal tier is the **local file API path (page-cache resident; physical reads not observed)**. Kaggle's file observations have positive process physical-read counters, so they use the qualifier **positive process physical-read counters; underlying storage and host cache unidentified**. Neither platform identifies physical media or isolates GPU speed from host effects. See the [counter audit](docs/FILE_API_AUDIT.md).

## Reproduce the released analysis without GPU work

```sh
git clone https://github.com/mohi-devhub/reload-or-recompute.git
cd reload-or-recompute
git checkout v0.1.0-data
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-analysis.txt
python3 scripts/materialize_results.py
python3 scripts/analyze_phase2.py --from-results outputs/results.jsonl
python3 scripts/report_phase2.py
python3 scripts/analyze_phase3.py --from-results outputs/results.jsonl
python3 scripts/audit_phase3.py
python3 scripts/report_phase3.py
python3 scripts/consolidate_study.py --check --figures
python3 -m unittest discover -s tests
```

The archive has both compressed and uncompressed SHA-256 checksums. Materialization refuses to overwrite a changed local JSONL. Consolidation verifies every numeric claim, evidence table and caption against the archive. It preserves the original record bytes and appends separately labeled presentation records. No coefficients are refitted. A10 and A10G remain separate by observed name and PCIe width; their model coverage differs. Their allocation differences are the likely source of the earlier service-tier spread, with causality unproved.

To regenerate the claim inventory after an intentional, reviewed data change, use:

```sh
python3 scripts/consolidate_study.py --figures
python3 scripts/materialize_results.py --pack
python3 scripts/consolidate_study.py --check
```

These commands use CPU only. Historical acquisition specifications and source hashes are retained in the ledgers and protocols. They document completed runs and do not authorize new paid work. Credentials remain outside the repository.

## Figures and source records

The [caption drafts](docs/FIGURE_CAPTIONS.md) link vector PDFs and PNGs for all four paper figures. Plot tables are `outputs/consolidated_crossovers.csv`, `outputs/consolidated_scorecard.csv`, and `outputs/consolidated_results.jsonl`. Sessions remain separate, and censored bandwidth bounds are not substituted with invented crossover points.

[The pilot report](docs/PILOT_REPORT.md), [phase-two report](docs/PHASE2_REPORT.md), and [phase-three report](docs/PHASE3_REPORT.md) retain the experimental context. The preregistrations in `docs/PREDICTIONS_*.md` and `configs/predictions_*.json` remain byte-identical to their pre-sweep commits. The six protected timing/transfer functions match the historical T4 source. Platform scheduling differences and executed source hashes are in [the source comparison](outputs/phase3_provenance.json).

Basic KV reuse and choosing reload versus recompute are established prior work. The [literature review](docs/RELATED_WORK.md) sets the novelty boundary. This release supports the claims in the inventory within their stated scope; it does not establish production-serving, P100, concurrency, or quantization results.
