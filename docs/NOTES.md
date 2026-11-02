# Study notes and deviations

## Before implementation

- Related work is reviewed in RELATED_WORK.md. py-kvcache substantially overlaps the central question. Proceed only as replication and older-hardware extension; no novelty claim for the underlying choice or slower-GPU hypothesis.
- The workspace initially contained no project or Git repository.
- The Kaggle CLI needed to refresh its existing credentials outside the filesystem sandbox. No credential file was read, copied, or added to this project.
- Pilot design: measure both requested new-turn lengths. Use one GPU for computation, but charge the budget for every allocated GPU if Kaggle allocates multiple devices.
- All timing estimates in planning are limits or projections, not measured results. Published source identifiers and configuration values are not project measurements.
