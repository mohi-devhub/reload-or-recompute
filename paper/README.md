# Local manuscript draft

Check out `paper-v0.1.2` for this manuscript revision. Data reproduction uses the separate `v0.1.0-data` tag, which has no manuscript directory.

The manuscript uses only the frozen `v0.1.0-data` measurements and its `docs/CLAIMS.md`. Citation metadata was checked against primary sources separately; those checks add no experiment results. No GPU jobs are needed to build or audit it.

Compile from this directory with a standard TeX installation:

```sh
pdflatex -interaction=nonstopmode -halt-on-error -no-shell-escape main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error -no-shell-escape main.tex
pdflatex -interaction=nonstopmode -halt-on-error -no-shell-escape main.tex
```

Or run `python3 scripts/build.py`; `--tex-bin` and `--texmf-home` allow an existing local toolchain outside PATH. Citations use numeric natbib with a BibTeX bibliography before the appendix. The setup follows grammar-vs-bits: standard article, Latin Modern, letter paper and the same margins, changed to one column. It uses standard packages and does not need shell escape or an arXiv style download.

The generated TeX and copied figure PDFs make compilation self-contained. The provenance/coverage scripts additionally require this repository and its immutable data tag:

```sh
python3 scripts/generate_evidence.py
python3 scripts/audit_numbers.py
python3 scripts/write_briefing.py
```

`scripts/audit_numbers.py` checks macro coverage, release/figure hashes and numeric-literal classification; it does not recompute every statistic. The independent recomputation is recorded in the root `AUDIT.md`.

`NUMBERS.md` maps every empirical macro use to its release source and distinguishes identifier, bibliography, formula and layout numbers. `generated/number_registry.json` retains raw values. `DATA_SOURCES.json` records release-file hashes. `CITATIONS.md` records verified titles, authors, versions, venues, dates and model-report qualifications; `sources/references_catalog.json` preserves primary-source evidence and full author lists; `scripts/prepare_citations.py` recreates BibTeX offline from that metadata.

The scorecard and short-context figures are unchanged released PDFs. The bandwidth-versus-GPU figure has a plain-language legend, and the throughput figure has a legible two-column panel layout and plain-language legend. Both use released renderers and observations, without new points or refitting. `scripts/print_bandwidth.py` and `scripts/print_prefill.py` reproduce those presentation changes; their metadata in `generated/` records the hashes.

`BRIEFING.md` explains every section, figure and used numerical entry. The introduction gives a problem-level motivation, and two alternative titles remain LaTeX comments. `BUILD.json` records compilation, PDF pagination, and both LaTeX and BibTeX warnings. The manuscript is versioned by its GitHub tag; arXiv submission and Zenodo release remain separate author actions.
