# Report performance baselines

Recorded 2026-11-14 for smart-report 2.13.14 on macOS arm64, Python 3.14.6,
8 reported logical CPUs. Exact OS/dependency versions, workload fingerprint and all
three raw samples per workload are in the adjacent JSON files.

## Workloads

- `table`: 600 body rows per scale unit, four fixed-width columns, repeated header.
- `chinese`: 80 paragraphs per unit, bundled Source Han Sans, first-line indentation.
- `shadows`: 80 native-text titles per unit with Gaussian shadows, sigma 2 pt, 300 dpi,
  ten titles per manually sized A4 page.

| Case | Scale | Median seconds | Range seconds | Maximum peak RSS MiB | Pages | First-run PDF bytes |
|---|---:|---:|---:|---:|---:|---:|
| table | 1 | 0.311 | 0.310–0.313 | 50.5 | 20 | 57,453 |
| chinese | 1 | 0.479 | 0.467–0.479 | 136.5 | 11 | 26,353 |
| shadows | 1 | 1.114 | 1.100–1.132 | 68.6 | 8 | 1,937,800 |
| table | 2 | 0.605 | 0.591–0.614 | 51.5 | 39 | 113,322 |
| chinese | 2 | 0.784 | 0.783–0.796 | 136.5 | 21 | 36,103 |
| shadows | 2 | 2.479 | 2.200–2.885 | 78.8 | 16 | 3,893,338 |

## Reproduce

```bash
uv sync --locked --extra gaussian
uv run --no-sync python scripts/benchmark_reports.py /tmp/report-bench-scale1 1 3
uv run --no-sync python scripts/benchmark_reports.py /tmp/report-bench-scale2 2 3
```

Each invocation writes `results.json` and one PDF per sample. Use the project Python
environment so the local library and bundled workload fonts are available. The
benchmark supports macOS/Linux; `ru_maxrss` is normalized from bytes on macOS and
KiB on Linux. Missing Gaussian dependencies fail explicitly.

The wall timer includes document construction, font registration when used, layout,
pagination, rendering and in-memory PDF serialization. It excludes process startup,
module imports, disk writes and PDF page-count inspection. Peak RSS is sampled just
after rendering and includes the interpreter, imports and native allocations up to
that point; it is a process high-water mark, not Python-only heap usage or incremental
allocation. Every sample is a fresh process, but filesystem/OS caches are not flushed.
Workloads run sequentially, with a 180-second timeout per sample.

Compare the same workload hash, sizes, dependencies and hardware under similar load.
Three runs establish an initial reference, not a statistically controlled performance
claim. These values are deliberately not CI thresholds; functional tests remain the
gate. Generated PDFs and timing outputs are not committed, only the reviewed raw
JSON baselines.

## Operating implications

At scale 1, shadows take the most time and produce the largest file; Chinese text
has the highest peak RSS. Doubling item counts here produces approximately 1.94x,
1.64x and 2.23x median time for table, Chinese and shadow cases respectively. These
observations select shadow rendering/file size and Chinese font memory as the next
profiling targets. They do not establish a specific hotspot or justify a cache yet.

Pagination-boundary samples are separate from these throughput workloads. They keep
oversized atomic content intact and use debug warnings to expose overflow rather
than benchmarking silently resized or truncated output.
