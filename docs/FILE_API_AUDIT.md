# Local file API observability

Physical reads were not observed on Modal. Its tier is the **local file API path (physical reads not observed)**. Page-cache residency is one interpretation of the zero process counters; the cache layer is unverified. Kaggle uses the **local file API path (positive process physical-read counters; underlying storage and host cache unidentified)**. Applying the Modal parenthetical to Kaggle would contradict the recorded counters. Neither platform identifies a physical device or establishes a storage-device benchmark.

Counts below include every recorded file observation, including calibration and the recovered partial H100 run. They describe I/O accounting and do not turn incomplete timings into scored cells.

| Phase | Record kind | Path | Positive / observations | Counter range, bytes | Median physical-read / file-byte ratio |
| --- | --- | --- | --- | --- | --- |
| pilot | bandwidth | file_read | 36 / 36 | 14696448 to 234897408 | 1.000006 |
| pilot | ttft | file | 72 / 72 | 14696448 to 234897408 | Not recorded |
| phase2 | microbenchmark | file_legs_torch | 1028 / 1028 | 200704 to 1879052288 | 1.000138 |
| phase2 | microbenchmark | file_legs_raw | 1028 / 1028 | 196608 to 1879048192 | 1.000000 |
| phase2 | measurement | file_raw_staged | 1902 / 1902 | 196608 to 1879048192 | 1.000000 |
| phase2 | measurement | file_torch_direct | 1902 / 1902 | 200704 to 1879052288 | 1.000124 |
| phase2 | measurement | file_torch_staged | 1902 / 1902 | 200704 to 1879052288 | 1.000124 |
| phase3 | microbenchmark | file_legs_torch | 0 / 990 | 0 to 0 | 0.000000 |
| phase3 | microbenchmark | file_legs_raw | 0 / 990 | 0 to 0 | 0.000000 |
| phase3 | microbenchmark | file_legs_direct | 0 / 180 | 0 to 0 | 0.000000 |
| phase3 | measurement | file_raw_staged | 0 / 1208 | 0 to 0 | 0.000000 |
| phase3 | measurement | file_torch_direct | 0 / 1207 | 0 to 0 | 0.000000 |

Global cache dropping was denied on Kaggle. Per-file eviction advice is advisory on both platforms. Positive Kaggle process counters support reads beyond the kernel page cache; they do not identify device media or rule out host/storage caches. The zero Modal counters and virtualized filesystem prevent the same conclusion there. No cached-versus-uncached ablation was performed.

| GPU / PCIe width | Model | Path | Comparison scope | Reload wins / resolved | Unresolved | Prefixes | New turns |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T4 | pythia-1.4b | file_raw_staged | all observed | 2 / 14 | 2 | [16, 32, 64, 128, 256, 512, 1024, 1792] | [32, 256] |
| T4 | pythia-1.4b | file_raw_staged | matched prefix and turn | 0 / 4 | 0 | [64, 256, 512, 1024] | [32] |
| T4 | pythia-1.4b | file_torch_direct | all observed | 2 / 13 | 3 | [16, 32, 64, 128, 256, 512, 1024, 1792] | [32, 256] |
| T4 | pythia-1.4b | file_torch_direct | matched prefix and turn | 0 / 4 | 0 | [64, 256, 512, 1024] | [32] |
| T4 | phi-2 | file_raw_staged | all observed | 6 / 11 | 5 | [16, 32, 64, 128, 256, 512, 1024, 1792] | [32, 256] |
| T4 | phi-2 | file_raw_staged | matched prefix and turn | 0 / 1 | 3 | [64, 256, 512, 1024] | [32] |
| T4 | phi-2 | file_torch_direct | all observed | 12 / 15 | 1 | [16, 32, 64, 128, 256, 512, 1024, 1792] | [32, 256] |
| T4 | phi-2 | file_torch_direct | matched prefix and turn | 2 / 3 | 1 | [64, 256, 512, 1024] | [32] |
| L4 (PCIe 3 x16) | pythia-1.4b | file_raw_staged | all observed | 0 / 5 | 0 | [64, 256, 512, 1024, 2016] | [32] |
| L4 (PCIe 3 x16) | pythia-1.4b | file_raw_staged | matched prefix and turn | 0 / 4 | 0 | [64, 256, 512, 1024] | [32] |
| L4 (PCIe 3 x16) | pythia-1.4b | file_torch_direct | all observed | 0 / 5 | 0 | [64, 256, 512, 1024, 2016] | [32] |
| L4 (PCIe 3 x16) | pythia-1.4b | file_torch_direct | matched prefix and turn | 0 / 4 | 0 | [64, 256, 512, 1024] | [32] |
| L4 (PCIe 3 x16) | phi-2 | file_raw_staged | all observed | 0 / 5 | 0 | [64, 256, 512, 1024, 2016] | [32] |
| L4 (PCIe 3 x16) | phi-2 | file_raw_staged | matched prefix and turn | 0 / 4 | 0 | [64, 256, 512, 1024] | [32] |
| L4 (PCIe 3 x16) | phi-2 | file_torch_direct | all observed | 0 / 5 | 0 | [64, 256, 512, 1024, 2016] | [32] |
| L4 (PCIe 3 x16) | phi-2 | file_torch_direct | matched prefix and turn | 0 / 4 | 0 | [64, 256, 512, 1024] | [32] |
| A10G (PCIe 4 x8) | pythia-1.4b | file_raw_staged | all observed | 0 / 5 | 0 | [64, 256, 512, 1024, 2016] | [32] |
| A10G (PCIe 4 x8) | pythia-1.4b | file_raw_staged | matched prefix and turn | 0 / 4 | 0 | [64, 256, 512, 1024] | [32] |
| A10G (PCIe 4 x8) | pythia-1.4b | file_torch_direct | all observed | 2 / 5 | 0 | [64, 256, 512, 1024, 2016] | [32] |
| A10G (PCIe 4 x8) | pythia-1.4b | file_torch_direct | matched prefix and turn | 1 / 4 | 0 | [64, 256, 512, 1024] | [32] |
| A10G (PCIe 4 x8) | phi-2 | file_raw_staged | all observed | 4 / 5 | 0 | [64, 256, 512, 1024, 2016] | [32] |
| A10G (PCIe 4 x8) | phi-2 | file_raw_staged | matched prefix and turn | 3 / 4 | 0 | [64, 256, 512, 1024] | [32] |
| A10G (PCIe 4 x8) | phi-2 | file_torch_direct | all observed | 4 / 5 | 0 | [64, 256, 512, 1024, 2016] | [32] |
| A10G (PCIe 4 x8) | phi-2 | file_torch_direct | matched prefix and turn | 3 / 4 | 0 | [64, 256, 512, 1024] | [32] |

A10 at PCIe x16 has no MHA sweep. The MHA Modal controls ran on A10G at PCIe x8. The comparison has different short-length grids and new-turn coverage across phases; it is not a matched factorial storage experiment. Sources: `consolidated_file_observability.csv`, `consolidated_file_wins.csv` and their underlying canonical records.
