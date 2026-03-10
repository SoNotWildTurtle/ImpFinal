"""Summarize processing telemetry to guide scheduling and tuning."""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Tuple

CORE_DIR = Path(__file__).resolve().parent
ROOT = CORE_DIR.parent
LOG_DIR = ROOT / "logs"
PROCESSING_LOG = LOG_DIR / "imp-processing-log.json"


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


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (ValueError, OSError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
    return None


SPARK_CHARS = " .:-=+*#%@"


def _sparkline(values: Iterable[float | int], width: int = 18) -> str:
    """Return a compact textual sparkline for human-friendly displays."""

    data = [float(v) for v in values if isinstance(v, (int, float))]
    if not data:
        return ""

    if len(data) > width:
        step = max(1, len(data) // width)
        averaged = []
        for index in range(0, len(data), step):
            chunk = data[index : index + step]
            averaged.append(sum(chunk) / len(chunk))
        data = averaged[-width:]

    minimum = min(data)
    maximum = max(data)
    if maximum == minimum:
        char = SPARK_CHARS[-2]
        return char * len(data)

    scale = (maximum - minimum) or 1.0
    buckets = len(SPARK_CHARS) - 1
    chars = []
    for value in data:
        ratio = (value - minimum) / scale
        chars.append(SPARK_CHARS[min(buckets, max(0, int(ratio * buckets)))])
    return "".join(chars)


def _aggregate_cycles(events: Iterable[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    data: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "durations": [],
            "threads": [],
            "errors": 0,
            "cycles": 0,
            "resource_scores": [],
            "backlog": [],
            "remote_dispatches": 0,
            "dispatch_intervals": [],
            "orchestration_events": 0,
            "recent_backlog": [],
            "recent_duration": [],
            "recent_threads": [],
            "max_backlog": 0,
            "first_timestamp": None,
            "last_timestamp": None,
        }
    )

    for event in events:
        group = event.get("group", "unknown")
        entry = data[group]
        event_type = event.get("event")
        timestamp = _parse_timestamp(event.get("timestamp"))
        if timestamp:
            if entry["first_timestamp"] is None:
                entry["first_timestamp"] = timestamp
            entry["last_timestamp"] = timestamp
        if event_type == "cycle":
            entry["cycles"] += 1
            entry["durations"].append(float(event.get("duration", 0.0)))
            entry["recent_duration"].append(float(event.get("duration", 0.0)))
            entry["threads"].append(float(event.get("threads", 0.0)))
            entry["recent_threads"].append(float(event.get("threads", 0.0)))
            entry["errors"] += int(event.get("errors", 0))
            entry["resource_scores"].append(float(event.get("resource_score", 0.0)))
            entry["backlog"].append(int(event.get("backlog", 0)))
            entry["recent_backlog"].append(int(event.get("backlog", 0)))
            if len(entry["recent_backlog"]) > 10:
                entry["recent_backlog"] = entry["recent_backlog"][-10:]
            if len(entry["recent_duration"]) > 10:
                entry["recent_duration"] = entry["recent_duration"][-10:]
            if len(entry["recent_threads"]) > 10:
                entry["recent_threads"] = entry["recent_threads"][-10:]
            entry["max_backlog"] = max(entry["max_backlog"], int(event.get("backlog", 0)))
        elif event_type == "remote_dispatch":
            entry["remote_dispatches"] += 1
            interval = event.get("interval")
            if isinstance(interval, (int, float)):
                entry["dispatch_intervals"].append(float(interval))
        elif event_type == "cloud_orchestration":
            entry["orchestration_events"] += 1
    return data


def _summarize_group(name: str, entry: Mapping[str, Any]) -> Dict[str, Any]:
    cycles = entry["cycles"] or 0
    durations = entry["durations"]
    threads = entry["threads"]
    resource_scores = entry["resource_scores"]
    backlog = entry["backlog"]

    if cycles:
        avg_duration = mean(durations) if durations else 0.0
        avg_threads = mean(threads) if threads else 0.0
        avg_resource = mean(resource_scores) if resource_scores else 0.0
        avg_backlog = mean(backlog) if backlog else 0.0
        error_rate = entry["errors"] / max(1, cycles)
    else:
        avg_duration = avg_threads = avg_resource = avg_backlog = error_rate = 0.0

    first_ts = entry.get("first_timestamp")
    last_ts = entry.get("last_timestamp")
    horizon = 0.0
    if isinstance(first_ts, datetime) and isinstance(last_ts, datetime):
        horizon = max(0.0, (last_ts - first_ts).total_seconds())

    throughput_per_hour = 0.0
    if horizon > 0 and cycles:
        throughput_per_hour = cycles / (horizon / 3600.0)

    dispatch_intervals = entry.get("dispatch_intervals") or []
    avg_dispatch_interval = mean(dispatch_intervals) if dispatch_intervals else None
    remote_ratio = entry["remote_dispatches"] / cycles if cycles else 0.0
    recent_backlog = entry.get("recent_backlog") or []

    summary = {
        "cycles": cycles,
        "average_duration": round(avg_duration, 4),
        "average_threads": round(avg_threads, 2),
        "error_rate": round(error_rate, 4),
        "average_resource_score": round(avg_resource, 2),
        "average_backlog": round(avg_backlog, 2),
        "remote_dispatches": entry["remote_dispatches"],
        "orchestration_events": entry["orchestration_events"],
        "max_backlog": entry.get("max_backlog", 0),
        "throughput_per_hour": round(throughput_per_hour, 2),
        "remote_dispatch_ratio": round(remote_ratio, 3),
        "last_cycle_at": last_ts.isoformat() if isinstance(last_ts, datetime) else None,
        "average_dispatch_interval": round(avg_dispatch_interval, 2)
        if avg_dispatch_interval is not None
        else None,
        "backlog_trend": _backlog_trend(recent_backlog),
    }
    summary["backlog_sparkline"] = _sparkline(entry.get("recent_backlog", []))
    summary["duration_sparkline"] = _sparkline(entry.get("recent_duration", []))
    summary["thread_sparkline"] = _sparkline(entry.get("recent_threads", []))
    score, status, alerts = _calculate_health(summary)
    summary["health_score"] = score
    summary["health_status"] = status
    if alerts:
        summary["alerts"] = alerts
    return summary


def _backlog_trend(recent: Iterable[int]) -> str:
    samples = list(recent)[-5:]
    if len(samples) < 2:
        return "stable"
    first, last = samples[0], samples[-1]
    if last > first + 1:
        return "rising"
    if last < first - 1:
        return "falling"
    return "stable"


def _calculate_health(metrics: Mapping[str, Any]) -> Tuple[int, str, List[str]]:
    """Return a simple health score, status text, and any alerts for a group."""

    score = 100.0
    alerts: List[str] = []

    error_rate = float(metrics.get("error_rate", 0.0))
    if error_rate > 0:
        penalty = min(45.0, error_rate * 200.0)
        score -= penalty
        if error_rate >= 0.2:
            alerts.append(f"High error rate ({error_rate:.0%})")

    avg_duration = float(metrics.get("average_duration", 0.0))
    if avg_duration > 20:
        penalty = min(20.0, (avg_duration - 20.0) * 1.5)
        score -= penalty
        alerts.append(f"Long runtime ({avg_duration:.1f}s)")

    avg_backlog = float(metrics.get("average_backlog", 0.0))
    if avg_backlog > 5:
        penalty = min(20.0, (avg_backlog - 5.0) * 1.5)
        score -= penalty
        alerts.append(f"Backlog growing ({avg_backlog:.1f})")

    if metrics.get("backlog_trend") == "rising":
        score -= 5
        alerts.append("Backlog trend rising")

    if metrics.get("remote_dispatches", 0) == 0 and metrics.get("cycles", 0) > 0:
        score -= 5
        alerts.append("No remote dispatches recorded")

    dispatch_ratio = metrics.get("remote_dispatch_ratio") or 0.0
    if dispatch_ratio and dispatch_ratio < 0.2 and metrics.get("remote_dispatches", 0) > 0:
        alerts.append("Remote dispatches infrequent relative to cycles")

    score = max(0, round(score))
    if score >= 80:
        status = "stable"
    elif score >= 60:
        status = "watch"
    else:
        status = "needs_attention"

    return score, status, alerts


PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _raise_priority(current: str, candidate: str) -> str:
    if PRIORITY_ORDER.get(candidate, 4) < PRIORITY_ORDER.get(current, 4):
        return candidate
    return current


def _build_recommendations(summary: Mapping[str, Mapping[str, Any]]) -> List[str]:
    recommendations: List[str] = []
    for group, metrics in summary.items():
        error_rate = metrics["error_rate"]
        avg_duration = metrics["average_duration"]
        remote_dispatches = metrics["remote_dispatches"]
        backlog_trend = metrics.get("backlog_trend")
        dispatch_ratio = metrics.get("remote_dispatch_ratio", 0.0)
        if error_rate >= 0.2:
            recommendations.append(
                f"Investigate failures in '{group}' (error rate {error_rate:.0%})."
            )
        if avg_duration > 30:
            recommendations.append(
                f"Consider splitting workload for '{group}' (avg duration {avg_duration:.1f}s)."
            )
        if remote_dispatches == 0 and metrics["cycles"] > 0:
            recommendations.append(
                f"Review remote tasks for '{group}' – no dispatches recorded."
            )
        elif dispatch_ratio < 0.2 and metrics["cycles"] > 5:
            recommendations.append(
                f"Increase remote throughput for '{group}' (dispatch ratio {dispatch_ratio:.0%})."
            )
        if backlog_trend == "rising":
            recommendations.append(
                f"Backlog is rising for '{group}'. Consider increasing threads or splitting work."
            )
    if not recommendations:
        recommendations.append("Processing telemetry shows no critical issues.")
    return recommendations


def _structured_action_plan(
    summary: Mapping[str, Mapping[str, Any]],
    forecasts: Mapping[str, Mapping[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    plan: List[Dict[str, Any]] = []
    forecasts = forecasts or {}

    for group, metrics in summary.items():
        health_status = metrics.get("health_status", "stable")
        priority = "low"
        if health_status == "needs_attention":
            priority = "critical"
        elif health_status == "watch":
            priority = "medium"

        reasons: List[str] = []
        actions: List[str] = []

        error_rate = float(metrics.get("error_rate", 0.0))
        if error_rate >= 0.2:
            priority = _raise_priority(priority, "critical")
            reasons.append(f"Error rate at {error_rate:.0%}")
            actions.append("Inspect recent failures and retry queue")
        elif error_rate >= 0.05:
            priority = _raise_priority(priority, "high")
            reasons.append(f"Error rate trending up ({error_rate:.0%})")
            actions.append("Audit failing tasks and add retries")

        backlog_trend = metrics.get("backlog_trend")
        avg_backlog = float(metrics.get("average_backlog", 0.0))
        if backlog_trend == "rising" or avg_backlog > 5:
            priority = _raise_priority(priority, "high")
            reasons.append(
                "Backlog rising" if backlog_trend == "rising" else "Backlog above target"
            )
            actions.append("Scale threads or offload work to remote nodes")

        dispatch_ratio = float(metrics.get("remote_dispatch_ratio", 0.0) or 0.0)
        remote_dispatches = int(metrics.get("remote_dispatches", 0))
        if remote_dispatches == 0 and metrics.get("cycles", 0) > 0:
            priority = _raise_priority(priority, "medium")
            reasons.append("No remote dispatches recorded")
            actions.append("Review distributed queue configuration")
        elif remote_dispatches > 0 and dispatch_ratio < 0.2 and metrics.get("cycles", 0) > 5:
            priority = _raise_priority(priority, "medium")
            reasons.append("Remote dispatch ratio low")
            actions.append("Increase remote capacity or adjust thresholds")

        forecast_entry = forecasts.get(group, {}).get("backlog") or {}
        forecast_values = forecast_entry.get("forecast") or []
        confidence = float(forecast_entry.get("confidence", 0.0))
        if forecast_values and confidence >= 0.4:
            projected = forecast_values[-1]
            if projected > avg_backlog + 3:
                priority = _raise_priority(priority, "high")
                reasons.append(
                    f"Forecast backlog {projected:.1f} with confidence {confidence:.0%}"
                )
                actions.append("Schedule pre-emptive scaling or task splitting")

        if not reasons and PRIORITY_ORDER.get(priority, 4) > PRIORITY_ORDER["medium"]:
            continue

        summary_text = "; ".join(reasons) if reasons else f"Status {health_status}"
        plan.append(
            {
                "group": group,
                "priority": priority,
                "summary": summary_text,
                "actions": actions or ["Review telemetry for this group"],
                "health_score": metrics.get("health_score"),
            }
        )

    if not plan:
        plan.append(
            {
                "group": "overall",
                "priority": "info",
                "summary": "Processing telemetry shows stable performance.",
                "actions": ["Continue routine monitoring"],
                "health_score": 100,
            }
        )

    plan.sort(
        key=lambda item: (
            PRIORITY_ORDER.get(item.get("priority", "info"), 4),
            item.get("group", ""),
        )
    )
    return plan


def processing_health_snapshot(limit: int | None = 200) -> Dict[str, Any]:
    """Return a condensed view of processing health for dashboards."""

    report = generate_processing_report(limit=limit)
    groups = report.get("groups", {})
    scores = [group["health_score"] for group in groups.values() if group.get("cycles")]
    average_score = round(sum(scores) / len(scores), 2) if scores else 100.0

    worst_groups = sorted(
        (
            (name, metrics)
            for name, metrics in groups.items()
            if metrics.get("cycles")
        ),
        key=lambda item: item[1].get("health_score", 100),
    )
    comparisons = processing_comparisons(limit=limit, top=3, report=report)

    summary = {
        "generated_at": report.get("generated_at"),
        "overall_health": {
            "score": average_score,
            "status": _status_from_score(average_score),
            "group_count": len(groups),
        },
        "groups": groups,
        "alerts": report.get("recommendations", []),
        "action_plan": report.get("action_plan", []),
        "comparisons": comparisons,
    }
    if worst_groups:
        summary["spotlight"] = [name for name, _ in worst_groups[:3]]
    leaders = [entry["group"] for entry in comparisons.get("top_performers", [])]
    if leaders:
        summary["leaders"] = leaders
    risks = [entry["group"] for entry in comparisons.get("needs_attention", [])]
    if risks:
        summary["risk_groups"] = risks
    return summary


def _status_from_score(score: float) -> str:
    if score >= 80:
        return "stable"
    if score >= 60:
        return "watch"
    return "needs_attention"


def generate_processing_report(limit: int | None = 200) -> Dict[str, Any]:
    events = _recent_events(limit)
    groups = _aggregate_cycles(events)
    summary = {name: _summarize_group(name, entry) for name, entry in groups.items()}

    processing_forecaster = None
    try:
        from . import imp_processing_forecaster
    except ImportError:
        pass
    else:
        processing_forecaster = imp_processing_forecaster

    orchestration_events = [
        event for event in events if event.get("event") == "cloud_orchestration"
    ]
    remote_events = [
        event for event in events if event.get("event") == "remote_dispatch"
    ]
    recent_highlights = [
        event
        for event in events
        if event.get("event") in {"cloud_orchestration", "remote_dispatch"}
    ][-5:]

    forecast_data = None
    if processing_forecaster:
        forecast_data = processing_forecaster.forecast_processing_metrics(limit=limit)

    action_plan = _structured_action_plan(summary, forecasts=forecast_data)

    report: Dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "events_analyzed": len(events),
        "groups": summary,
        "orchestration_event_count": len(orchestration_events),
        "remote_dispatch_count": len(remote_events),
        "recent_highlights": recent_highlights,
        "recommendations": _build_recommendations(summary),
        "action_plan": action_plan,
    }
    scores = [metrics["health_score"] for metrics in summary.values() if metrics.get("cycles")]
    average_score = round(sum(scores) / len(scores), 2) if scores else 100.0
    report["overall_health"] = {
        "score": average_score,
        "status": _status_from_score(average_score),
        "group_count": len(summary),
    }
    if forecast_data is not None:
        report["forecasts"] = forecast_data
    return report


def processing_comparisons(
    limit: int | None = 200,
    *,
    top: int = 3,
    report: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return rankings that compare processing groups across key metrics."""

    if report is None:
        report = generate_processing_report(limit=limit)

    groups: Mapping[str, Mapping[str, Any]] = report.get("groups", {})

    def _sorted(
        key_func,
        *,
        reverse: bool,
    ) -> List[Dict[str, Any]]:
        items: List[Tuple[str, float, Mapping[str, Any]]] = []
        for name, metrics in groups.items():
            try:
                value = key_func(metrics)
            except (TypeError, ValueError):
                continue
            if value is None:
                continue
            items.append((name, float(value), metrics))
        items.sort(key=lambda item: item[1], reverse=reverse)
        results: List[Dict[str, Any]] = []
        for name, value, metrics in items[: max(0, top) or 0]:
            entry = {
                "group": name,
                "value": round(value, 4),
                "health_score": metrics.get("health_score"),
                "health_status": metrics.get("health_status"),
                "average_backlog": metrics.get("average_backlog"),
                "remote_dispatch_ratio": metrics.get("remote_dispatch_ratio"),
                "error_rate": metrics.get("error_rate"),
            }
            results.append(entry)
        return results

    needs_attention = [
        {
            "group": name,
            "health_score": metrics.get("health_score"),
            "health_status": metrics.get("health_status"),
            "average_backlog": metrics.get("average_backlog"),
        }
        for name, metrics in groups.items()
        if metrics.get("health_status") == "needs_attention"
    ]
    needs_attention.sort(key=lambda item: item.get("health_score") or 100)

    return {
        "generated_at": report.get("generated_at"),
        "top_performers": _sorted(
            lambda metrics: metrics.get("health_score", 0.0), reverse=True
        ),
        "largest_backlog": _sorted(
            lambda metrics: metrics.get("average_backlog", 0.0), reverse=True
        ),
        "highest_error_rate": _sorted(
            lambda metrics: metrics.get("error_rate", 0.0), reverse=True
        ),
        "lowest_remote_ratio": _sorted(
            lambda metrics: metrics.get("remote_dispatch_ratio", 0.0), reverse=False
        ),
        "needs_attention": needs_attention,
    }


def export_report(path: Path, limit: int | None = 200) -> Dict[str, Any]:
    report = generate_processing_report(limit=limit)
    write_json(path, report)
    return report


def group_diagnostics(name: str, *, limit: int | None = 200) -> Dict[str, Any]:
    events = _recent_events(limit)
    group_events = [event for event in events if event.get("group") == name]
    if not group_events:
        return {"group": name, "summary": None, "recent_events": [], "trend": {}}

    summary_map = _aggregate_cycles(group_events)
    metrics = summary_map.get(name)
    summary = _summarize_group(name, metrics) if metrics else None
    trend = {
        "backlog": metrics.get("recent_backlog", []) if metrics else [],
        "dispatch_intervals": metrics.get("dispatch_intervals", []) if metrics else [],
    }
    return {
        "group": name,
        "summary": summary,
        "recent_events": group_events[-10:],
        "trend": trend,
    }


def format_group_diagnostics(diagnostics: Mapping[str, Any]) -> str:
    group = diagnostics.get("group", "unknown")
    summary = diagnostics.get("summary") or {}
    lines = [f"Diagnostics for group '{group}'"]
    if not summary:
        lines.append("No events recorded.")
        return "\n".join(lines)

    lines.append(
        "Health score: {score} ({status})".format(
            score=summary.get("health_score", "n/a"),
            status=summary.get("health_status", "unknown"),
        )
    )
    lines.append(
        "Throughput: {cycles} cycles, {rate} cycles/hour".format(
            cycles=summary.get("cycles", 0),
            rate=summary.get("throughput_per_hour", 0.0),
        )
    )
    lines.append(
        "Backlog avg={avg} max={max} trend={trend}".format(
            avg=summary.get("average_backlog", 0.0),
            max=summary.get("max_backlog", 0),
            trend=summary.get("backlog_trend", "stable"),
        )
    )
    lines.append(
        "Remote dispatches: {count} ratio={ratio}".format(
            count=summary.get("remote_dispatches", 0),
            ratio=summary.get("remote_dispatch_ratio", 0.0),
        )
    )
    interval = summary.get("average_dispatch_interval")
    if interval:
        lines.append(f"Average dispatch interval: {interval}s")
    last_cycle = summary.get("last_cycle_at")
    if last_cycle:
        lines.append(f"Last cycle completed: {last_cycle}")
    alerts = summary.get("alerts") or []
    if alerts:
        lines.append("Alerts:")
        for alert in alerts:
            lines.append(f"- {alert}")
    recent_events = diagnostics.get("recent_events") or []
    if recent_events:
        lines.append("")
        lines.append("Recent events:")
        for event in recent_events[-5:]:
            timestamp = event.get("timestamp") or "unknown"
            description = event.get("event", "unknown")
            lines.append(f"  - {timestamp}: {description}")
    return "\n".join(lines)


def format_comparisons(data: Mapping[str, Any]) -> str:
    lines = ["Processing Comparisons"]

    top = data.get("top_performers") or []
    if top:
        lines.append("Top performers:")
        for entry in top:
            lines.append(
                "  - {group} (score {score}, backlog {backlog})".format(
                    group=entry.get("group"),
                    score=entry.get("health_score", "n/a"),
                    backlog=entry.get("average_backlog", "n/a"),
                )
            )

    backlog = data.get("largest_backlog") or []
    if backlog:
        lines.append("Largest average backlog:")
        for entry in backlog:
            lines.append(
                "  - {group} ({backlog})".format(
                    group=entry.get("group"),
                    backlog=entry.get("average_backlog", entry.get("value")),
                )
            )

    errors = data.get("highest_error_rate") or []
    if errors:
        lines.append("Highest error rate:")
        for entry in errors:
            rate = entry.get("error_rate", entry.get("value", 0.0))
            lines.append(
                f"  - {entry.get('group')} ({rate:.0%})"
            )

    remote = data.get("lowest_remote_ratio") or []
    if remote:
        lines.append("Lowest remote dispatch ratio:")
        for entry in remote:
            ratio = entry.get("remote_dispatch_ratio", entry.get("value", 0.0))
            lines.append(
                f"  - {entry.get('group')} ({ratio:.0%})"
            )

    needs = data.get("needs_attention") or []
    if needs:
        lines.append("Needs attention:")
        for entry in needs:
            lines.append(
                "  - {group} (score {score})".format(
                    group=entry.get("group"),
                    score=entry.get("health_score", "n/a"),
                )
            )

    if len(lines) == 1:
        lines.append("No processing groups to compare yet.")

    return "\n".join(lines)


def group_timeline(name: str, *, limit: int | None = 200) -> List[Dict[str, Any]]:
    """Return chronological cycle metrics for the requested processing group."""

    events = _recent_events(limit)
    timeline: List[Tuple[datetime | None, Dict[str, Any]]] = []
    for event in events:
        if event.get("group") != name or event.get("event") != "cycle":
            continue
        timestamp = _parse_timestamp(event.get("timestamp"))
        entry = {
            "timestamp": timestamp.isoformat() if timestamp else event.get("timestamp"),
            "backlog": int(event.get("backlog", 0)),
            "duration": float(event.get("duration", 0.0)),
            "threads": float(event.get("threads", 0.0)),
            "resource_score": float(event.get("resource_score", 0.0)),
        }
        timeline.append((timestamp, entry))

    timeline.sort(key=lambda pair: pair[0] or datetime.min)
    return [entry for _, entry in timeline]


def format_group_timeline(name: str, timeline: List[Mapping[str, Any]]) -> str:
    lines = [f"Timeline for group '{name}'"]
    if not timeline:
        lines.append("No cycle telemetry recorded yet.")
        return "\n".join(lines)

    lines.append("timestamp                backlog duration threads resource")
    recent = timeline[-10:]
    for entry in recent:
        ts = (entry.get("timestamp") or "unknown")
        ts = ts[:26] if isinstance(ts, str) else str(ts)
        backlog = int(entry.get("backlog", 0))
        duration = float(entry.get("duration", 0.0))
        threads = float(entry.get("threads", 0.0))
        resource = float(entry.get("resource_score", 0.0))
        lines.append(
            f"{ts:<24} {backlog:>7} {duration:>8.2f} {threads:>7.2f} {resource:>8.2f}"
        )

    backlog_values = [entry.get("backlog", 0) for entry in timeline]
    duration_values = [entry.get("duration", 0.0) for entry in timeline]
    resource_values = [entry.get("resource_score", 0.0) for entry in timeline]

    lines.append("")
    backlog_sparkline = _sparkline(backlog_values)
    if backlog_sparkline:
        lines.append(f"Backlog sparkline  : {backlog_sparkline}")
    duration_sparkline = _sparkline(duration_values)
    if duration_sparkline:
        lines.append(f"Duration sparkline : {duration_sparkline}")
    resource_sparkline = _sparkline(resource_values)
    if resource_sparkline:
        lines.append(f"Resource sparkline : {resource_sparkline}")
    return "\n".join(lines)


def _format_report(report: Mapping[str, Any]) -> str:
    lines = ["IMP Processing Report"]
    lines.append(f"Generated at: {report.get('generated_at')}")
    lines.append(f"Events analyzed: {report.get('events_analyzed')}")
    overall = report.get("overall_health") or {}
    if overall:
        lines.append(
            "Overall health: score={score} status={status} groups={group_count}".format(
                score=overall.get("score", "n/a"),
                status=overall.get("status", "unknown"),
                group_count=overall.get("group_count", 0),
            )
        )
    lines.append("")
    for group, metrics in sorted(report.get("groups", {}).items()):
        lines.append(f"Group: {group}")
        lines.append(
            "  cycles={cycles} avg_duration={average_duration}s avg_threads={average_threads}".format(
                **metrics
            )
        )
        lines.append(
            "  error_rate={error_rate} remote_dispatches={remote_dispatches} orchestration_events={orchestration_events}".format(
                **metrics
            )
        )
        lines.append(
            "  avg_resource={average_resource_score} avg_backlog={average_backlog}".format(
                **metrics
            )
        )
        lines.append(
            "  health_score={health_score} status={health_status}".format(**metrics)
        )
        alerts = metrics.get("alerts")
        if alerts:
            lines.append("  alerts: " + "; ".join(alerts))
        lines.append("")
    if report.get("recommendations"):
        lines.append("Recommendations:")
        for item in report["recommendations"]:
            lines.append(f"- {item}")
    else:
        lines.append("Recommendations: none")
    if report.get("action_plan"):
        lines.append("")
        lines.append("Action plan:")
        for entry in report["action_plan"]:
            lines.append(
                "- [{priority}] {group}: {summary}".format(
                    priority=entry.get("priority", "info").upper(),
                    group=entry.get("group", "unknown"),
                    summary=entry.get("summary", ""),
                )
            )
            for action in entry.get("actions", []):
                lines.append(f"    -> {action}")
    return "\n".join(lines)


def _format_summary(summary: Mapping[str, Any]) -> str:
    overall = summary.get("overall_health", {})
    lines = ["Processing Health Snapshot"]
    lines.append(
        "Overall: score={score} status={status} groups={group_count}".format(
            score=overall.get("score", "n/a"),
            status=overall.get("status", "unknown"),
            group_count=overall.get("group_count", 0),
        )
    )
    lines.append("")
    spotlight = summary.get("spotlight") or []
    if spotlight:
        lines.append("Focus groups: " + ", ".join(spotlight))
        lines.append("")
    for group, metrics in sorted(summary.get("groups", {}).items()):
        lines.append(
            "{name}: score={score} status={status} cycles={cycles} errors={errors}".format(
                name=group,
                score=metrics.get("health_score", "n/a"),
                status=metrics.get("health_status", "unknown"),
                cycles=metrics.get("cycles", 0),
                errors=metrics.get("error_rate", 0.0),
            )
        )
    if summary.get("alerts"):
        lines.append("")
        lines.append("Alerts:")
        for alert in summary["alerts"]:
            lines.append(f"- {alert}")
    return "\n".join(lines)


def format_action_plan(plan: Iterable[Mapping[str, Any]]) -> str:
    lines = ["Processing Action Plan"]
    for entry in plan:
        priority = entry.get("priority", "info").upper()
        group = entry.get("group", "unknown")
        summary = entry.get("summary", "")
        lines.append(f"- [{priority}] {group}: {summary}")
        for action in entry.get("actions", []):
            lines.append(f"    -> {action}")
    return "\n".join(lines)


def action_plan(limit: int | None = 200) -> List[Dict[str, Any]]:
    report = generate_processing_report(limit=limit)
    return report.get("action_plan", [])


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate summaries from IMP processing telemetry."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Number of recent events to analyze (default: 200).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as formatted JSON instead of text.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional file path to save the generated report as JSON.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a condensed health summary instead of the full report.",
    )
    parser.add_argument(
        "--group",
        help="Show diagnostics for a specific processing group.",
    )
    parser.add_argument(
        "--timeline",
        action="store_true",
        help="Display a timeline view for the specified group (requires --group).",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Show rankings across processing groups.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="Number of groups to display when comparing (default: 3).",
    )
    parser.add_argument(
        "--alerts-only",
        action="store_true",
        help="Only display alerts and recommendations.",
    )
    parser.add_argument(
        "--actions",
        action="store_true",
        help="Display the structured processing action plan.",
    )
    args = parser.parse_args(argv)

    if args.timeline:
        if not args.group:
            parser.error("--timeline requires --group to be specified")
        timeline = group_timeline(args.group, limit=args.limit)
        if args.json:
            print(json.dumps({"group": args.group, "timeline": timeline}, indent=2))
        else:
            print(format_group_timeline(args.group, timeline))
        return

    if args.group:
        diagnostics = group_diagnostics(args.group, limit=args.limit)
        print(format_group_diagnostics(diagnostics))
        return

    if args.compare:
        data = processing_comparisons(limit=args.limit, top=max(1, args.top))
        if args.json:
            print(json.dumps({"comparisons": data}, indent=2))
        else:
            print(format_comparisons(data))
        return

    if args.actions:
        plan = action_plan(limit=args.limit)
        if args.json:
            print(json.dumps({"action_plan": plan}, indent=2))
        else:
            print(format_action_plan(plan))
        return

    if args.summary:
        snapshot = processing_health_snapshot(limit=args.limit)
        if args.json:
            print(json.dumps(snapshot, indent=2))
        else:
            print(_format_summary(snapshot))
        return

    report = generate_processing_report(limit=args.limit)
    if args.alerts_only:
        alerts = report.get("recommendations", [])
        if args.json:
            print(json.dumps({"alerts": alerts}, indent=2))
        else:
            if alerts:
                print("Alerts and recommendations:")
                for item in alerts:
                    print(f"- {item}")
            else:
                print("No alerts recorded.")
        return
    if args.output:
        export_report(args.output, limit=args.limit)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(_format_report(report))


if __name__ == "__main__":
    main()
