# Numerical evidence map

All empirical values in the manuscript use `\N{key}` macros generated from **v0.1.0-data**. This map lists every use in the text, captions and appendix tables. Values are not fitted or replaced using later observations. Commas are thousands separators; retained precision follows the released claims or cited tables.

## Coverage

- 289 distinct source-mapped empirical values or table cells occur at 321 TeX locations.
- 306 registry entries are available; unused entries are not claims in the paper.
- 4 figure source/data mappings are verified. Three PDFs are byte-identical to the release; only the throughput figure is reflowed for legibility, with unchanged data and predictions.
- No unclassified numeric literal remains in manuscript TeX after the metadata and layout categories below.
- Regenerate the macros with `python3 paper/scripts/generate_evidence.py`; verify this map with `python3 paper/scripts/audit_numbers.py`.

## Empirical values and their uses

| Key | Printed value | Release file and exact selector | Claim | TeX locations |
| --- | --- | --- | --- | --- |
| A10Correct | 192 | `outputs/consolidated_scorecard.csv`: gpu=A10.correct_decisions | 9 | `main.tex:27`, `main.tex:117` |
| A10GCorrect | 398 | `outputs/consolidated_scorecard.csv`: gpu=A10G.correct_decisions | 9 | `main.tex:27`, `main.tex:117` |
| A10GExtrapError | 5,873.459 | `docs/CLAIMS.md`: claim 10 A10G recompute absolute error | 10 | `main.tex:159` |
| A10GExtrapObs | 13,914.555 | `docs/CLAIMS.md`: claim 10 A10G recompute observed | 10 | `main.tex:159` |
| A10GExtrapPred | 8,041.096 | `docs/CLAIMS.md`: claim 10 A10G recompute predicted | 10 | `main.tex:159` |
| A10GMAE | 5.758 | `outputs/consolidated_scorecard.csv`: gpu=A10G.median_absolute_ttft_error_ms | 9 | `main.tex:117` |
| A10GRatioTotal | 24 | `outputs/claims_evidence.json`: hypothesis_scorecards.gpu=A10G.RatioTotal | 11 | `main.tex:162` |
| A10GRatioYes | 20 | `outputs/claims_evidence.json`: hypothesis_scorecards.gpu=A10G.RatioYes | 11 | `main.tex:162` |
| A10GResolved | 426 | `outputs/consolidated_scorecard.csv`: gpu=A10G.resolved_decisions | 9 | `main.tex:27`, `main.tex:117` |
| A10GUnresolved | 3 | `outputs/consolidated_scorecard.csv`: gpu=A10G.unresolved_decisions | 9 | `main.tex:117` |
| A10MAE | 2.040 | `outputs/consolidated_scorecard.csv`: gpu=A10.median_absolute_ttft_error_ms | 9 | `main.tex:117` |
| A10RatioTotal | 12 | `outputs/claims_evidence.json`: hypothesis_scorecards.gpu=A10.RatioTotal | 11 | `main.tex:162` |
| A10RatioYes | 11 | `outputs/claims_evidence.json`: hypothesis_scorecards.gpu=A10.RatioYes | 11 | `main.tex:162` |
| A10Resolved | 206 | `outputs/consolidated_scorecard.csv`: gpu=A10.resolved_decisions | 9 | `main.tex:27`, `main.tex:117` |
| A10Unresolved | 14 | `outputs/consolidated_scorecard.csv`: gpu=A10.unresolved_decisions | 9 | `main.tex:117` |
| AdjustedCorrect | 1,237 | `outputs/claims_evidence.json`: phase2_report_totals.rule_counts.ttft_rule_agreements | 5 | `main.tex:135` |
| AmpereGeneration | 4 | `docs/PHASE3_REPORT.md`: active PCIe generation for A10 and A10G | 15 | `main.tex:80`, `main.tex:80` |
| AmpereSpreadLong | 22.664 | `docs/CLAIMS.md`: claim 15 N256 matched relative range | 15 | `main.tex:155` |
| AmpereSpreadShort | 23.611 | `docs/CLAIMS.md`: claim 15 N32 matched relative range | 15 | `main.tex:155` |
| AnomalyPairs | 4 | `docs/CLAIMS.md`: claim 21 comparisons | 21 | `main.tex:172` |
| Bootstraps | 10,000 | `outputs/results.jsonl.gz`: released measurement protocol / referenced canonical analysis metadata | 3 | `main.tex:104` |
| Boundary | 256 | `outputs/consolidated_coverage.csv`: prefix or new-turn length present in coverage | 3 | `main.tex:142` |
| CI | 95 | `docs/PHASE3_REPORT.md`: released measurement protocol / referenced canonical analysis metadata | 3 | `main.tex:104` |
| CalA10Seconds | 42.5 | `docs/PHASE3_REPORT.md`: calibration-a10-main wall seconds | 9 | `main.tex:179` |
| CalL4Seconds | 63.4 | `docs/PHASE3_REPORT.md`: calibration-l4-main wall seconds | 9 | `main.tex:179` |
| CalRepeats | 3 | `docs/PHASE3_PROTOCOL.md`: released measurement protocol / referenced canonical analysis metadata | 3 | `main.tex:106` |
| Cov0Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 1,792 | `outputs/consolidated_coverage.csv`: row 0.prefixes | 3 | `generated/coverage.tex:5` |
| Cov0Sessions | 1 | `outputs/consolidated_coverage.csv`: row 0.sessions | 3 | `generated/coverage.tex:5` |
| Cov0Turn | 32 | `outputs/consolidated_coverage.csv`: row 0.turn_tokens | 3 | `generated/coverage.tex:5` |
| Cov10Prefixes | 16, 32, 64, 128, 256, 512, 1,024 | `outputs/consolidated_coverage.csv`: row 10.prefixes | 3 | `generated/coverage.tex:15` |
| Cov10Sessions | 1 | `outputs/consolidated_coverage.csv`: row 10.sessions | 3 | `generated/coverage.tex:15` |
| Cov10Turn | 256 | `outputs/consolidated_coverage.csv`: row 10.turn_tokens | 3 | `generated/coverage.tex:15` |
| Cov11Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 1,792 | `outputs/consolidated_coverage.csv`: row 11.prefixes | 3 | `generated/coverage.tex:16` |
| Cov11Sessions | 1 | `outputs/consolidated_coverage.csv`: row 11.sessions | 3 | `generated/coverage.tex:16` |
| Cov11Turn | 32 | `outputs/consolidated_coverage.csv`: row 11.turn_tokens | 3 | `generated/coverage.tex:16` |
| Cov12Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 1,792 | `outputs/consolidated_coverage.csv`: row 12.prefixes | 3 | `generated/coverage.tex:17` |
| Cov12Sessions | 1 | `outputs/consolidated_coverage.csv`: row 12.sessions | 3 | `generated/coverage.tex:17` |
| Cov12Turn | 256 | `outputs/consolidated_coverage.csv`: row 12.turn_tokens | 3 | `generated/coverage.tex:17` |
| Cov13Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | `outputs/consolidated_coverage.csv`: row 13.prefixes | 3 | `generated/coverage.tex:18` |
| Cov13Sessions | 1 | `outputs/consolidated_coverage.csv`: row 13.sessions | 3 | `generated/coverage.tex:18` |
| Cov13Turn | 32 | `outputs/consolidated_coverage.csv`: row 13.turn_tokens | 3 | `generated/coverage.tex:18` |
| Cov14Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | `outputs/consolidated_coverage.csv`: row 14.prefixes | 3 | `generated/coverage.tex:19` |
| Cov14Sessions | 1 | `outputs/consolidated_coverage.csv`: row 14.sessions | 3 | `generated/coverage.tex:19` |
| Cov14Turn | 256 | `outputs/consolidated_coverage.csv`: row 14.turn_tokens | 3 | `generated/coverage.tex:19` |
| Cov15Prefixes | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | `outputs/consolidated_coverage.csv`: row 15.prefixes | 3 | `generated/coverage.tex:20` |
| Cov15Sessions | 1 | `outputs/consolidated_coverage.csv`: row 15.sessions | 3 | `generated/coverage.tex:20` |
| Cov15Turn | 32 | `outputs/consolidated_coverage.csv`: row 15.turn_tokens | 3 | `generated/coverage.tex:20` |
| Cov16Prefixes | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | `outputs/consolidated_coverage.csv`: row 16.prefixes | 3 | `generated/coverage.tex:21` |
| Cov16Sessions | 1 | `outputs/consolidated_coverage.csv`: row 16.sessions | 3 | `generated/coverage.tex:21` |
| Cov16Turn | 256 | `outputs/consolidated_coverage.csv`: row 16.turn_tokens | 3 | `generated/coverage.tex:21` |
| Cov17Prefixes | 64, 256, 512, 1,024, 2,016 | `outputs/consolidated_coverage.csv`: row 17.prefixes | 3 | `generated/coverage.tex:22` |
| Cov17Sessions | 1 | `outputs/consolidated_coverage.csv`: row 17.sessions | 3 | `generated/coverage.tex:22` |
| Cov17Turn | 32 | `outputs/consolidated_coverage.csv`: row 17.turn_tokens | 3 | `generated/coverage.tex:22` |
| Cov18Prefixes | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | `outputs/consolidated_coverage.csv`: row 18.prefixes | 3 | `generated/coverage.tex:23` |
| Cov18Sessions | 1 | `outputs/consolidated_coverage.csv`: row 18.sessions | 3 | `generated/coverage.tex:23` |
| Cov18Turn | 32 | `outputs/consolidated_coverage.csv`: row 18.turn_tokens | 3 | `generated/coverage.tex:23` |
| Cov19Prefixes | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | `outputs/consolidated_coverage.csv`: row 19.prefixes | 3 | `generated/coverage.tex:24` |
| Cov19Sessions | 1 | `outputs/consolidated_coverage.csv`: row 19.sessions | 3 | `generated/coverage.tex:24` |
| Cov19Turn | 256 | `outputs/consolidated_coverage.csv`: row 19.turn_tokens | 3 | `generated/coverage.tex:24` |
| Cov1Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 1,792 | `outputs/consolidated_coverage.csv`: row 1.prefixes | 3 | `generated/coverage.tex:6` |
| Cov1Sessions | 1 | `outputs/consolidated_coverage.csv`: row 1.sessions | 3 | `generated/coverage.tex:6` |
| Cov1Turn | 256 | `outputs/consolidated_coverage.csv`: row 1.turn_tokens | 3 | `generated/coverage.tex:6` |
| Cov20Prefixes | 64, 256, 512, 1,024, 32,736 | `outputs/consolidated_coverage.csv`: row 20.prefixes | 3 | `generated/coverage.tex:25` |
| Cov20Sessions | 1 | `outputs/consolidated_coverage.csv`: row 20.sessions | 3 | `generated/coverage.tex:25` |
| Cov20Turn | 32 | `outputs/consolidated_coverage.csv`: row 20.turn_tokens | 3 | `generated/coverage.tex:25` |
| Cov21Prefixes | 64, 256, 512, 1,024, 2,016 | `outputs/consolidated_coverage.csv`: row 21.prefixes | 3 | `generated/coverage.tex:26` |
| Cov21Sessions | 1 | `outputs/consolidated_coverage.csv`: row 21.sessions | 3 | `generated/coverage.tex:26` |
| Cov21Turn | 32 | `outputs/consolidated_coverage.csv`: row 21.turn_tokens | 3 | `generated/coverage.tex:26` |
| Cov22Prefixes | 64, 256, 512, 1,024 | `outputs/consolidated_coverage.csv`: row 22.prefixes | 3 | `generated/coverage.tex:27` |
| Cov22Sessions | 1 | `outputs/consolidated_coverage.csv`: row 22.sessions | 3 | `generated/coverage.tex:27` |
| Cov22Turn | 32 | `outputs/consolidated_coverage.csv`: row 22.turn_tokens | 3 | `generated/coverage.tex:27` |
| Cov23Prefixes | 1,024, 16,384 | `outputs/consolidated_coverage.csv`: row 23.prefixes | 3 | `generated/coverage.tex:28` |
| Cov23Sessions | 1 | `outputs/consolidated_coverage.csv`: row 23.sessions | 3 | `generated/coverage.tex:28` |
| Cov23Turn | 32 | `outputs/consolidated_coverage.csv`: row 23.turn_tokens | 3 | `generated/coverage.tex:28` |
| Cov24Prefixes | 64, 256, 512, 1,024, 2,016 | `outputs/consolidated_coverage.csv`: row 24.prefixes | 3 | `generated/coverage.tex:29` |
| Cov24Sessions | 1 | `outputs/consolidated_coverage.csv`: row 24.sessions | 3 | `generated/coverage.tex:29` |
| Cov24Turn | 32 | `outputs/consolidated_coverage.csv`: row 24.turn_tokens | 3 | `generated/coverage.tex:29` |
| Cov25Prefixes | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | `outputs/consolidated_coverage.csv`: row 25.prefixes | 3 | `generated/coverage.tex:30` |
| Cov25Sessions | 2 | `outputs/consolidated_coverage.csv`: row 25.sessions | 3 | `generated/coverage.tex:30` |
| Cov25Turn | 32 | `outputs/consolidated_coverage.csv`: row 25.turn_tokens | 3 | `generated/coverage.tex:30` |
| Cov26Prefixes | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | `outputs/consolidated_coverage.csv`: row 26.prefixes | 3 | `generated/coverage.tex:31` |
| Cov26Sessions | 2 | `outputs/consolidated_coverage.csv`: row 26.sessions | 3 | `generated/coverage.tex:31` |
| Cov26Turn | 256 | `outputs/consolidated_coverage.csv`: row 26.turn_tokens | 3 | `generated/coverage.tex:31` |
| Cov27Prefixes | 64, 256, 512, 1,024, 32,736 | `outputs/consolidated_coverage.csv`: row 27.prefixes | 3 | `generated/coverage.tex:32` |
| Cov27Sessions | 1 | `outputs/consolidated_coverage.csv`: row 27.sessions | 3 | `generated/coverage.tex:32` |
| Cov27Turn | 32 | `outputs/consolidated_coverage.csv`: row 27.turn_tokens | 3 | `generated/coverage.tex:32` |
| Cov28Prefixes | 64, 256, 512, 1,024, 2,016 | `outputs/consolidated_coverage.csv`: row 28.prefixes | 3 | `generated/coverage.tex:33` |
| Cov28Sessions | 1 | `outputs/consolidated_coverage.csv`: row 28.sessions | 3 | `generated/coverage.tex:33` |
| Cov28Turn | 32 | `outputs/consolidated_coverage.csv`: row 28.turn_tokens | 3 | `generated/coverage.tex:33` |
| Cov29Prefixes | 64, 256, 512, 1,024 | `outputs/consolidated_coverage.csv`: row 29.prefixes | 3 | `generated/coverage.tex:34` |
| Cov29Sessions | 1 | `outputs/consolidated_coverage.csv`: row 29.sessions | 3 | `generated/coverage.tex:34` |
| Cov29Turn | 32 | `outputs/consolidated_coverage.csv`: row 29.turn_tokens | 3 | `generated/coverage.tex:34` |
| Cov2Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192 | `outputs/consolidated_coverage.csv`: row 2.prefixes | 3 | `generated/coverage.tex:7` |
| Cov2Sessions | 1 | `outputs/consolidated_coverage.csv`: row 2.sessions | 3 | `generated/coverage.tex:7` |
| Cov2Turn | 32 | `outputs/consolidated_coverage.csv`: row 2.turn_tokens | 3 | `generated/coverage.tex:7` |
| Cov30Prefixes | 512, 2,048, 8,192 | `outputs/consolidated_coverage.csv`: row 30.prefixes | 3 | `generated/coverage.tex:35` |
| Cov30Sessions | 1 | `outputs/consolidated_coverage.csv`: row 30.sessions | 3 | `generated/coverage.tex:35` |
| Cov30Turn | 32 | `outputs/consolidated_coverage.csv`: row 30.turn_tokens | 3 | `generated/coverage.tex:35` |
| Cov31Prefixes | 512, 2,048, 8,192 | `outputs/consolidated_coverage.csv`: row 31.prefixes | 3 | `generated/coverage.tex:36` |
| Cov31Sessions | 1 | `outputs/consolidated_coverage.csv`: row 31.sessions | 3 | `generated/coverage.tex:36` |
| Cov31Turn | 256 | `outputs/consolidated_coverage.csv`: row 31.turn_tokens | 3 | `generated/coverage.tex:36` |
| Cov3Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192 | `outputs/consolidated_coverage.csv`: row 3.prefixes | 3 | `generated/coverage.tex:8` |
| Cov3Sessions | 1 | `outputs/consolidated_coverage.csv`: row 3.sessions | 3 | `generated/coverage.tex:8` |
| Cov3Turn | 256 | `outputs/consolidated_coverage.csv`: row 3.turn_tokens | 3 | `generated/coverage.tex:8` |
| Cov4Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 1,792, 2,048, 8,192 | `outputs/consolidated_coverage.csv`: row 4.prefixes | 3 | `generated/coverage.tex:9` |
| Cov4Sessions | 1 | `outputs/consolidated_coverage.csv`: row 4.sessions | 3 | `generated/coverage.tex:9` |
| Cov4Turn | 32 | `outputs/consolidated_coverage.csv`: row 4.turn_tokens | 3 | `generated/coverage.tex:9` |
| Cov5Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | `outputs/consolidated_coverage.csv`: row 5.prefixes | 3 | `generated/coverage.tex:10` |
| Cov5Sessions | 3 | `outputs/consolidated_coverage.csv`: row 5.sessions | 3 | `generated/coverage.tex:10` |
| Cov5Turn | 32 | `outputs/consolidated_coverage.csv`: row 5.turn_tokens | 3 | `generated/coverage.tex:10` |
| Cov6Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | `outputs/consolidated_coverage.csv`: row 6.prefixes | 3 | `generated/coverage.tex:11` |
| Cov6Sessions | 3 | `outputs/consolidated_coverage.csv`: row 6.sessions | 3 | `generated/coverage.tex:11` |
| Cov6Turn | 256 | `outputs/consolidated_coverage.csv`: row 6.turn_tokens | 3 | `generated/coverage.tex:11` |
| Cov7Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | `outputs/consolidated_coverage.csv`: row 7.prefixes | 3 | `generated/coverage.tex:12` |
| Cov7Sessions | 1 | `outputs/consolidated_coverage.csv`: row 7.sessions | 3 | `generated/coverage.tex:12` |
| Cov7Turn | 32 | `outputs/consolidated_coverage.csv`: row 7.turn_tokens | 3 | `generated/coverage.tex:12` |
| Cov8Prefixes | 16, 32, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | `outputs/consolidated_coverage.csv`: row 8.prefixes | 3 | `generated/coverage.tex:13` |
| Cov8Sessions | 1 | `outputs/consolidated_coverage.csv`: row 8.sessions | 3 | `generated/coverage.tex:13` |
| Cov8Turn | 256 | `outputs/consolidated_coverage.csv`: row 8.turn_tokens | 3 | `generated/coverage.tex:13` |
| Cov9Prefixes | 16, 32, 64, 128, 256, 512, 1,024 | `outputs/consolidated_coverage.csv`: row 9.prefixes | 3 | `generated/coverage.tex:14` |
| Cov9Sessions | 1 | `outputs/consolidated_coverage.csv`: row 9.sessions | 3 | `generated/coverage.tex:14` |
| Cov9Turn | 32 | `outputs/consolidated_coverage.csv`: row 9.turn_tokens | 3 | `generated/coverage.tex:14` |
| Example | 512 | `outputs/consolidated_coverage.csv`: prefix or new-turn length present in coverage | 3 | `main.tex:78`, `main.tex:137`, `main.tex:151` |
| ExtrapLength | 32,736 | `outputs/consolidated_coverage.csv`: prefix or new-turn length present in coverage | 3 | `main.tex:159` |
| FullRepeats | 10 | `docs/PHASE3_PROTOCOL.md`: released measurement protocol / referenced canonical analysis metadata | 3 | `main.tex:78`, `main.tex:102` |
| H100Cells | 26 | `outputs/consolidated_scorecard.csv`: gpu=H100!.complete_cells | 9 | `main.tex:198` |
| H100Correct | 20 | `outputs/consolidated_scorecard.csv`: gpu=H100!.correct_decisions | 9 | `main.tex:27`, `main.tex:117` |
| H100Missing | 52 | `docs/CLAIMS.md`: claim 20 unfinished cells | 20 | `main.tex:198` |
| H100RatioTotal | 1 | `outputs/claims_evidence.json`: hypothesis_scorecards.gpu=H100.RatioTotal | 11 | `main.tex:162` |
| H100RatioYes | 0 | `outputs/claims_evidence.json`: hypothesis_scorecards.gpu=H100.RatioYes | 11 | `main.tex:162` |
| H100Resolved | 21 | `outputs/consolidated_scorecard.csv`: gpu=H100!.resolved_decisions | 9 | `main.tex:27`, `main.tex:117` |
| H100Unresolved | 1 | `outputs/consolidated_scorecard.csv`: gpu=H100!.unresolved_decisions | 9 | `main.tex:117` |
| HalfAdjusted | 2,442.265 | `docs/CLAIMS.md`: claim 6 adjusted B* | 6 | `main.tex:137` |
| HalfPrefix | 226.626 | `docs/CLAIMS.md`: claim 6 prefix-only B* | 6 | `main.tex:137` |
| KV0 | 12,288 | `outputs/claims_evidence.json`: kv_bytes_per_token.Qwen/Qwen2.5-0.5B | 4 | `generated/models.tex:3` |
| KV1 | 28,672 | `outputs/claims_evidence.json`: kv_bytes_per_token.Qwen/Qwen2.5-1.5B | 4 | `generated/models.tex:4` |
| KV2 | 36,864 | `outputs/claims_evidence.json`: kv_bytes_per_token.Qwen/Qwen2.5-3B | 4 | `generated/models.tex:5` |
| KV3 | 196,608 | `outputs/claims_evidence.json`: kv_bytes_per_token.EleutherAI/pythia-1.4b | 4 | `generated/models.tex:6` |
| KV4 | 196,608 | `outputs/claims_evidence.json`: kv_bytes_per_token.facebook/opt-1.3b | 4 | `generated/models.tex:7` |
| KV5 | 327,680 | `outputs/claims_evidence.json`: kv_bytes_per_token.microsoft/phi-2 | 4 | `generated/models.tex:8` |
| KV6 | 114,688 | `outputs/claims_evidence.json`: kv_bytes_per_token.unsloth/Llama-3.2-3B-Instruct | 4 | `generated/models.tex:9` |
| KaggleFileSamples | 7,762 | `outputs/consolidated_file_observability.csv`: phase2.sum(samples) | 16 | `main.tex:111` |
| KaggleMaxBytes | 1,879,052,288 | `outputs/consolidated_file_observability.csv`: phase2.maximum_bytes | 16 | `main.tex:111` |
| KaggleMinBytes | 196,608 | `outputs/consolidated_file_observability.csv`: phase2.minimum_bytes | 16 | `main.tex:111` |
| KaggleReads | 7,762 | `outputs/consolidated_file_observability.csv`: phase2.sum(positive) | 16 | `main.tex:111` |
| L4Correct | 574 | `outputs/consolidated_scorecard.csv`: gpu=L4.correct_decisions | 9 | `main.tex:27`, `main.tex:117` |
| L4ExtrapError | 4,934.542 | `docs/CLAIMS.md`: claim 10 L4 recompute absolute error | 10 | `main.tex:159` |
| L4ExtrapObs | 18,022.902 | `docs/CLAIMS.md`: claim 10 L4 recompute observed | 10 | `main.tex:159` |
| L4ExtrapPred | 13,088.360 | `docs/CLAIMS.md`: claim 10 L4 recompute predicted | 10 | `main.tex:159` |
| L4MAE | 3.203 | `outputs/consolidated_scorecard.csv`: gpu=L4.median_absolute_ttft_error_ms | 9 | `main.tex:117` |
| L4RatioTotal | 27 | `outputs/claims_evidence.json`: hypothesis_scorecards.gpu=L4.RatioTotal | 11 | `main.tex:162` |
| L4RatioYes | 25 | `outputs/claims_evidence.json`: hypothesis_scorecards.gpu=L4.RatioYes | 11 | `main.tex:162` |
| L4Resolved | 636 | `outputs/consolidated_scorecard.csv`: gpu=L4.resolved_decisions | 9 | `main.tex:27`, `main.tex:117` |
| L4SpreadLong | 4.417 | `docs/CLAIMS.md`: claim 14 L4 N256 median spread | 14 | `main.tex:155` |
| L4SpreadShort | 4.956 | `docs/CLAIMS.md`: claim 14 L4 N32 median spread | 14 | `main.tex:155` |
| L4Unresolved | 13 | `outputs/consolidated_scorecard.csv`: gpu=L4.unresolved_decisions | 9 | `main.tex:117` |
| Long | 256 | `outputs/consolidated_coverage.csv`: prefix or new-turn length present in coverage | 3 | `main.tex:78`, `main.tex:94` |
| LongPrefix | 8,192 | `outputs/consolidated_coverage.csv`: prefix or new-turn length present in coverage | 3 | `main.tex:78` |
| MainGrid | 16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384 | `outputs/consolidated_coverage.csv`: phase3 main-model prefixes | 3 | `main.tex:94` |
| Matched | 1,024 | `outputs/consolidated_coverage.csv`: prefix or new-turn length present in coverage | 3 | `main.tex:126`, `main.tex:198` |
| MaxMain | 16,384 | `outputs/consolidated_coverage.csv`: prefix or new-turn length present in coverage | 3 | `main.tex:198` |
| MhaGrid | 64, 256, 512, 1,024 | `docs/CLAIMS.md`: claim 18 matched prefixes | 18 | `main.tex:169` |
| MicroRepeats | 5 | `docs/PHASE3_PROTOCOL.md`: released measurement protocol / referenced canonical analysis metadata | 3 | `main.tex:106` |
| ModalFileSamples | 4,575 | `outputs/consolidated_file_observability.csv`: phase3.sum(samples) | 17 | `main.tex:113` |
| ModalReads | 0 | `outputs/consolidated_file_observability.csv`: phase3.sum(positive) | 17 | `main.tex:113` |
| ModelCount | 7 | `outputs/claims_evidence.json`: phase2_report_totals.model configurations | 3 | `main.tex:27`, `main.tex:78` |
| PhiHigh | 1598.4 | `docs/CLAIMS.md`: claim 7 Phi achieved high | 7 | `main.tex:151` |
| PhiLow | 799.2 | `docs/CLAIMS.md`: claim 7 Phi achieved low | 7 | `main.tex:151` |
| PilotMid | 2,048 | `outputs/consolidated_coverage.csv`: pilot prefixes | 1 | `main.tex:78` |
| PilotRepeats | 12 | `docs/CLAIMS.md`: claim 1 measured repeats | 1 | `main.tex:78` |
| PrefixCorrect | 1,017 | `outputs/claims_evidence.json`: phase2_report_totals.rule_counts.prefix_rule_agreements | 5 | `main.tex:135` |
| PythiaHigh | 1597.2 | `docs/CLAIMS.md`: claim 7 Pythia achieved high | 7 | `main.tex:151` |
| PythiaLow | 798.9 | `docs/CLAIMS.md`: claim 7 Pythia achieved low | 7 | `main.tex:151` |
| QwenMainHigh | 398.4 | `docs/CLAIMS.md`: claim 7 Qwen1.5 achieved high | 7 | `main.tex:151` |
| QwenMainLow | 199.5 | `docs/CLAIMS.md`: claim 7 Qwen1.5 achieved low | 7 | `main.tex:151` |
| QwenThreeHigh | 199.7 | `docs/CLAIMS.md`: claim 7 Qwen3 achieved high | 7 | `main.tex:151` |
| QwenThreeLow | 99.9 | `docs/CLAIMS.md`: claim 7 Qwen3 achieved low | 7 | `main.tex:151` |
| Rate100 | 100 | `docs/PHASE2_PROTOCOL.md`: simulated-bandwidth target grid | 12 | `main.tex:126` |
| Rate1600 | 1,600 | `docs/PHASE2_PROTOCOL.md`: simulated-bandwidth target grid | 12 | `main.tex:126`, `main.tex:126` |
| Rate200 | 200 | `docs/PHASE2_PROTOCOL.md`: simulated-bandwidth target grid | 12 | `main.tex:126`, `main.tex:126` |
| Rate400 | 400 | `docs/PHASE2_PROTOCOL.md`: simulated-bandwidth target grid | 12 | `main.tex:126`, `main.tex:126` |
| Rate800 | 800 | `docs/PHASE2_PROTOCOL.md`: simulated-bandwidth target grid | 12 | `main.tex:126`, `main.tex:126`, `main.tex:126` |
| Rates | 50, 100, 200, 400, 800, 1,600 | `docs/PHASE2_PROTOCOL.md`: Rate-limited copies are simulated bandwidth | 3 | `main.tex:99` |
| RawNewError | 3.086 | `docs/CLAIMS.md`: claim 19 raw corrected APE | 19 | `main.tex:153` |
| RawOldError | 3.107 | `docs/CLAIMS.md`: claim 19 raw old APE | 19 | `main.tex:153` |
| Score12Col2 | 574 / 636 | `docs/PHASE3_REPORT.md`: scorecard table line 13, column 3 | 9 | `generated/scorecards.tex:5` |
| Score12Col3 | 13 | `docs/PHASE3_REPORT.md`: scorecard table line 13, column 4 | 9 | `generated/scorecards.tex:5` |
| Score12Col4 | 767 | `docs/PHASE3_REPORT.md`: scorecard table line 13, column 5 | 9 | `generated/scorecards.tex:5` |
| Score12Col5 | 3.203 | `docs/PHASE3_REPORT.md`: scorecard table line 13, column 6 | 9 | `generated/scorecards.tex:5` |
| Score13Col2 | 246 / 248 | `docs/PHASE3_REPORT.md`: scorecard table line 14, column 3 | 9 | `generated/scorecards.tex:6` |
| Score13Col3 | 5 | `docs/PHASE3_REPORT.md`: scorecard table line 14, column 4 | 9 | `generated/scorecards.tex:6` |
| Score13Col4 | 299 | `docs/PHASE3_REPORT.md`: scorecard table line 14, column 5 | 9 | `generated/scorecards.tex:6` |
| Score13Col5 | 2.822 | `docs/PHASE3_REPORT.md`: scorecard table line 14, column 6 | 9 | `generated/scorecards.tex:6` |
| Score14Col2 | 231 / 289 | `docs/PHASE3_REPORT.md`: scorecard table line 15, column 3 | 9 | `generated/scorecards.tex:7` |
| Score14Col3 | 8 | `docs/PHASE3_REPORT.md`: scorecard table line 15, column 4 | 9 | `generated/scorecards.tex:7` |
| Score14Col4 | 351 | `docs/PHASE3_REPORT.md`: scorecard table line 15, column 5 | 9 | `generated/scorecards.tex:7` |
| Score14Col5 | 2.981 | `docs/PHASE3_REPORT.md`: scorecard table line 15, column 6 | 9 | `generated/scorecards.tex:7` |
| Score15Col2 | 97 / 99 | `docs/PHASE3_REPORT.md`: scorecard table line 16, column 3 | 9 | `generated/scorecards.tex:8` |
| Score15Col3 | 0 | `docs/PHASE3_REPORT.md`: scorecard table line 16, column 4 | 9 | `generated/scorecards.tex:8` |
| Score15Col4 | 117 | `docs/PHASE3_REPORT.md`: scorecard table line 16, column 5 | 9 | `generated/scorecards.tex:8` |
| Score15Col5 | 4.007 | `docs/PHASE3_REPORT.md`: scorecard table line 16, column 6 | 9 | `generated/scorecards.tex:8` |
| Score16Col2 | 193 / 201 | `docs/PHASE3_REPORT.md`: scorecard table line 17, column 3 | 9 | `generated/scorecards.tex:9` |
| Score16Col3 | 8 | `docs/PHASE3_REPORT.md`: scorecard table line 17, column 4 | 9 | `generated/scorecards.tex:9` |
| Score16Col4 | 247 | `docs/PHASE3_REPORT.md`: scorecard table line 17, column 5 | 9 | `generated/scorecards.tex:9` |
| Score16Col5 | 1.506 | `docs/PHASE3_REPORT.md`: scorecard table line 17, column 6 | 9 | `generated/scorecards.tex:9` |
| Score17Col2 | 188 / 216 | `docs/PHASE3_REPORT.md`: scorecard table line 18, column 3 | 9 | `generated/scorecards.tex:10` |
| Score17Col3 | 4 | `docs/PHASE3_REPORT.md`: scorecard table line 18, column 4 | 9 | `generated/scorecards.tex:10` |
| Score17Col4 | 260 | `docs/PHASE3_REPORT.md`: scorecard table line 18, column 5 | 9 | `generated/scorecards.tex:10` |
| Score17Col5 | 3.681 | `docs/PHASE3_REPORT.md`: scorecard table line 18, column 6 | 9 | `generated/scorecards.tex:10` |
| Score18Col2 | 193 / 219 | `docs/PHASE3_REPORT.md`: scorecard table line 19, column 3 | 9 | `generated/scorecards.tex:11` |
| Score18Col3 | 1 | `docs/PHASE3_REPORT.md`: scorecard table line 19, column 4 | 9 | `generated/scorecards.tex:11` |
| Score18Col4 | 260 | `docs/PHASE3_REPORT.md`: scorecard table line 19, column 5 | 9 | `generated/scorecards.tex:11` |
| Score18Col5 | 3.654 | `docs/PHASE3_REPORT.md`: scorecard table line 19, column 6 | 9 | `generated/scorecards.tex:11` |
| Score19Col2 | 192 / 206 | `docs/PHASE3_REPORT.md`: scorecard table line 20, column 3 | 9 | `generated/scorecards.tex:12` |
| Score19Col3 | 14 | `docs/PHASE3_REPORT.md`: scorecard table line 20, column 4 | 9 | `generated/scorecards.tex:12` |
| Score19Col4 | 260 | `docs/PHASE3_REPORT.md`: scorecard table line 20, column 5 | 9 | `generated/scorecards.tex:12` |
| Score19Col5 | 2.040 | `docs/PHASE3_REPORT.md`: scorecard table line 20, column 6 | 9 | `generated/scorecards.tex:12` |
| Score20Col2 | 59 / 63 | `docs/PHASE3_REPORT.md`: scorecard table line 21, column 3 | 9 | `generated/scorecards.tex:13` |
| Score20Col3 | 3 | `docs/PHASE3_REPORT.md`: scorecard table line 21, column 4 | 9 | `generated/scorecards.tex:13` |
| Score20Col4 | 78 | `docs/PHASE3_REPORT.md`: scorecard table line 21, column 5 | 9 | `generated/scorecards.tex:13` |
| Score20Col5 | 2.275 | `docs/PHASE3_REPORT.md`: scorecard table line 21, column 6 | 9 | `generated/scorecards.tex:13` |
| Score21Col2 | 96 / 105 | `docs/PHASE3_REPORT.md`: scorecard table line 22, column 3 | 9 | `generated/scorecards.tex:14` |
| Score21Col3 | 5 | `docs/PHASE3_REPORT.md`: scorecard table line 22, column 4 | 9 | `generated/scorecards.tex:14` |
| Score21Col4 | 130 | `docs/PHASE3_REPORT.md`: scorecard table line 22, column 5 | 9 | `generated/scorecards.tex:14` |
| Score21Col5 | 2.308 | `docs/PHASE3_REPORT.md`: scorecard table line 22, column 6 | 9 | `generated/scorecards.tex:14` |
| Score22Col2 | 37 / 38 | `docs/PHASE3_REPORT.md`: scorecard table line 23, column 3 | 9 | `generated/scorecards.tex:15` |
| Score22Col3 | 6 | `docs/PHASE3_REPORT.md`: scorecard table line 23, column 4 | 9 | `generated/scorecards.tex:15` |
| Score22Col4 | 52 | `docs/PHASE3_REPORT.md`: scorecard table line 23, column 5 | 9 | `generated/scorecards.tex:15` |
| Score22Col5 | 1.341 | `docs/PHASE3_REPORT.md`: scorecard table line 23, column 6 | 9 | `generated/scorecards.tex:15` |
| Score23Col2 | 192 / 206 | `docs/PHASE3_REPORT.md`: scorecard table line 24, column 3 | 9 | `generated/scorecards.tex:16` |
| Score23Col3 | 14 | `docs/PHASE3_REPORT.md`: scorecard table line 24, column 4 | 9 | `generated/scorecards.tex:16` |
| Score23Col4 | 260 | `docs/PHASE3_REPORT.md`: scorecard table line 24, column 5 | 9 | `generated/scorecards.tex:16` |
| Score23Col5 | 2.040 | `docs/PHASE3_REPORT.md`: scorecard table line 24, column 6 | 9 | `generated/scorecards.tex:16` |
| Score24Col2 | 398 / 426 | `docs/PHASE3_REPORT.md`: scorecard table line 25, column 3 | 9 | `generated/scorecards.tex:17` |
| Score24Col3 | 3 | `docs/PHASE3_REPORT.md`: scorecard table line 25, column 4 | 9 | `generated/scorecards.tex:17` |
| Score24Col4 | 507 | `docs/PHASE3_REPORT.md`: scorecard table line 25, column 5 | 9 | `generated/scorecards.tex:17` |
| Score24Col5 | 5.758 | `docs/PHASE3_REPORT.md`: scorecard table line 25, column 6 | 9 | `generated/scorecards.tex:17` |
| Score25Col2 | 178 / 187 | `docs/PHASE3_REPORT.md`: scorecard table line 26, column 3 | 9 | `generated/scorecards.tex:18` |
| Score25Col3 | 0 | `docs/PHASE3_REPORT.md`: scorecard table line 26, column 4 | 9 | `generated/scorecards.tex:18` |
| Score25Col4 | 221 | `docs/PHASE3_REPORT.md`: scorecard table line 26, column 5 | 9 | `generated/scorecards.tex:18` |
| Score25Col5 | 5.094 | `docs/PHASE3_REPORT.md`: scorecard table line 26, column 6 | 9 | `generated/scorecards.tex:18` |
| Score26Col2 | 170 / 185 | `docs/PHASE3_REPORT.md`: scorecard table line 27, column 3 | 9 | `generated/scorecards.tex:19` |
| Score26Col3 | 2 | `docs/PHASE3_REPORT.md`: scorecard table line 27, column 4 | 9 | `generated/scorecards.tex:19` |
| Score26Col4 | 221 | `docs/PHASE3_REPORT.md`: scorecard table line 27, column 5 | 9 | `generated/scorecards.tex:19` |
| Score26Col5 | 5.511 | `docs/PHASE3_REPORT.md`: scorecard table line 27, column 6 | 9 | `generated/scorecards.tex:19` |
| Score27Col2 | 50 / 54 | `docs/PHASE3_REPORT.md`: scorecard table line 28, column 3 | 9 | `generated/scorecards.tex:20` |
| Score27Col3 | 1 | `docs/PHASE3_REPORT.md`: scorecard table line 28, column 4 | 9 | `generated/scorecards.tex:20` |
| Score27Col4 | 65 | `docs/PHASE3_REPORT.md`: scorecard table line 28, column 5 | 9 | `generated/scorecards.tex:20` |
| Score27Col5 | 8.371 | `docs/PHASE3_REPORT.md`: scorecard table line 28, column 6 | 9 | `generated/scorecards.tex:20` |
| Score28Col2 | 193 / 209 | `docs/PHASE3_REPORT.md`: scorecard table line 29, column 3 | 9 | `generated/scorecards.tex:21` |
| Score28Col3 | 0 | `docs/PHASE3_REPORT.md`: scorecard table line 29, column 4 | 9 | `generated/scorecards.tex:21` |
| Score28Col4 | 247 | `docs/PHASE3_REPORT.md`: scorecard table line 29, column 5 | 9 | `generated/scorecards.tex:21` |
| Score28Col5 | 5.031 | `docs/PHASE3_REPORT.md`: scorecard table line 29, column 6 | 9 | `generated/scorecards.tex:21` |
| Score29Col2 | 205 / 217 | `docs/PHASE3_REPORT.md`: scorecard table line 30, column 3 | 9 | `generated/scorecards.tex:22` |
| Score29Col3 | 3 | `docs/PHASE3_REPORT.md`: scorecard table line 30, column 4 | 9 | `generated/scorecards.tex:22` |
| Score29Col4 | 260 | `docs/PHASE3_REPORT.md`: scorecard table line 30, column 5 | 9 | `generated/scorecards.tex:22` |
| Score29Col5 | 6.433 | `docs/PHASE3_REPORT.md`: scorecard table line 30, column 6 | 9 | `generated/scorecards.tex:22` |
| Score30Col2 | 20 / 21 | `docs/PHASE3_REPORT.md`: scorecard table line 31, column 3 | 9 | `generated/scorecards.tex:23` |
| Score30Col3 | 1 | `docs/PHASE3_REPORT.md`: scorecard table line 31, column 4 | 9 | `generated/scorecards.tex:23` |
| Score30Col4 | 26 | `docs/PHASE3_REPORT.md`: scorecard table line 31, column 5 | 9 | `generated/scorecards.tex:23` |
| Score30Col5 | 6.579 | `docs/PHASE3_REPORT.md`: scorecard table line 31, column 6 | 9 | `generated/scorecards.tex:23` |
| Score31Col2 | 11 / 11 | `docs/PHASE3_REPORT.md`: scorecard table line 32, column 3 | 9 | `generated/scorecards.tex:24` |
| Score31Col3 | 0 | `docs/PHASE3_REPORT.md`: scorecard table line 32, column 4 | 9 | `generated/scorecards.tex:24` |
| Score31Col4 | 13 | `docs/PHASE3_REPORT.md`: scorecard table line 32, column 5 | 9 | `generated/scorecards.tex:24` |
| Score31Col5 | 0.332 | `docs/PHASE3_REPORT.md`: scorecard table line 32, column 6 | 9 | `generated/scorecards.tex:24` |
| Score32Col2 | 9 / 10 | `docs/PHASE3_REPORT.md`: scorecard table line 33, column 3 | 9 | `generated/scorecards.tex:25` |
| Score32Col3 | 1 | `docs/PHASE3_REPORT.md`: scorecard table line 33, column 4 | 9 | `generated/scorecards.tex:25` |
| Score32Col4 | 13 | `docs/PHASE3_REPORT.md`: scorecard table line 33, column 5 | 9 | `generated/scorecards.tex:25` |
| Score32Col5 | 9.999 | `docs/PHASE3_REPORT.md`: scorecard table line 33, column 6 | 9 | `generated/scorecards.tex:25` |
| Score33Col2 | 20 / 21 | `docs/PHASE3_REPORT.md`: scorecard table line 34, column 3 | 9 | `generated/scorecards.tex:26` |
| Score33Col3 | 1 | `docs/PHASE3_REPORT.md`: scorecard table line 34, column 4 | 9 | `generated/scorecards.tex:26` |
| Score33Col4 | 26 | `docs/PHASE3_REPORT.md`: scorecard table line 34, column 5 | 9 | `generated/scorecards.tex:26` |
| Score33Col5 | 6.579 | `docs/PHASE3_REPORT.md`: scorecard table line 34, column 6 | 9 | `generated/scorecards.tex:26` |
| SessionsL4 | 2 | `docs/PHASE3_PROTOCOL.md`: released measurement protocol / referenced canonical analysis metadata | 3 | `main.tex:80` |
| SessionsT4 | 3 | `docs/PHASE3_REPORT.md`: released measurement protocol / referenced canonical analysis metadata | 3 | `main.tex:80` |
| Short | 32 | `outputs/consolidated_coverage.csv`: prefix or new-turn length present in coverage | 3 | `main.tex:78`, `main.tex:94`, `main.tex:94`, `main.tex:126`, `main.tex:129`, `main.tex:137`, `main.tex:142`, `main.tex:151`, `main.tex:159`, `main.tex:165`, `main.tex:169` |
| ShortGrid | 16, 64, 128, 256 | `docs/CLAIMS.md`: claim 13 common short prefixes | 13 | `main.tex:142` |
| T4Held2Correct | 148 | `outputs/claims_evidence.json`: phase2-main-session-2.agreements | 8 | `main.tex:139` |
| T4Held2Resolved | 149 | `outputs/claims_evidence.json`: phase2-main-session-2.resolved_cells | 8 | `main.tex:139` |
| T4Held3Correct | 146 | `outputs/claims_evidence.json`: phase2-main-session-3.agreements | 8 | `main.tex:139` |
| T4Held3Resolved | 150 | `outputs/claims_evidence.json`: phase2-main-session-3.resolved_cells | 8 | `main.tex:139` |
| T4Invalid | 0 | `outputs/claims_evidence.json`: phase2_report_totals.invalid_measurements | 3 | `main.tex:78` |
| T4Resolved | 1,258 | `outputs/claims_evidence.json`: phase2_report_totals.rule_counts.resolved_comparisons | 5 | `main.tex:135`, `main.tex:135` |
| T4Sessions | 10 | `outputs/claims_evidence.json`: phase2_report_totals.full_sessions | 3 | `main.tex:78` |
| T4SpreadLong | 14.847 | `docs/CLAIMS.md`: claim 14 T4 N256 median spread | 14 | `main.tex:155` |
| T4SpreadShort | 12.341 | `docs/CLAIMS.md`: claim 14 T4 N32 median spread | 14 | `main.tex:155` |
| T4Timings | 26,040 | `outputs/claims_evidence.json`: phase2_report_totals.accepted_measurements | 3 | `main.tex:27`, `main.tex:78` |
| TorchNewError | 3.097 | `docs/CLAIMS.md`: claim 19 torch corrected APE | 19 | `main.tex:153` |
| TorchOldError | 11.78 | `docs/CLAIMS.md`: claim 19 torch old APE | 19 | `main.tex:153` |

## Figures

| Figure | Numeric source | Preservation |
| --- | --- | --- |
| bstar-vs-gpu | `outputs/consolidated_crossovers.csv` in the release; exact released PDF and draft SHA-256 in `generated/number_audit.json` | Exact PDF |
| frozen-scorecard | `outputs/consolidated_scorecard.csv` in the release; exact released PDF and draft SHA-256 in `generated/number_audit.json` | Exact PDF |
| short-context-regime | `outputs/consolidated_results.jsonl` in the release; exact released PDF and draft SHA-256 in `generated/number_audit.json` | Exact PDF |
| bstar-vs-prefill | `outputs/consolidated_crossovers.csv` in the release; exact released PDF and draft SHA-256 in `generated/number_audit.json` | Layout-only reflow; `generated/figure_reformat.json` |

Axes ticks, figure labels, table/section/equation counters, bibliography labels and page numbers are display/document counters, not additional measurements. The figure data mappings cover plotted values and censoring; axis tick spacing does not constitute another observed bandwidth.

## Identifiers and non-empirical numbers

| Kind | Tokens | Source and interpretation |
| --- | --- | --- |
| Model names | Qwen2.5-0.5B, Qwen2.5-1.5B, Qwen2.5-3B, Llama-3.2-3B-Instruct, Llama 3.2-3B, Pythia-1.4B, pythia-1.4b, opt-1.3b, Phi-2, phi-2, Qwen 0.5B, Qwen 1.5B, Qwen 3B | Released model and coverage tables; numeric substrings are checkpoint identifiers, not extra results. |
| Hardware and dtype labels | T4, L4, A10, A10G, H100, P100; x16, x8; fp16, bf16; H2D | Released PHASE3_REPORT.md, model table and claim 22. PCIe widths remain separate. H2D names host-to-device movement, not a measurement. |
| Runtime versions | 2.11.0+cu130; 4.51.3 | Released PHASE3_REPORT.md; exact software identifiers. |
| Artifact version | v0.1.0-data | Frozen release/tag, not a measurement. |
| Author identity | achumohith14@gmail.com; 0009-0003-2978-3045 | Explicit author-provided email and ORCID. |
| Run and command identifiers | l4-main-1, l4-main-2, l4-controls, a10-main-1, a10-main-2, a10-controls, h100-main; python3 and phase2/phase3 script names | Released PHASE3_REPORT.md and README.md; label digits are identifiers, not additional observations. |
| Formula constants | Positive denominator, zero boundary | Mathematical definition in claim 6 and the user-requested rule; zero is not a measured latency. |
| Proposed recipe | One-minute checklist | User-requested operating suggestion, explicitly not a timing guarantee. Actual calibration function times are separately mapped as CalA10Seconds and CalL4Seconds. |
| Bibliographic numbers | Citation years, arXiv IDs, versions and access date | Primary-source metadata verified in CITATIONS.md and sources/verified_citations.json; no external performance numbers are adopted. |
| Typesetting parameters | Article font size, page margins, figure widths, table widths and spacing | Standard document layout adapted from grammar-vs-bits, not experimental quantities. Individual occurrences are in generated/number_audit.json. |

The registry preserves direct sources for descriptive same-session statistics separately from frozen predictions. A10/A10G aggregates are never pooled. The source strengths and limitations remain those of CLAIMS.md.
