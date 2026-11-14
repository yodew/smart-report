"""Record render time, native peak RSS, page count and PDF size in fresh processes."""

# /// script
# requires-python = ">=3.10"
# dependencies = ["smart-report[gaussian]", "pypdf", "typing-extensions"]
# ///
# Run: uv run --no-sync python scripts/benchmark_reports.py OUTPUT_DIR [SCALE] [REPEATS]

from __future__ import annotations

import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
from dataclasses import asdict, dataclass
from importlib.metadata import version
from io import BytesIO
from pathlib import Path
from time import perf_counter

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from examples.benchmark_cases import BenchmarkCase, build_case


@dataclass(frozen=True, slots=True)
class Sample:
    seconds: float
    peak_rss_mib: float
    pdf_bytes: int
    pages: int


@dataclass(frozen=True, slots=True)
class Result:
    case: BenchmarkCase
    scale: int
    median_seconds: float
    min_seconds: float
    max_seconds: float
    max_peak_rss_mib: float
    samples: tuple[Sample, ...]


@dataclass(frozen=True, slots=True)
class Environment:
    python: str
    platform: str
    machine: str
    cpu_count: int | None
    packages: tuple[tuple[str, str], ...]
    workload_sha256: str


@dataclass(frozen=True, slots=True)
class Report:
    schema_version: int
    environment: Environment
    results: tuple[Result, ...]


def _worker(case: BenchmarkCase, scale: int, output: Path) -> Sample:
    import resource

    started = perf_counter()
    data = build_case(case, scale).save_to_bytes()
    seconds = perf_counter() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_rss_mib = rss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    # Disk I/O and PDF inspection are outside both the timer and peak-RSS sample.
    output.write_bytes(data)
    return Sample(seconds, peak_rss_mib, len(data), len(PdfReader(BytesIO(data)).pages))


def _case(value: str) -> BenchmarkCase:
    match value:
        case "table" | "chinese" | "shadows":
            return value
        case _:
            raise AssertionError(f"Unknown benchmark workload: {value}")


def _measure(output: Path, scale: int, repeats: int) -> Report:
    output.mkdir(parents=True, exist_ok=True)
    results: list[Result] = []
    cases: tuple[BenchmarkCase, ...] = ("table", "chinese", "shadows")
    for case in cases:
        samples: list[Sample] = []
        for index in range(repeats):
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--worker", case, str(scale),
                 str(output.resolve() / f"{case}-{index + 1}.pdf")],
                check=True, capture_output=True, text=True, timeout=180,
            )
            samples.append(Sample(**json.loads(completed.stdout)))
        times = [sample.seconds for sample in samples]
        results.append(Result(case, scale, statistics.median(times), min(times), max(times),
                              max(sample.peak_rss_mib for sample in samples), tuple(samples)))
    fingerprint = hashlib.sha256(Path(__file__).read_bytes() + (ROOT / "examples/benchmark_cases.py").read_bytes()).hexdigest()
    environment = Environment(
        platform.python_version(), platform.platform(), platform.machine(), os.cpu_count(),
        tuple((name, version(name)) for name in ("smart-report", "reportlab", "pillow", "pypdfium2", "fonttools", "uharfbuzz")),
        fingerprint,
    )
    return Report(1, environment, tuple(results))


def main() -> int:
    if sys.platform not in {"darwin", "linux"}:
        print("Peak-RSS benchmarks currently support macOS and Linux", file=sys.stderr)
        return 2
    args = sys.argv[1:]
    match args:
        case ["--worker", case, raw_scale, path]:
            print(json.dumps(asdict(_worker(_case(case), int(raw_scale), Path(path))), allow_nan=False))
            return 0
        case [path] | [path, _] | [path, _, _]:
            scale = int(args[1]) if len(args) > 1 else 1
            repeats = int(args[2]) if len(args) > 2 else 3
            if scale < 1 or repeats < 1:
                print("Scale and repeats must be positive integers", file=sys.stderr)
                return 2
            try:
                report = _measure(Path(path), scale, repeats)
            except subprocess.CalledProcessError as error:
                print(error.stderr, file=sys.stderr)
                return 1
            result_path = Path(path) / "results.json"
            result_path.write_text(json.dumps(asdict(report), indent=2, allow_nan=False) + "\n")
            print(result_path)
            return 0
        case _:
            print("Usage: benchmark_reports.py OUTPUT_DIR [SCALE=1] [REPEATS=3]", file=sys.stderr)
            return 2


if __name__ == "__main__":
    raise SystemExit(main())
