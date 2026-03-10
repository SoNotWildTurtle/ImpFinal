"""Validate processing forecast generation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORECASTER_PATH = ROOT / "core" / "imp_processing_forecaster.py"
LOG_DIR = ROOT / "logs"
PROCESSING_LOG = LOG_DIR / "imp-processing-log.json"

spec = importlib.util.spec_from_file_location("imp_processing_forecaster", FORECASTER_PATH)
forecaster = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forecaster)


def _write_log(entries):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSING_LOG.write_text(json.dumps(entries))


def _restore_log(original: str | None):
    if original is None:
        if PROCESSING_LOG.exists():
            PROCESSING_LOG.unlink()
    else:
        PROCESSING_LOG.write_text(original)


def test_forecast_outputs_confidence_and_predictions():
    original = PROCESSING_LOG.read_text() if PROCESSING_LOG.exists() else None
    sample = [
        {
            "event": "cycle",
            "group": "self_improvement",
            "duration": 10 + i,
            "backlog": 5 + i,
            "resource_score": 0.5 + (i * 0.01),
        }
        for i in range(8)
    ]
    _write_log(sample)
    try:
        result = forecaster.forecast_processing_metrics(limit=20, horizon=2)
    finally:
        _restore_log(original)

    assert "self_improvement" in result
    group = result["self_improvement"]
    assert group["backlog"]["forecast"] and len(group["backlog"]["forecast"]) == 2
    assert 0.0 <= group["backlog"]["confidence"] <= 1.0
    assert group["duration"]["samples"] == 8


def test_export_forecast_creates_file(tmp_path):
    output = tmp_path / "forecast.json"
    forecast = forecaster.export_forecast(path=output, limit=0, horizon=1)
    assert output.exists()
    assert forecast["forecasts"] == {}
