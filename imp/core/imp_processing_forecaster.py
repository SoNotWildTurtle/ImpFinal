"""Forecast upcoming processing load to guide scheduling decisions."""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Tuple


CORE_DIR = Path(__file__).resolve().parent
ROOT = CORE_DIR.parent
LOG_DIR = ROOT / "logs"
PROCESSING_LOG = LOG_DIR / "imp-processing-log.json"
FORECAST_LOG = LOG_DIR / "imp-processing-forecast.json"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


utils = _load("imp_utils", CORE_DIR / "imp_utils.py")
read_json = utils.read_json
write_json = utils.write_json


def _recent_events(limit: int | None = None) -> List[Dict[str, Any]]:
    events = read_json(PROCESSING_LOG, [])
    if limit and limit > 0:
        return events[-limit:]
    return events


def _group_time_series(events: Iterable[Mapping[str, Any]]) -> Dict[str, Dict[str, List[float]]]:
    series: Dict[str, Dict[str, List[float]]] = defaultdict(
        lambda: {
            "backlog": [],
            "duration": [],
            "resource_score": [],
        }
    )
    for event in events:
        if event.get("event") != "cycle":
            continue
        group = event.get("group", "unknown")
        entry = series[group]
        entry["backlog"].append(float(event.get("backlog", 0.0)))
        entry["duration"].append(float(event.get("duration", 0.0)))
        entry["resource_score"].append(float(event.get("resource_score", 0.0)))
    return series


def _linear_forecast(values: List[float], horizon: int) -> Tuple[List[float], float]:
    if not values:
        return [0.0] * horizon, 0.0
    if len(values) == 1:
        return [values[0]] * horizon, 0.0

    n = len(values)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    denominator = sum((x - mean_x) ** 2 for x in xs) or 1.0
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x

    forecasts = [max(0.0, intercept + slope * (n + i)) for i in range(1, horizon + 1)]
    volatility = mean(abs(y - (intercept + slope * x)) for x, y in zip(xs, values))
    return forecasts, volatility


def _confidence(values: List[float], volatility: float) -> float:
    if not values:
        return 0.0
    magnitude = mean(abs(v) for v in values) or 1.0
    ratio = max(0.0, 1.0 - min(volatility / magnitude, 1.0))
    sample_bonus = min(len(values) / 50.0, 0.4)
    return round(min(1.0, ratio + sample_bonus), 2)


def forecast_processing_metrics(limit: int | None = 200, horizon: int = 3) -> Dict[str, Any]:
    events = _recent_events(limit)
    grouped = _group_time_series(events)

    result: Dict[str, Any] = {}
    for group, metrics in grouped.items():
        group_result: Dict[str, Any] = {}
        for key, values in metrics.items():
            forecasts, volatility = _linear_forecast(values, horizon)
            group_result[key] = {
                "samples": len(values),
                "recent_average": round(mean(values[-10:]) if values else 0.0, 3),
                "forecast": [round(v, 3) for v in forecasts],
                "volatility": round(volatility, 3),
                "confidence": _confidence(values, volatility),
            }
        result[group] = group_result
    return result


def export_forecast(path: Path | None = None, limit: int | None = 200, horizon: int = 3) -> Dict[str, Any]:
    forecast = {
        "generated_at": utils.utc_timestamp(),
        "limit": limit,
        "horizon": horizon,
        "forecasts": forecast_processing_metrics(limit=limit, horizon=horizon),
    }
    target = path or FORECAST_LOG
    write_json(target, forecast)
    return forecast


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Forecast upcoming processing load")
    parser.add_argument("--limit", type=int, default=200, help="Number of recent events to analyse")
    parser.add_argument("--horizon", type=int, default=3, help="Forecast horizon in cycles")
    parser.add_argument(
        "--output",
        type=Path,
        default=FORECAST_LOG,
        help="Where to write the forecast report",
    )
    parser.add_argument("--print", action="store_true", help="Print the forecast summary to stdout")
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    forecast = export_forecast(path=args.output, limit=args.limit, horizon=args.horizon)
    if args.print:
        print(json.dumps(forecast, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
