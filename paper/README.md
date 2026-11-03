# Local manuscript draft

The manuscript uses only the frozen `v0.1.0-data` measurements and its `docs/CLAIMS.md`. Citation metadata was checked against primary sources separately; those checks add no experiment results. No GPU jobs are needed to build or audit it.

Compile from this directory with a standard TeX installation:

```sh
pdflatex -interaction=nonstopmode -halt-on-error -no-shell-escape main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error -no-shell-escape main.tex
pdflatex -interaction=nonstopmode -halt-on-error -no-shell-escape main.tex
```

Or run `python3 scripts/build.py`; `--tex-bin` and `--texmf-home` allow an existing local toolchain outside PATH. The setup follows grammar-vs-bits: standard article, Latin Modern, letter paper and the same margins, changed to one column. It uses standard packages and does not need shell escape or an arXiv style download.

The generated TeX and copied figure PDFs make compilation self-contained. The audit scripts additionally require this repository and its immutable data tag:

```sh
python3 scripts/generate_evidence.py
python3 scripts/audit_numbers.py
python3 scripts/write_briefing.py
```

`NUMBERS.md` maps every empirical macro use to its release source and distinguishes identifier, bibliography, formula and layout numbers. `generated/number_registry.json` retains raw values. `DATA_SOURCES.json` records release-file hashes. `CITATIONS.md` records verified titles, authors, versions, venues and dates; `scripts/prepare_citations.py` recreates BibTeX offline from that metadata.

Three figures are unchanged released PDFs. The throughput figure alone is reflowed to a legible two-column panel layout using the released renderer and observations, without new points or refitting. `scripts/print_prefill.py` reproduces that presentation change and `generated/figure_reformat.json` records its hashes.

`BRIEFING.md` explains every section, figure and used numerical entry. The introduction retains the requested author-motivation placeholder, and two alternative titles remain LaTeX comments. `BUILD.json` records compilation and PDF pagination. This is a draft for author review; no submission, upload or posting has been performed.
