"""Utility helpers for persisting runtime metrics to artifacts."""

from __future__ import annotations

import csv
import json
import os
import time
from contextlib import ContextDecorator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

__all__ = ["log_metric", "MetricTimer", "metric_timer"]


@dataclass
class MetricRecord:
    """A canonical representation of a metric sample."""

    timestamp: str
    metric: str
    value: float
    unit: str
    tags: Dict[str, str]

    @classmethod
    def create(
        cls,
        metric: str,
        value: float,
        unit: str,
        tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[float] = None,
    ) -> "MetricRecord":
        ts = datetime.fromtimestamp(timestamp or time.time(), tz=timezone.utc)
        return cls(
            timestamp=ts.isoformat().replace("+00:00", "Z"),
            metric=metric,
            value=float(value),
            unit=unit,
            tags=dict(tags or {}),
        )


def _artifacts_dir() -> Path:
    base = os.environ.get("SMARTGLASS_ARTIFACTS_DIR", "artifacts")
    return Path(base)


def _csv_path() -> Path:
    return _artifacts_dir() / "metrics.csv"


def _jsonl_path() -> Path:
    return _artifacts_dir() / "metrics.jsonl"


def _ensure_destination(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def log_metric(
    metric: str,
    value: float,
    *,
    unit: str = "count",
    tags: Optional[Dict[str, str]] = None,
    timestamp: Optional[float] = None,
) -> None:
    """Append a metric sample to the CSV and JSONL artifact files."""

    record = MetricRecord.create(metric, value, unit, tags=tags, timestamp=timestamp)
    _write_csv(record)
    _write_jsonl(record)


def _write_csv(record: MetricRecord) -> None:
    path = _csv_path()
    _ensure_destination(path)
    row = {
        "timestamp": record.timestamp,
        "metric": record.metric,
        "value": f"{record.value:.9f}",
        "unit": record.unit,
        "tags": json.dumps(record.tags, sort_keys=True),
    }
    should_write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(row.keys()))
        if should_write_header:
            writer.writeheader()
        writer.writerow(row)


def _write_jsonl(record: MetricRecord) -> None:
    path = _jsonl_path()
    _ensure_destination(path)
    payload = {
        "timestamp": record.timestamp,
        "metric": record.metric,
        "value": record.value,
        "unit": record.unit,
        "tags": record.tags,
    }
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, sort_keys=True))
        fp.write("\n")


class MetricTimer(ContextDecorator):
    """Context manager for timing code sections and emitting metrics."""

    def __init__(
        self,
        metric: str,
        *,
        unit: str = "ms",
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        self.metric = metric
        self.unit = unit
        self.tags = dict(tags or {})
        self.elapsed: Optional[float] = None
        self._start: Optional[float] = None

    def __enter__(self) -> "MetricTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._start is None:
            return None
        scale = 1000.0 if self.unit == "ms" else 1.0
        self.elapsed = (time.perf_counter() - self._start) * scale
        log_metric(self.metric, self.elapsed, unit=self.unit, tags=self.tags)
        return None


def metric_timer(
    metric: str,
    *,
    unit: str = "ms",
    tags: Optional[Dict[str, str]] = None,
) -> MetricTimer:
    """Factory for :class:`MetricTimer` to match contextmanager usage."""

    return MetricTimer(metric, unit=unit, tags=tags)
