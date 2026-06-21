# R006 raw-data completion

Archive v1.0-RC2 closes the R006 repaired-path raw-row gap.

The canonical deposit now contains:

- 3,440 per-rollout rows;
- 80 answer-blind path-selection rows;
- 3,360 measured rows across 5 traces, 2 continuation conditions, 7 cuts, and 48 rollouts per cell;
- sealed predeclaration, seed, model, environment, and source-reuse receipts;
- a frozen scan-ready runner;
- a standard-library constructor that reconstructs all 70 profile cells and all five trace summaries exactly.

The public conclusions are unchanged: fresh continuation holds through `k=32` in 4/5 traces, original-tail replay re-closes 5/5, and the endpoint Wilson intervals separate in 4/5.
