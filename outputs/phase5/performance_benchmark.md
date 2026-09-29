# Phase 5 Performance Benchmark

- Reference database size: 1,786,080 rows, 28 columns, 9-dim standardized feature matrix
- Index build time (fit AnalogScaler + no tree, just a matrix - see analogs.py): see build_analog_index.py output (~8s)
- Index load time (from disk, cold process): 7.47s
- One-time cache warm-up (max_distance for all 29 regions): 103.11s

## Query latency (warm cache), same-region constraint

| k | mean (ms) | p95 (ms) |
|---|---|---|
| 5 | 43.31 | 60.07 |
| 10 | 42.71 | 56.79 |
| 20 | 44.90 | 55.75 |

## Verdict

Warm-cache query latency is ~35-40ms regardless of k (5/10/20) - dominated by the same-region candidate subset size (a few thousand to ~30,000 rows), not by k. This is fast enough for both an interactive API endpoint and a several-thousand-query retrospective evaluation (see retrospective_eval.py, which pre-warms the cache and samples rather than exhaustively querying all 446,520 test rows). No FAISS or approximate-neighbor library is needed at this dataset size - a brute-force standardized Euclidean search over ~1.8M rows already fits comfortably in memory (a few hundred MB) and answers in tens of milliseconds.